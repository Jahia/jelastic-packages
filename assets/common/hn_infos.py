#!/usr/bin/env python3

import argparse
import logging
from os import environ
from sys import exit
from pylastic import Jelastic
import json
from check_before_hn_upgrade import get_hardware_nodes, \
    get_containers, \
    get_jahia_cloud_envnames_from_papi
from hn_upgrade import Hardware_node_upgrade

logging.getLogger().setLevel(logging.WARN)

RED_COLOR = "\033[0;31m"
YELLOW_COLOR = "\033[0;33m"
NO_COLOR = '\033[0m'

node_group_translation = {
    "jahia": {
        "bl": "Haproxy",
        "cp": "Browsing",
        "proc": "Processing",
        "sqldb": "MariaDB"
    },
    "jcustomer": {
        "cp": "jCustomer",
        "es": "Elasticsearch"
    }
}


def build_env_nodes_list(environments, containers, valid_envnames):
    """
        Updates the list of all environments in the region with their number of node per node group
    """
    for container in containers:
        # Ignore weird jelastic containers
        if "envName" not in container or container["envName"] not in valid_envnames:
            continue

        env_name = container["envName"]
        node_group = container["nodeGroup"]

        if env_name not in environments:
            environments[env_name] = {}
        if node_group not in environments[env_name]:
            environments[env_name][node_group] = 1
        else:
            environments[env_name][node_group] += 1


def argparser():
    """script options"""
    parser = argparse.ArgumentParser()

    args_list = parser.add_argument_group('Arguments')

    args_list.add_argument("--jelastic-hardware-node-hostname",
                           default=environ.get("JELASTIC_HARDWARE_NODE_HOSTNAME"),
                           dest="hn_hostname",
                           help="The jelastic hardware node hostname, "
                                "can be set with JELASTIC_HARDWARE_NODE_HOSTNAME env var")
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
    args_list.add_argument("--papi-token",
                           dest="papi_token",
                           default=environ.get('PAPI_TOKEN'),
                           help="Papi token")
    args_list.add_argument("--papi-hostname",
                           dest="papi_hostname",
                           default=environ.get('PAPI_HOSTNAME'),
                           help="Papi hostname (papi.(dev.)cloud-core.jahia.com)")

    return parser.parse_args()


def check_if_db_master_node(envname, node_index, jelastic_user_session):
    """
        Return True if the db node is the current cluster "master", False otherwise
    """
    url = jelastic_user_session.hostname + "/1.0/environment/control/rest/execcmdbygroup"
    command = "mysql -NB -u admin -padmin -P 6032 -h 127.0.0.1 " \
              "-e \\\"SELECT hostname FROM runtime_mysql_servers ORDER BY weight DESC LIMIT 1\\\""
    params = {
        'session': jelastic_user_session.session,
        'envname': envname,
        'nodeGroup': "proc",
        'commandList': '[{"command": "' + command + '", "params":""}]'
    }
    resp = jelastic_user_session.s.get(url, params=params)
    result = json.loads(resp.text)
    if result['result'] != 0:
        logging.error(resp.text)
        exit(1)

    return result["responses"][0]["out"] == node_index


def get_containers_infos_on_hn(
        jelastic_session,
        jelastic_hostname,
        hn_hostname,
        region,
        papi_hostname,
        papi_token
):
    """
        Returns a dict with containers in the following format
        organizationName:
            env1:
               - node_id
                 node_group
                 group_nodes_count (the number of nodes in the group the node belongs to)
    """
    environments = {}
    hardware_node_containers = None
    valid_envnames = get_jahia_cloud_envnames_from_papi(papi_hostname, papi_token)
    all_hardware_nodes = get_hardware_nodes(jelastic_session)
    for hardware_node in all_hardware_nodes:
        if hardware_node["hardwareNodeGroup"] != region or \
           hardware_node["status"] == "INFRASTRUCTURE_NODE":
            continue

        containers = get_containers(jelastic_session, hardware_node["id"])
        build_env_nodes_list(environments, containers, valid_envnames)
        if hardware_node["hostname"] == hn_hostname:
            hardware_node_containers = containers

    if not hardware_node_containers:
        print("Hardware node not found")
        exit(1)

    organizations_envs = {}
    # The class is only used to get organization names so we only need to provide papi variables
    hn_upgrade = Hardware_node_upgrade(None, None, None, None, None, None, None, None, None, None,
                                       papi_hostname, papi_token, False)
    for container in hardware_node_containers:
        # Ignore weird jelastic containers
        if "envName" not in container or \
           container["envName"] not in valid_envnames or \
           container["status"] != 1:
            continue

        env_name = container["envName"]
        node_group = container["nodeGroup"]
        organization = hn_upgrade.get_jelastic_login_from_envname(env_name)
        env_type = "jahia" if "proc" in environments[env_name].keys() else "jcustomer"
        if organization not in organizations_envs:
            organizations_envs[organization] = {}

        if env_name not in organizations_envs[organization]:
            organizations_envs[organization][env_name] = []

        pretty_node_type = node_group_translation[env_type][node_group]
        node = {
            "node_id": container["id"],
            "node_group": pretty_node_type,
            "group_nodes_count": environments[env_name][node_group]
        }
        if node["group_nodes_count"] > 1 and node_group == "sqldb":
            node_index = container["customitem"]["dockerLinks"][0]["alias"]
            account_token = jelastic_session.sysAdminSignAsUser(organization)
            user_session = Jelastic(jelastic_hostname, organization, session=account_token)
            node["master"] = check_if_db_master_node(env_name, node_index, user_session)
            user_session.signOut()

        organizations_envs[organization][env_name].append(node)

    return organizations_envs


def get_nodegroup_clusters_having_all_nodes_on_hn(nodes):
    """
        Returns the list of clusters having all their nodes on the hn
    """
    wrong_clusters = []
    nodegroup_count = {}
    for node in nodes:
        if node["group_nodes_count"] == 1:
            # Standalone node, skip it
            continue

        if node["node_group"] not in nodegroup_count:
            nodegroup_count[node["node_group"]] = 0
        nodegroup_count[node["node_group"]] += 1

        if nodegroup_count[node["node_group"]] == node["group_nodes_count"]:
            wrong_clusters.append(node["node_group"])

    return wrong_clusters


def get_env_nodes_output(nodes):
    template = "\n{color}    - {nodeGroup} {nodeId}{topology}" + NO_COLOR
    cluster_template = "{role} in a {nodeGroupCount} nodes cluster"
    nodes_output = ""
    for node in nodes:
        color = ""
        role_text = ""
        topology_text = ""
        if node["group_nodes_count"] > 1:
            if "master" in node:
                if node["master"]:
                    role_text = " Master"
                    color = RED_COLOR
                else:
                    role_text = " Slave"
            topology_text = cluster_template.format(nodeGroupCount=node["group_nodes_count"],
                                                    role=role_text)
        else:
            color = YELLOW_COLOR
            if node["node_group"] != node_group_translation["jahia"]["proc"]:
                topology_text = " standalone"

        nodes_output += template.format(color=color, nodeGroup=node["node_group"],
                                        nodeId=node["node_id"], topology=topology_text)
    return nodes_output


def display_envs(organizations_environments):
    wrong_cluster_template = "\n" + RED_COLOR + "    ** All {} nodes are on this HN **" + NO_COLOR
    env_template = "\n {color} - {env_name}:" + NO_COLOR + "{wrong_clusters}{nodes}"
    org_template = "{color}{organization}:" + NO_COLOR + "{envs_output}"

    criticity_color = [NO_COLOR, YELLOW_COLOR, RED_COLOR]
    for organization, envs in organizations_environments.items():
        org_criticity = 0
        envs_output = ""
        for env, nodes in envs.items():
            env_criticity = 0
            nodes_output = get_env_nodes_output(nodes)
            if RED_COLOR in nodes_output:
                env_criticity = 2
            elif YELLOW_COLOR in nodes_output:
                env_criticity = 1

            wrong_clusters = get_nodegroup_clusters_having_all_nodes_on_hn(nodes)
            wrong_output = ""
            if wrong_clusters:
                for wrong_nodegroup in wrong_clusters:
                    wrong_output += wrong_cluster_template.format(wrong_nodegroup)
                env_criticity = 2

            color = criticity_color[env_criticity]
            envs_output += env_template.format(color=color, env_name=env,
                                               wrong_clusters=wrong_output, nodes=nodes_output)

            if env_criticity > org_criticity:
                org_criticity = env_criticity

        color = criticity_color[org_criticity]
        print(org_template.format(color=color, organization=organization, envs_output=envs_output))


if __name__ == "__main__":
    args = argparser()

    jel_session = Jelastic(
        hostname=args.jserver,
        login=args.juser,
        password=args.jpassword,
    )
    jel_session.signIn()
    orgs_environments = get_containers_infos_on_hn(
        jel_session,
        args.jserver,
        args.hn_hostname,
        args.region,
        args.papi_hostname,
        args.papi_token,
    )
    display_envs(orgs_environments)
