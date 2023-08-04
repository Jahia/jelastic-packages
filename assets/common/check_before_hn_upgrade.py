#!/usr/bin/env python3

import argparse
import logging
import re
import requests
import os
from http import HTTPStatus
from sys import exit
from pylastic import Jelastic
import json

logger = logging.getLogger()


def argparser():
    """script options"""
    parser = argparse.ArgumentParser(
        epilog='''
        Default values are set with these environement variables:
        juser, jpassword, jserver
        '''
    )

    jel_stuff = parser.add_argument_group('Jelastic Stuffs')
    jel_stuff.add_argument("-u", "--user",
                           default=os.environ.get('juser'),
                           help="the jelastic user (default: %(default)s)")
    jel_stuff.add_argument("-p", "--password",
                           default=os.environ.get('jpassword'),
                           help="the jelastic user's password (default: %(default)s)")
    jel_stuff.add_argument("-j", "--jelastic",
                           default=os.environ.get('jserver'),
                           help="Jelastic Cluster DNS (default: %(default)s)")
    jel_stuff.add_argument("-r", "--region",
                           help="Jelastic region name")
    jel_stuff.add_argument("--papi-token",
                           dest="papi_token",
                           default=os.environ.get('PAPI_TOKEN'),
                           help="Papi token")
    jel_stuff.add_argument("--papi-hostname",
                           dest="papi_hostname",
                           default=os.environ.get('PAPI_HOSTNAME'),
                           help="Papi hostname (papi.(dev.)cloud-core.jahia.com)")

    return parser.parse_args()


def get_hardware_nodes(juser_sess):
    url = juser_sess.hostname + "/1.0/administration/cluster/rest/gethdnodes"
    params = {
        'session': juser_sess.session,
        'appid': 'cluster'
    }
    resp = juser_sess.s.get(url, params=params)

    if json.loads(resp.text)['result'] != 0:
        logging.error("Cannot retrieve hardware node list. Code:" + str(resp.text))
        exit(1)
    else:
        return json.loads(resp.text)['array']


def get_containers(juser_sess, hn_id):
    url = juser_sess.hostname + "/1.0/administration/cluster/rest/getnodes"
    params = {
        'session': juser_sess.session,
        'appid': 'cluster',
        'hdnodeid': hn_id
    }
    resp = juser_sess.s.get(url, params=params)

    if json.loads(resp.text)['result'] != 0:
        logging.error("Cannot retrieve " + str(hn_id) + "nodes. Code:" + str(resp.text))
        exit(1)
    else:
        return json.loads(resp.text)["array"]


# Record containers infos in environments and hn list for further use
def add_hn_containers_to_lists(hardware_node, environments, hardware_node_with_containers,
                               juser_sess, valid_envnames):
    hardware_node_data = {
        "name": hardware_node["hostname"],
        "containers": {}
    }

    containers = get_containers(juser_sess, hardware_node["id"])
    for container in containers:
        # Ignore weird jelastic containers
        if "envName" not in container or container["envName"] not in valid_envnames:
            continue

        env_name = container["envName"]
        node_group = container["nodeGroup"]

        # Add container to the environment
        if env_name not in environments:
            environments[env_name] = {}
        if node_group not in environments[env_name]:
            environments[env_name][node_group] = 1
        else:
            environments[env_name][node_group] += 1

        # Add container to the hardware node
        if env_name not in hardware_node_data["containers"]:
            hardware_node_data["containers"][env_name] = {}
        if node_group not in hardware_node_data["containers"][env_name]:
            hardware_node_data["containers"][env_name][node_group] = 1
        else:
            hardware_node_data["containers"][env_name][node_group] += 1

    hardware_node_with_containers.append(hardware_node_data)


def is_count_valid(node_group, count, environment):
    if (node_group == "cp" or node_group == "bl") and \
       environment[node_group] > 1 and \
       count > (environment[node_group] / 2):
        return False
    elif (node_group == "sqldb" or node_group == "es" or node_group == "storage") and count > 1:
        return False
    return True


def check_hardwarenodes(jelastic_session, region, papi_hostname, papi_token):
    environments = {}
    hardware_node_with_containers = []

    all_hardware_nodes = get_hardware_nodes(jelastic_session)
    for hardware_node in all_hardware_nodes:
        if hardware_node["hardwareNodeGroup"] != region or \
           hardware_node["status"] == "INFRASTRUCTURE_NODE":
            continue
        add_hn_containers_to_lists(
            hardware_node,
            environments,
            hardware_node_with_containers,
            jelastic_session,
            get_jahia_cloud_envnames_from_papi(papi_hostname, papi_token)
        )

    if len(hardware_node_with_containers) == 0:
        logger.info("No hardware node found for " + region + " region")
        return False

    all_hns_ok = True
    for hardware_node in hardware_node_with_containers:
        hn_ok = True
        line_template = "{env_name} has {count} {node_group} out of {node_group_count} on this HN\n"
        fails = ""

        for env_name, node_groups in hardware_node["containers"].items():
            for node_group, count in node_groups.items():
                if not is_count_valid(node_group, count, environments[env_name]):
                    hn_ok = False
                    fails += line_template.format(
                                env_name=env_name,
                                count=count,
                                node_group=node_group,
                                node_group_count=environments[env_name][node_group]
                             )

        if hn_ok:
            logger.info(hardware_node["name"] + " [" + GREEN_COLOR + "OK" + NO_COLOR + "]")
        else:
            logger.error(hardware_node["name"] + " [" + RED_COLOR + "NOK" + NO_COLOR + "]")
            logger.error(fails)
            all_hns_ok = False

    return all_hns_ok


def get_jahia_cloud_envnames_from_papi(papi_hostname, papi_token):
    url = "https://" + papi_hostname + "/api/v1/paas-environment"
    try:
        response = requests.get(url=url, headers={"X-PAPI-KEY": papi_token})
        if response.status_code != HTTPStatus.OK:
            logger.error(str(response.status_code) + " : " + response.text)
            exit(1)

    except requests.RequestException as exception:
        logger.error("Exception when trying to send the GET request" + str(exception))
        exit(1)
    envs = response.json()
    envnames = []
    for env in envs:
        envnames.append(env["namespace"])
    return envnames


# We don't care about processing node since there is always only one
VALID_NODEGROUP = ["cp", "sqldb", "bl", "es", "storage"]

# SHELL colors
RED_COLOR = "\033[0;31m"
GREEN_COLOR = "\033[0;32m"
NO_COLOR = '\033[0m'


if __name__ == "__main__":
    args = argparser()

    GATE_DNS = re.sub(r'^(app|jca)\.(.*)', r'gate.\2', args.jelastic)
    GATE_PORT = 3022

    JEL_SESS = Jelastic(hostname=args.jelastic, login=args.user, password=args.password)
    JEL_SESS.signIn()
    if check_hardwarenodes(JEL_SESS, args.region, args.papi_hostname, args.papi_token):
        exit(0)
    else:
        exit(1)
