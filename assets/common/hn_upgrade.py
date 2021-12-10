#!/usr/bin/env python3

import argparse
import logging
import json
import requests
import datetime
from http import HTTPStatus
from os import environ, path
from pylastic import Jelastic
from check_before_hn_upgrade import check_hardwarenodes, \
                                    get_hardware_nodes,  \
                                    get_containers,      \
                                    get_jahia_cloud_envnames_from_papi

LOG_FORMAT = "%(asctime)s %(levelname)s: [%(funcName)s] %(message)s"
logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)

logger = logging.getLogger()


class Hardware_node_upgrade():

    def __init__(self, jelastic_session, jelastic_hn_hostname, datadog_hn_hostname, region, recover_file_path,
                 recover_state, dry_run, jserver, dd_app_key, dd_api_key, papi_hostname, papi_token,
                 skip_stop):
        self.jelastic_session = jelastic_session
        self.jelastic_hardware_node_hostname = jelastic_hn_hostname
        self.datadog_hardware_node_hostname = datadog_hn_hostname
        self.region = region
        self.recover_file_path = recover_file_path
        self.recover_state = recover_state
        self.dry_run = dry_run
        self.jserver = jserver
        self.dd_app_key = dd_app_key
        self.dd_api_key = dd_api_key
        self.papi_hostname = papi_hostname
        self.papi_token = papi_token
        self.skip_stop = skip_stop

    def start_hn_upgrade(self):
        """
        Perform hn upgrade
        """
        if not self.dry_run:
            print("Make sure every possible action on environments is disabled from cloud dashboard" +
                  " (including environment creation)")
            input("Press enter to start the upgrade")

        hn_infos = self.get_hn_infos()

        self.set_hn_status(hn_infos, "MAINTENANCE")
        if not self.skip_stop and not check_hardwarenodes(self.jelastic_session, self.region,
                                                          self.papi_hostname, self.papi_token):
            self.set_hn_status(hn_infos, "ACTIVE")
            exit(1)

        valid_envnames = get_jahia_cloud_envnames_from_papi(self.papi_hostname, self.papi_token)
        running_containers = self.get_running_containers_id(jelastic_session, hn_infos["id"], valid_envnames)

        if not self.recover_state:
            self.persist_running_containers(self.recover_file_path, running_containers)

        if not self.skip_stop:
            self.stop_nodes(running_containers)

        jelastic_session.signOut()

        self.mute_hardware_node(self.datadog_hardware_node_hostname)
        self.wait_for_system_upgrade_to_be_done()

        if self.recover_state:
            running_containers = self.retrieve_running_containers(self.recover_file_path)

        # Need to re-signup. Don't know why but session seems to expire between first signIn
        # and maitenance disabling. So I added the signout after stop_nodes to re-signIn here
        jelastic_session.signIn()
        self.start_nodes(running_containers)
        jelastic_session.signOut()
        self.ask_to_disable_maintenance_mode()
        jelastic_session.signIn()
        self.set_hn_status(hn_infos, "ACTIVE")
        self.unmute_hardware_node(self.datadog_hardware_node_hostname)

    def get_hn_infos(self):
        """
            Fetch info about the hn to upgrade. It will be used to update its status
        """
        hns = get_hardware_nodes(self.jelastic_session)
        hn_data = None
        hn_hostnames_list = []
        for hn in hns:
            if hn["hostname"] == self.jelastic_hardware_node_hostname:
                hn_data = hn
            hn_hostnames_list.append(hn["hostname"])

        if hn_data is None:
            hn_hostnames_list.sort()
            logger.error("Hardware node not found. List of available hostnames:\n- " + "\n- ".join(hn_hostnames_list))
            exit(1)

        if hn_data["hardwareNodeGroup"] != self.region:
            logger.error("Hardware node is not in the specified region")
            exit(1)

        return hn_data

    def set_hn_status(self, hn_infos, status):
        """
            Set the hardware node status (can be MAINTENANCE, ACTIVE for example)
        """
        logger.info("Setting " + hn_infos["hostname"] + " status to " + status)

        if self.dry_run:
            return

        url = self.jelastic_session.hostname + "/1.0/administration/cluster/rest/edithdnode"
        # According to the documentation, all parameters are optional (even id...)
        # But as the api throw an error when one of the following is missing,
        # we are kind of forced to set theses optional parameters
        # And because of a bug, we have to specify soapPort and tcpPort because if not set,
        # the api will silently set these values to 0
        data = {
            "soapCredential": {"login": hn_infos["soapCredential"]["login"]},
            "soapPort": hn_infos["soapPort"],
            "sshCredential": {"login": hn_infos["sshCredential"]["login"]},
            "hostname": hn_infos["hostname"],
            "id": hn_infos["id"],
            "hardwareNodeGroup": hn_infos["hardwareNodeGroup"],
            "ipAddress": hn_infos["ipAddress"],
            "status": status,
            "tcpPort": hn_infos["tcpPort"]
        }
        params = {
            'session': self.jelastic_session.session,
            'appid': 'cluster',
            'hdnode': json.dumps(data)
        }
        resp = self.jelastic_session.s.get(url, params=params)

        if json.loads(resp.text)['result'] != 0:
            logger.error("Cannot set . Code:" + str(resp.text))
            exit(1)

    def get_running_containers_id(self, jelasic_session, hn_id, valid_envnames):
        """
            Returns: list with the following format:
                [env1: {bl:[id1], cp:[id2, id3]}, env2: {...}, ...]
        """
        logger.info("Getting running containers on the hardware node to upgrade")

        containers = get_containers(jelastic_session, hn_id)
        running_containers = {}
        for container in containers:
            if "envName" not in container:
                continue
            envname = container["envName"]
            node_group = container["nodeGroup"]
            status = container["status"]

            # Status = 1 when node is running
            if status == 1 and envname in valid_envnames:
                if envname not in running_containers:
                    running_containers[envname] = {}
                if node_group not in running_containers[envname]:
                    running_containers[envname][node_group] = []
                running_containers[envname][node_group].append(container["id"])

        return running_containers

    def get_jelastic_login_from_envname(self, envname):
        """
            Necessary to login as user to run stop/start packages
        """
        url = "https://" + self.papi_hostname + "/api/v1/paas-environment?namespace=" + envname
        headers = {"X-PAPI-KEY": self.papi_token}
        response = self.send_get_request(url, headers)
        org_id = response.json()[0]["paas_organization_id"]
        url = "https://" + self.papi_hostname + "/api/v1/paas-organization/" + str(org_id)
        response = self.send_get_request(url, headers)
        organization = response.json()
        return organization["jelastic_login"]

    def stop_nodes(self, running_containers):
        package = \
            "https://raw.githubusercontent.com/Jahia/jelastic-packages/main/packages/common/stop-nodes.yaml"
        for envname, containers in running_containers.items():
            logger.info("Stopping the following containers for " + envname + ": " + str(containers))
            settings = {"nodesToStop": json.dumps(containers), "dryRun": self.dry_run}
            res = json.loads(self.run_jelastic_package(settings, package, envname))
            if res["response"]["result"] != 0:
                logger.error("The package returned an error in " +
                             res["response"]["action"] + " action: " +
                             res["response"]["error"])
                exit(1)

    def start_nodes(self, running_containers):
        package = \
            "https://raw.githubusercontent.com/Jahia/jelastic-packages/main/packages/common/start-nodes.yaml"
        for envname, containers in running_containers.items():
            logger.info("Starting the following containers for " + envname + ": " + str(containers))
            settings = {"nodesToStart": containers, "dryRun": self.dry_run}
            res = json.loads(self.run_jelastic_package(settings, package, envname))
            if res["response"]["result"] != 0:
                logger.error("The package returned an error in " +
                             res["response"]["action"] + " action: " +
                             res["response"]["error"])

    def run_jelastic_package(self, settings, package, envname):
        jelastic_login = self.get_jelastic_login_from_envname(envname)
        juser_token = jelastic_session.sysAdminSignAsUser(jelastic_login)
        juser_sess = Jelastic(hostname=self.jserver,
                              login=jelastic_login,
                              session=juser_token)
        res = juser_sess.devScriptEval(package, envname, settings=settings)
        logger.info(res)
        juser_sess.signOut()
        return res.text

    def mute_hardware_node(self, hn_hostname):
        logger.info("Muting " + hn_hostname + " in datadog")
        if self.dry_run:
            return
        url = "https://api.datadoghq.com/api/v1/host/" + hn_hostname + "/mute"
        end_time = datetime.datetime.now() + datetime.timedelta(minutes=30)

        headers = {
            "DD-API-KEY": self.dd_api_key,
            "DD-APPLICATION-KEY": self.dd_app_key
        }

        data = {
            "end": str(int(datetime.datetime.timestamp(end_time))),
            "action": "Muted",
            "override": "true"
        }
        self.send_post_request(url, data, headers)

    def unmute_hardware_node(self, datadog_hn_hostname):
        logger.info("Unmuting " + datadog_hn_hostname + " in datadog")
        if self.dry_run:
            return
        url = "https://api.datadoghq.com/api/v1/host/" + datadog_hn_hostname + "/unmute"

        headers = {
            "DD-API-KEY": self.dd_api_key,
            "DD-APPLICATION-KEY": self.dd_app_key
        }
        self.send_post_request(url, headers=headers)

    def send_post_request(self, url, data=None, headers=None):
        try:
            response = requests.post(url=url, headers=headers, data=data)
            if response.status_code != HTTPStatus.OK:
                logger.error(str(response.status_code) + " : " + response.text)
                exit(1)
        except requests.RequestException as exception:
            logger.error("Exception when trying to send the POST request" + str(exception))
            exit(1)

    def send_get_request(self, url, headers=None):
        try:
            response = requests.get(url=url, headers=headers)
            if response.status_code != HTTPStatus.OK:
                logger.error(str(response.status_code) + " : " + response.text)
                exit(1)
        except requests.RequestException as exception:
            logger.error("Exception when trying to send the GET request" + str(exception))
            exit(1)
        return response

    def persist_running_containers(self, file_path, containers_ids):
        logger.info("Saving containers to stop list:" + json.dumps(containers_ids))
        if self.dry_run:
            return
        with open(file_path, 'w') as f:
            json.dump(containers_ids, f)

    def retrieve_running_containers(self, file_path):
        logger.info("Loading containers to start list")
        if self.dry_run:
            return
        with open(file_path, 'r') as f:
            return json.load(f)

    def wait_for_system_upgrade_to_be_done(self):
        print("Waiting for hardware node system upgrade to be completed")
        val = ""
        while val not in ["done", "abort"]:
            val = input("Type \"done\" when completed, \"abort\" to abort the script and exit\n")
        if val == "abort":
            logger.info("Aborting upgrade at the hardware node system upgrade step...")
            exit(0)

    def ask_to_disable_maintenance_mode(self):
        val = ""
        while val not in ["yes", "abort"]:
            val = input("Disable maintenance on the hardware node[yes/abort]\n")
        if val == "abort":
            logger.info("Aborting without disabling maintenance mode...")
            exit(0)


def argparser():
    """script options"""
    parser = argparse.ArgumentParser()

    args_list = parser.add_argument_group('Arguments')
    args_list.add_argument("--dry-run",
                           action="store_true",
                           dest="dry_run",
                           help="If set, does not perform any actions, only outputs what it would have done")

    args_list.add_argument("--jelastic-hardware-node-hostname",
                           default=environ.get("JELASTIC_HARDWARE_NODE_HOSTNAME"),
                           dest="jelastic_hn_hostname",
                           help="The jelastic hardware node hostname, "
                                "can be set with JELASTIC_HARDWARE_NODE_HOSTNAME env var")
    args_list.add_argument("--datadog-hardware-node-hostname",
                           default=environ.get("DATADOG_HARDWARE_NODE_HOSTNAME"),
                           dest="datadog_hn_hostname",
                           help="The hardware node hostname for datadog, " +
                                "can be set with DATADOG_HARDWARE_NODE_HOSTNAME env var")
    args_list.add_argument("--juser",
                           default=environ.get('JELASTIC_USER'),
                           help="the jelastic user, can be set with JELASTIC_USER env var")
    args_list.add_argument("--jpassword",
                           default=environ.get('JELASTIC_PASSWORD'),
                           help="the jelastic user, can be set with JELASTIC_PASSWORD env var")
    args_list.add_argument("--jserver",
                           default=environ.get('JELASTIC_SERVER'),
                           help="Jelastic Cluster DNS, can be set with JELASTIC_SERVER env var")
    args_list.add_argument("--region",
                           default=environ.get("JELASTIC_REGION"),
                           help="Jelastic region name. Can be set with JELASTIC_REGION env var")

    args_list.add_argument("--dd-app-key",
                           dest="dd_app_key",
                           default=environ.get('DD_APP_KEY'),
                           help="jc infra dd app key, can be set with DD_APP_KEY env var")
    args_list.add_argument("--dd-api-key",
                           dest="dd_api_key",
                           default=environ.get('DD_API_KEY'),
                           help="jc infra dd api key, can be set with DD_API_KEY env var")

    args_list.add_argument("--papi-token",
                           dest="papi_token",
                           default=environ.get('PAPI_TOKEN'),
                           help="Papi token")
    args_list.add_argument("--papi-hostname",
                           dest="papi_hostname",
                           default=environ.get('PAPI_HOSTNAME'),
                           help="Papi hostname (papi.(dev.)cloud-core.jahia.com)")

    args_list.add_argument("--state-file-path",
                           dest="recover_state_file_path",
                           required=True,
                           help="State file path")
    args_list.add_argument("--recover-state",
                           action="store_true",
                           dest="recover_state",
                           help="If this parameter is set, the state file won't be created/updated and should already exist (useful if the script has been stopped before restarting the nodes during a previous run for instance)")

    args_list.add_argument("--skip-stop",
                           action="store_true",
                           dest="skip_stop",
                           help="If this parameter is set, the script won't check the cluster state and stop nodes on the HN. It  can't be used if --recover-state is not set. It's meant to be used if the script was unintentially exited during the upgrade, of if starting some nodes failed")

    args = parser.parse_args()

    MANDATORY_VARIABLES = ["jelastic_hn_hostname", "datadog_hn_hostname", "juser", "jpassword",
                           "jserver", "region", "dd_app_key", "dd_api_key", "papi_hostname", "papi_token"]
    for mandatory_variable in MANDATORY_VARIABLES:
        args_dict = args.__dict__
        if mandatory_variable not in args_dict.keys() or not args_dict[mandatory_variable]:
            print("Parameter " + mandatory_variable + " is not set")
            print(parser.print_help())
            exit(1)

    if args.skip_stop and not args.recover_state:
        print("--skip-stop only can be set if --recover-state is set")
        exit(1)

    return args


if __name__ == "__main__":
    args = argparser()

    if args.recover_state and not path.exists(args.recover_state_file_path):
        logger.error("The provided state file does not exist")
        exit(1)

    jelastic_session = Jelastic(hostname=args.jserver,
                                login=args.juser,
                                password=args.jpassword)
    jelastic_session.signIn()

    hn_upgrade = Hardware_node_upgrade(
        jelastic_session,
        args.jelastic_hn_hostname,
        args.datadog_hn_hostname,
        args.region,
        args.recover_state_file_path,
        args.recover_state,
        args.dry_run,
        args.jserver,
        args.dd_app_key,
        args.dd_api_key,
        args.papi_hostname,
        args.papi_token,
        args.skip_stop
    )
    hn_upgrade.start_hn_upgrade()

    jelastic_session.signOut()
