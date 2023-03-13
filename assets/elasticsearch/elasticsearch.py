#!/usr/bin/env python3
import logging
import argparse
import json
import sys
import lib_aws as AWS

LOG_FORMAT = "%(asctime)s %(levelname)s: [%(funcName)s] %(message)s"
logging.basicConfig(format=LOG_FORMAT, level=logging.INFO, stream=sys.stdout)

def argparser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucketname",
                        help="the bucket name you want to play with",
                        required=False)
    parser.add_argument("--backupname",
                        help="the backup name you want to play with",
                        required=False)
    parser.add_argument("-c", "--cloudprovider",
                        help="the backup cloudprovider",
                        required=True)
    parser.add_argument("-o", "--operation",
                        help="backup or restore",
                        required=True)
    return parser.parse_args()


if __name__ == '__main__':
    args = argparser()
    try:
        with open('/metadata_from_HOST', 'r') as f:
            # These variables are required to create AWS resources,
            # but are not used in case of restore
            props = dict(line.strip().split('=', 1) for line in f)
            region = props['JEL_REGION']
            role = props['JEL_ENV_ROLE']
    except:
        logging.error("A problem occured when reading /metadata_from_HOST file. Exiting")
        exit(1)

    if args.cloudprovider == "aws" and args.operation == "backup":
        # Create bucket if it does not exist
        cp = AWS.PlayWithIt(region_name=region, env=role)
        if not cp.test_if_bucket_exist(args.bucketname):
            cp.create_bucket(args.bucketname)
    elif args.cloudprovider == "ovh" and args.operation == "backup":
        # Create bucket if it does not exist
        cp = AWS.PlayWithIt(region_name="eu-west-1", env=role)
        if not cp.test_if_bucket_exist(args.bucketname):
            cp.create_bucket(args.bucketname)
