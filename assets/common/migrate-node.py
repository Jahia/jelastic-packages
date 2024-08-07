#!/usr/bin/env python3

import argparse
import logging
import os
from sys import exit
import json
from pylastic import Jelastic

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
    jel_stuff.add_argument("-u", "--juser",
                           default=os.environ.get('juser'),
                           dest="juser",
                           help="the jelastic admin user (default: %(default)s)")
    jel_stuff.add_argument("-p", "--password",
                           default=os.environ.get('jpassword'),
                           dest="jpassword",
                           help="the jelastic user's password (default: %(default)s)")
    jel_stuff.add_argument("-j", "--jserver",
                           dest="jserver",
                           default=os.environ.get('jserver'),
                           help="Jelastic Cluster DNS (default: %(default)s)")
    jel_stuff.add_argument("-m", "--user-mail",
                           dest="user_mail",
                           required=True,
                           help="User owning the node to migrate mail")
    jel_stuff.add_argument("-e", "--envname",
                           dest="envname",
                           required=True,
                           help="Environment name owning the node to migrate")
    jel_stuff.add_argument("-n", "--node-id",
                           dest="node_id",
                           required=True,
                           help="Id of the node to migrate")
    jel_stuff.add_argument("-d" ,"--dest-hn",
                           dest="dest_hn",
                           required=True,
                           help="The hardware node to migrate the node to")
    jel_stuff.add_argument("-t" ,"--tag",
                           dest="tag",
                           default="main",
                           help="The tag/branch/commit to use. Default is main")

    return parser.parse_args()


def migrate_nodes(admin_sess, node_id, dest_hn):
    url = admin_sess.hostname + "/1.0/administration/cluster/rest/migratenode"
    params = {
        'session': admin_sess.session,
        'appid': 'cluster',
        'nodeid': node_id,
        'hdnodeid': dest_hn,
        "isOnline": False
    }
    resp = admin_sess.s.get(url, params=params)

    if json.loads(resp.text)['result'] != 0:
        logging.error("Cannot migrate node. Error:" + str(resp.text))
        exit(1)


def run_migration_events_package(juser_sess, tag, node_id, step="post"): # step must match "pre" or "post"
    settings = {
        "step": step,
        "nodeId": node_id
    }
    package = "https://raw.githubusercontent.com/Jahia/jelastic-packages/" + tag + "/packages/common/migrate-node-events.yml"
    resp = juser_sess.devScriptEval(package, args.envname, settings=settings)

    if json.loads(resp.text)["response"]['result'] != 0:
        logging.error("Failed to run " + step + " migration package. Error:" + str(resp.text))
        exit(1)

if __name__ == "__main__":
    args = argparser()

    JEL_SESS = Jelastic(hostname=args.jserver, login=args.juser, password=args.jpassword)
    JEL_SESS.signIn()

    juser_token = JEL_SESS.sysAdminSignAsUser(args.user_mail)
    juser_sess = Jelastic(hostname=args.jserver, login=args.user_mail,
                          session=juser_token)

    print("Running pre-migration step")
    run_migration_events_package(juser_sess, args.tag, args.node_id, "pre")
    print("Migrating node")
    migrate_nodes(JEL_SESS, args.node_id, args.dest_hn)
    print("Running post-migration step")
    run_migration_events_package(juser_sess, args.tag, args.node_id, "post")

    juser_sess.signOut()
    JEL_SESS.signOut()
