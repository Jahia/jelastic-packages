#!/usr/bin/env python
import logging
import argparse
import os
import json
import re
import sys
from datetime import datetime

LOG_FORMAT = "%(asctime)s %(levelname)s: [%(funcName)s] %(message)s"
logging.basicConfig(format=LOG_FORMAT, level=logging.INFO, stream=sys.stdout)

AZ_RG = "paas_backup"
# AZ_CRED = "{}/.azure/cred.json".format(os.environ['HOME'])
AZ_CRED = "/tmp/azurecred.json"

def argparser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--accesskey",
                        help="the cp access key to connect")
    parser.add_argument("--secretkey",
                        help="the cp secret key to connect")
    parser.add_argument("-a", "--action",
                        help="do you want to do ?",
                        choices=['upload', 'download',
                                 'list',
                                 'addmeta', 'delmeta',
                                 'rotate'],
                        required=True)
    parser.add_argument("--bucketname",
                        help="the bucket name you want to play with",
                        required=False)
    parser.add_argument("--backupname",
                        help="the backup name you want to play with",
                        required=False)
    parser.add_argument("--displayname",
                        help="the env displayname (for metadata)",
                        required=False)
    parser.add_argument("-f", "--file",
                        help="the file you want to download or upload",
                        required=False)
    parser.add_argument("-k", "--keep",
                        help="how many backup do you want to keep",
                        type=int)
    parser.add_argument("-F", "--foreign",
                        help="if backup is from another cloud/region/role, eg: aws,eu-west-1,prod"
                        )
    parser.add_argument("-t", "--timestamp",
                        help="timestamp in format %%Y-%%m-%%dT%%H:%%M:00",
                        required=False)
    parser.add_argument("-m", "--mode",
                        help="this is a manual launch or auto launch ?",
                        choices=['auto', 'manual'])
    parser.add_argument("-p", "--progress",
                        help="show transfert progression",
                        action="store_true")
    return parser.parse_args()


def download(bucket, object_name, filename, **kwargs):
    if cp.download_file(filename, object_name=object_name, bucket=bucket):
        logging.info(r"well done \o/")
        return True
    else:
        logging.error("problem ^_^")
        return False


def upload(filename, bucket, object_name, **kwargs):
    if cp.upload_file(filename, bucket=bucket, object_name=object_name):
        logging.info("{} is now uploaded as {}:{}"
                     .format(filename, bucket, object_name))
        return True
    else:
        logging.error("A problem occured when trying to upload {} to {}:{}"
                      .format(filename, bucket, object_name))
        return False


def retention(bucket, backupname, to_keep, **kwargs):
    f = cp.folder_list(bucket=bucket)
    metabucket = kwargs['metabucket']
    uid = kwargs['uid']
    folders = []
    for e in f:  # this is for remove only auto backup for a backupname
        if re.search('{}_.*_auto/?$'.format(backupname), e):
            folders.append(e)
    if to_keep < len(folders):
        logging.info("You ask for {} backup retention but found {}"
                     .format(to_keep, len(folders)))
        to_remove = folders[:len(folders)-len(folders[-to_keep:])]
        logging.info("I should remove this: {}".format(to_remove))
        for f in to_remove:
            timestamp = re.split('_', f)[1]
            print("backupname: {}\ttimestamp: {}"
                  .format(backupname, timestamp))
            logging.info("Removing {} ({} from metadata file)"
                         .format(backupname, timestamp))
            remove_from_metadata_file(metabucket, backupname, timestamp,
                                      uid=uid)
            if cp.delete_folder(f, bucket=bucket):
                logging.info("{}:{} and his content is now deleted"
                             .format(bucket, f))
            else:
                logging.warning("{}:{} and his content cannot be deleted"
                                .format(bucket, f))
    else:
        logging.info("You ask for {} backup retention and found {}"
                     .format(to_keep, len(folders)))


def list_backup(bucket, **kwargs):
    metadatakey = "{}_backup_metadata.json".format(kwargs['uid'])
    tmpfile = "/tmp/backrest_metadata.tmp"
    try:
        aws_sm_md.download_file(tmpfile, object_name=metadatakey,
                         bucket=bucket, quiet=True)
        logging.info("The metadata file have been downloaded from {}"
                     .format(bucket))
        with open(tmpfile, 'r') as f:
            listbackups = json.load(f)
    except:
        logging.info("No metadata file yet, nothing to list")
        listbackups = {"backups": []}
    return str(json.dumps(listbackups))


def add_to_metadata_file(bucket, backupname, timestamp, mode,
                         product, version, **kwargs):
    metadatakey = "{}_backup_metadata.json".format(kwargs['uid'])
    tmpfile = "/tmp/backrest_metadata.tmp"

    if product == "dx":
        folder = "{}_{}_{}".format(backupname, timestamp, mode)
    else:
        folder = backupname

    try:
        aws_sm_md.download_file(tmpfile, object_name=metadatakey, bucket=bucket)
        logging.info("A existing metadata file have been downloaded from {}"
                     .format(bucket))
        with open(tmpfile, 'r') as f:
            listbackups = json.load(f)
    except:
        logging.info("No existing metadata file found in {}, start a new one"
                     .format(bucket))
        listbackups = {"backups": []}

    if product == 'dx':
        size = cp.folder_size(folder, bucket=kwargs['frombucket'])
    else:
        size = 1

    d = {"name": backupname,
         "timestamp": timestamp,
         "mode": mode,
         "size": size,
         "product": product,
         "version": version,
         "cloudprovider": cloudprovider,
         "region": region,
         "envrole": role
         }

    try:
        d['envname'] = os.environ['envName']
    except:
        pass
    try:
        d['displayname'] = kwargs['displayname']
    except:
        pass
    try:
        d['uid'] = kwargs['uid']
    except:
        pass

    listbackups['backups'].append(d)

    with open(tmpfile, 'w+') as tmp:
        tmp.write(json.dumps(listbackups, indent=2, sort_keys=True))

    try:
        aws_sm_md.upload_file(tmpfile, bucket=bucket, object_name=metadatakey)
        return True
    except:
        return False

def remove_from_metadata_file(bucket, backupname, timestamp, **kwargs):
    metadatakey = "{}_backup_metadata.json".format(kwargs['uid'])
    tmpfile = "/tmp/backrest_metadata.tmp"
    try:
        aws_sm_md.download_file(tmpfile, object_name=metadatakey, bucket=bucket)
        logging.info("A existing metadata file have been downloaded from {}"
                     .format(bucket))
        with open(tmpfile, 'r') as f:
            listbackups = json.load(f)
    except:
        logging.info("No metadata file yet, nothing to remove")
        return True

    for bck in listbackups['backups']:
        if bck['name'] == backupname and bck['timestamp'] == timestamp:
            listbackups['backups'].remove(bck)
            break

    with open(tmpfile, 'w+') as tmp:
        tmp.write(json.dumps(listbackups, indent=2, sort_keys=True))

    try:
        aws_sm_md.upload_file(tmpfile, bucket=bucket, object_name=metadatakey)
        return True
    except:
        return False


if __name__ == '__main__':
    args = argparser()

    if args.progress:
        show_progress = True
    else:
        show_progress = False

    if args.foreign:
        cloudprovider = args.foreign.split(',')[0]
        region = args.foreign.split(',')[1]
        role = args.foreign.split(',')[2]
        logging.info("you specify a foreign env: {} on {}"
                     .format(region, cloudprovider))
    else:
        try:
            with open('/metadata_from_HOST', 'r') as f:
                props = dict(line.strip().split('=', 1) for line in f)
                cloudprovider = props['JEL_CLOUDPROVIDER']
                if cloudprovider not in ['aws', 'azure', 'ovh']:
                    exit(1)
                region = props['JEL_REGION']
                role = props['JEL_ENV_ROLE']
        except:
            logging.error("A problem occured when reading /metadata_from_HOST file. Exiting")
            exit(1)


    object_name = "{}_{}_{}/{}".format(args.backupname, args.timestamp,
                                       args.mode, args.file)
    # cloudprovider = args.cloudprovider

    try:
        version = os.environ['DX_VERSION']
        product = 'dx'
    except:
        version = dx_product = 'undefined'

    if version == 'undefined':
        try:
            version = os.environ['UNOMI_VERSION']
            product = 'jcustomer'
        except:
            version = product = 'undefined'


    def getuid():
        try:
            uid = re.sub(r'^jc(dev|preprod|prod)(?P<uid>[0-9]+).*$',
                         r'\g<uid>',
                         args.bucketname)
        except:
            logging.error("Cannot find UID in bucketname ({})"
                          .format(args.bucketname))
            exit(1)
        return uid

    def setmetabucketname():
        return "jc{}backupmetadata".format(role)

    logging.info("You want to work with {} as cloud provider. Let's go"
                 .format(cloudprovider))
    import lib_aws as AWS
    aws_sm_md = AWS.PlayWithIt(region_name="eu-west-1", show_progress=show_progress)
    if cloudprovider == 'aws':
        import lib_aws as JC
        cp = JC.PlayWithIt(region_name=region, env=role, show_progress=show_progress)
    elif cloudprovider == 'azure' and args.action != 'list':
        import lib_azure as JC
        cp = JC.PlayWithIt(region_name=region, sto_cont_name=args.backupname.lower(),
                           rg=AZ_RG, sto_account=args.bucketname,
                           authpath=AZ_CRED, env=role)
        logging.info("I need to retreive Azure auth_file from Secret Manager")
        secret = json.loads(aws_sm_md.get_secret('paas_azure_auth_file'))['value']
        secret = json.loads(secret)
        with open(AZ_CRED, 'w') as f:
            f.write(json.dumps(secret, indent=4, sort_keys=True))
    elif cloudprovider == 'ovh':
        import lib_aws as JC
        cp = JC.PlayWithIt(region_name="eu-west-1", env=role, show_progress=show_progress)
    if args.timestamp:
        timestamp = args.timestamp
    else:
        timestamp = datetime.today().strftime('%Y-%m-%dT%H:%M:00')

    if args.action == 'upload':
        if not upload(args.file, args.bucketname, object_name):
            logging.error("Fail to upload file")
            exit(1)
        if args.keep:
            retention(args.bucketname, args.backupname, args.keep)
    elif args.action == 'download':
        if not download(args.bucketname, object_name, args.file):
            logging.error("Fail to download file")
            exit(1)
    elif args.action == 'addmeta':
        uid = getuid()
        metabucket = setmetabucketname()
        res = add_to_metadata_file(metabucket, args.backupname,
                                   timestamp, args.mode,
                                   product, version,
                                   displayname=args.displayname,
                                   uid=uid, frombucket=args.bucketname)
        if not res:
            logging.error("Fail to add metadata")
            exit(1)

    elif args.action == 'delmeta':
        uid = getuid()
        metabucket = setmetabucketname()
        res = remove_from_metadata_file(metabucket, args.backupname,
                                        timestamp, uid=uid)
        if not res:
            logging.error("Fail to delete metadata")
            exit(1)
    elif args.action == 'list':
        uid = getuid()
        metabucket = setmetabucketname()
        print(list_backup(metabucket, uid=uid))
    elif args.action == 'rotate':
        uid = getuid()
        metabucket = setmetabucketname()
        retention(args.bucketname, args.backupname, args.keep,
                  metabucket=metabucket, uid=uid)
    if os.path.exists(AZ_CRED):
       os.remove(AZ_CRED)
