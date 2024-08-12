#!/usr/bin/env python3

import argparse
from os import environ
from pylastic import Jelastic
import json
import logging
from check_before_hn_upgrade import get_hardware_nodes, \
    get_containers

LOG_FORMAT = "%(asctime)s %(levelname)s: [%(funcName)s] %(message)s"
logging.basicConfig(format=LOG_FORMAT, level=logging.INFO)

logger = logging.getLogger()


def argparser():
    """script options"""
    parser = argparse.ArgumentParser()

    args_list = parser.add_argument_group('Arguments')

    args_list.add_argument("--juser",
                           default=environ.get('JELASTIC_USER'),
                           help="The Jelastic user, can be set with JELASTIC_USER env var")
    args_list.add_argument("--jpassword",
                           default=environ.get('JELASTIC_PASSWORD'),
                           help="The Jelastic user's password, can be set with JELASTIC_PASSWORD env var")
    args_list.add_argument("--jserver",
                           default=environ.get('JELASTIC_SERVER'),
                           help="Jelastic cluster DNS, can be set with JELASTIC_SERVER env var")
    args_list.add_argument("--region",
                           default=environ.get("JELASTIC_REGION"),
                           help="Jelastic region name, can be set with JELASTIC_REGION env var")
    args_list.add_argument("--exclude",
                           default="",
                           help="(Optional, empty by default) Comma separated list of HNs that should be excluded from the plan")
    args_list.add_argument("--max-group-size",
                           default=0,
                           type=int,
                           help="(Optional, disabled by default) The maximum number of HNs per group. 0 to disable")
    args_list.add_argument("--include-infra-nodes",
                           default=False,
                           action='store_true',
                           help="(Optional, disabled by default) If you want to include the INFRASTRUCTURE nodes")

    return parser.parse_args()


def get_envs_containers_list(jel_session, hn_list):
    envs = {}
    for hn in hn_list:
        containers = get_containers(jel_session, hn["id"])
        for container in containers:
            env_name = container["envName"]
            node_group = container["nodeGroup"]
            if env_name not in envs:
                envs[env_name] = {}
            if node_group not in envs[env_name]:
                envs[env_name][node_group] = []
            envs[env_name][node_group].append(hn["hostname"])
    return envs


def get_hn_list(jel_session, region, hns_to_exclude, include_infra_nodes):
    hn_list = []
    all_hardware_nodes = get_hardware_nodes(jel_session)
    for hardware_node in all_hardware_nodes:
        if hardware_node["hardwareNodeGroup"] == region and \
        (include_infra_nodes or hardware_node["status"] != "INFRASTRUCTURE_NODE"):
            hardware_node["hostname"] = hardware_node["hostname"].split(".")[0]
            if hardware_node["hostname"] not in hns_to_exclude:
                hn_list.append(hardware_node)
    return hn_list


def generate_hn_links_dict(hn_list):
    """
        Returns a dict containing all hns with the following format
            hn1: [hn2, .., hnX],
            ...
            hnX: [hn1, .., hnX-1],
    """
    hn_links = {}
    for hn in hn_list:
        hn_links[hn["hostname"]] = []
        for hn_dest in hn_list:
            if hn_dest["hostname"] != hn["hostname"]:
                hn_links[hn["hostname"]].append(hn_dest["hostname"])

    return hn_links


def unlink_hns(hn_links, hn_list):
    """
        Unlink two HNs that cannot be upgraded simultaneously
    """
    for hn in hn_list:
        for hn_dest in hn_list:
            if hn_dest in hn_links[hn]:
                hn_links[hn].remove(hn_dest)
                hn_links[hn_dest].remove(hn)


def invalidate_links_for_environments(hn_links, environments):
    """
        Unlink HNs that cannot be upgraded simultaneously because they
        host nodes from the same environment's nodegroup
    """
    for env_name, node_groups in environments.items():
        for node_group, hns in node_groups.items():
            if len(hns) <= 1:
                continue  # If single node in node group, skip

            logger.debug("Invalidate " + str(hns) + " for " + env_name)
            unlink_hns(hn_links, hns)


def invalidate_links_for_core_nodes(hn_links, hn_list):
    """
        Unlink HNs that cannot be upgraded simultaneously because they
        are "core nodes" (PAAS-2945)
    """
    hns = [hn['hostname'] for hn in hn_list if 'virtualNetIp' in hn]
    logger.debug("Invalidate " + str(hns) + " because they are core nodes")
    unlink_hns(hn_links, hns)


def get_less_linked_hn(hn_links):
    less_linked = "none"
    links_count = 666
    for hn, links in hn_links.items():
        if len(links) < links_count:
            less_linked = hn
            links_count = len(links)
    return less_linked


def clear_hn(hn_links, hn_to_del, group):
    """
        Remove all occurences of an HN and the hn linked to him from the hn_links dict
    """
    cleaned_hn_links = {}
    linked = hn_links[hn_to_del]
    linked_to_del = group
    for hn, linked in hn_links.items():
        if hn == hn_to_del or hn in linked_to_del:  # ignore the hn to del and those linked
            continue
        cleaned_hn_links[hn] = []
        for link in linked:
            if link not in linked_to_del and link != hn_to_del:
                cleaned_hn_links[hn].append(link)

    return cleaned_hn_links


def is_optimized(hn_links):
    """
        Return True if there is no links (compatible hns) remaining. False otherwise
    """
    for hn, linked in hn_links.items():
        if len(linked) > 0:
            return False
    return True


def split_into_groups(hn_links, max_group_size):
    """
        Split hns into compatible groups
    """
    groups = []
    while not is_optimized(hn_links):
        less_linked = get_less_linked_hn(hn_links)
        logger.debug("Less linked: " + less_linked)
        group = [less_linked]
        max_size = len(hn_links[less_linked]) if max_group_size == 0 else max_group_size
        for elem in hn_links[less_linked]:
            compatible = True
            for elem_in_group in group:
                if elem not in hn_links[elem_in_group]:
                    compatible = False
                    break
            if not compatible:
                continue
            group.append(elem)
            if len(group) >= max_size:
                break

        groups.append(group)
        hn_links = clear_hn(hn_links, less_linked, group)
    for hn, linked in hn_links.items():
        groups.append([hn])

    return groups


if __name__ == "__main__":
    args = argparser()
    hns_to_exclude = [] if args.exclude == "" else args.exclude.replace(" ", "").split(",")

    jel_session = Jelastic(
        hostname=args.jserver,
        login=args.juser,
        password=args.jpassword,
    )
    jel_session.signIn()

    hn_list = get_hn_list(jel_session, args.region, hns_to_exclude, args.include_infra_nodes)
    hn_links = generate_hn_links_dict(hn_list)
    envs_conainers = get_envs_containers_list(jel_session, hn_list)

    invalidate_links_for_core_nodes(hn_links, hn_list)
    invalidate_links_for_environments(hn_links, envs_conainers)

    print("hns count:" + str(len(hn_list)))
    print("List of hns groups:")
    groups = split_into_groups(hn_links, args.max_group_size)
    for group in groups:
        print(group)
