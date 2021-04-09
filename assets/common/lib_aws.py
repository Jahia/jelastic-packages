#!/usr/bin/env python
import json
import logging
import os
import threading
import sys
import re
import boto3
from botocore.exceptions import ClientError

LOG_FORMAT = "%(asctime)s %(levelname)s: [%(funcName)s] %(message)s"
logging.basicConfig(format=LOG_FORMAT, level=logging.INFO, stream=sys.stdout)


class ProgressPercentage(object):
    def __init__(self, filename, source_size=None):
        self._filename = filename
        self._seen_so_far = 0
        self._lock = threading.Lock()
        if source_size is None:
            self._size = float(os.path.getsize(filename))
        else:
            self._size = source_size

    def __call__(self, bytes_amount):
        # To simplify, assume this is hooked up to a single filename
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = (self._seen_so_far / self._size) * 100
            sys.stdout.write(
                "\r%s  %s / %s  (%.2f%%)" % (
                    self._filename, self._seen_so_far, self._size,
                    percentage))
            sys.stdout.flush()


class PlayWithIt():
    def __init__(self, envname='testenv', accountID='testID',
                 region_name='eu-west-1', env='prod', accesskey=None,
                 secretkey=None, show_progress=False, **kwargs):
        self.region_name = region_name
        self.envname = envname
        self.accountID = accountID
        self.env = env
        self.accesskey = accesskey
        self.secretkey = secretkey
        self.show_progress = show_progress
        self.tags = [{'Key': 'product', 'Value': 'cloud-pass'},
                     {'Key': 'envname', 'Value': self.envname},
                     {'Key': 'env', 'Value': self.env},
                     {'Key': 'project', 'Value': 'jahia_cloud_{}'.format(self.env)}]
        self.awsid = boto3.client('sts').get_caller_identity().get('Account')
        self.iampolicy = """{{"Version": "2012-10-17",
                              "Statement": [
                                  {{"Effect": "Allow",
                                   "Action": [
                                       "s3:DeleteObjectTagging",
                                       "s3:ListBucketByTags",
                                       "s3:ListBucketMultipartUploads",
                                       "s3:GetBucketTagging",
                                       "s3:ReplicateTags",
                                       "s3:PutObjectVersionTagging",
                                       "s3:CreateBucket",
                                       "s3:ListBucket",
                                       "s3:DeleteObjectVersionTagging",
                                       "s3:PutEncryptionConfiguration",
                                       "s3:PutObject",
                                       "s3:GetObject",
                                       "s3:PutBucketTagging",
                                       "s3:PutObjectTagging",
                                       "s3:DeleteObject",
                                       "s3:DeleteBucket"
                                   ],
                                   "Resource": [
                                       "arn:aws:s3:::{bucketname}/*",
                                       "arn:aws:s3:::{bucketname}"
                                   ]
                                    }},
                                    {{
                                        "Effect": "Allow",
                                        "Action": "s3:ListAllMyBuckets",
                                        "Resource": "*"
                                    }}
                              ]
                              }}"""

    # TOOLS FUNCTIONS #########################################################
    def return_resource_session(self, resourcename):
        if self.accesskey is None and self.secretkey is None:
            session = boto3.resource(resourcename)
        else:
            session = boto3.Session(aws_access_key_id = self.accesskey,
                                    aws_secret_access_key = self.secretkey)
            session = session.resource(resourcename)
        return session

    def return_client_session(self, resourcename):
        if self.accesskey is None and self.secretkey is None:
            session = boto3.client(resourcename)
        else:
            session = boto3.Session(aws_access_key_id = self.accesskey,
                                    aws_secret_access_key = self.secretkey)
            session = session.client(resourcename)
        return session
    # BUCKET METHODES #########################################################
    def test_if_bucket_exist(self, name):
        s3 = self.return_resource_session('s3')
        bucket = s3.Bucket(name)

        if bucket.creation_date:
            logging.info("Bucket {} exist".format(name))
            return True
        else:
            logging.info("Bucket {} do not exist".format(name))
            return False

    def create_bucket(self, name):
        if self.test_if_bucket_exist(name):
            logging.warning("You try to create Bucket {} which already exist"
                            .format(name))
            return False
        s3 = self.return_resource_session('s3')
        args = {'Bucket': name}
        # bellow is because us-east-1 is not a valid LocationConstraint
        # for aws api, see https://github.com/boto/boto3/issues/125
        # TL;DR: if us-west-1 => do not specify it
        # may be to remove when it will be fixed
        if self.region_name != 'us-east-1':
            args['CreateBucketConfiguration'] = {'LocationConstraint':
                                                  self.region_name}
        # well, back to normal
        if self.env == 'prod':
            tag = [{'Key': 'project', 'Value': 'jahia_cloud_prod'}]
        else:
            tag = [{'Key': 'project', 'Value': 'jahia_cloud_dev'}]
        try:
            s3.create_bucket(**args)
            logging.info("Bucket {} is now created in region {}"
                         .format(name, self.region_name))
            b_tagging = s3.BucketTagging(name)
            set_tag = b_tagging.put(Tagging={'TagSet':tag})
        except ClientError as e:
            logging.error("Cannot create Bucket {} in region {}"
                          .format(name, self.region_name))
            logging.error(e)
            return False
        return True

    def delete_bucket(self, name):
        if not self.test_if_bucket_exist(name):
            logging.warning("You try to delete Bucket {} which do not exist"
                            .format(name))
            return False
        s3 = self.return_resource_session('s3')
        bucket = s3.Bucket(name)
        try:
            # all keys inside a bucket must be deleted before the bucket itself
            for key in bucket.objects.all():
                key.delete()
            bucket.delete()
            logging.info("Bucket {} is now deleted".format(name))
        except ClientError as e:
            logging.error("Cannot delete Bucket {}".format(name))
            logging.error(e)
            return False
        return True

    def delete_folder(self, folder, bucket=None, **kwargs):
        if not self.test_if_bucket_exist(bucket):
            logging.warning("You try to delete {} in {} which do not exist"
                            .format(folder, bucket))
            return False
        s3 = self.return_resource_session('s3')
        b = s3.Bucket(bucket)
        try:
            for obj in b.objects.filter(Prefix=folder):
                s3.Object(bucket, obj.key).delete()
                logging.info('{}:{} is now deleted'.format(bucket, obj.key))
        except ClientError as e:
            logging.error('Something going wrong wrong here')
            logging.error(e)
            return False
        return True

    def upload_file(self, file_name, bucket=None, object_name=None, **kargs):
        """Upload a file to an S3 bucket
        :param file_name: File to upload
        :param bucket: Bucket to upload to
        :param object_name: S3 objname. If not specified then file_name is used
        :return: True if file was uploaded, else False
        """
        if not self.test_if_bucket_exist(bucket):
            logging.info("You try to upload to Bucket {} which do not exist"
                         .format(bucket))
            logging.info("I will create it for you man...")
            self.create_bucket(bucket)

        # If S3 object_name was not specified, use file_name
        if object_name is None:
            object_name = file_name

        # Upload the file
        s3_client = self.return_client_session('s3')
        # s3_client = s3.client('s3')
        try:
            s3_client.upload_file(file_name, bucket, object_name,
                      Callback=ProgressPercentage(file_name) \
                              if self.show_progress else None,
                      ExtraArgs={
                          "ServerSideEncryption": "AES256"
                      })
            print('')  # just do get a new line
            logging.info("{} have been pushed to {}:{}"
                         .format(file_name, bucket, object_name))
        except ClientError as e:
            logging.error("A problem occur when pushed {} to {}:{}"
                          .format(file_name, bucket, object_name))
            logging.error(e)
            return False
        return True

    def test_if_key_exist(self, bucket, key):
        if not self.test_if_bucket_exist(bucket):
            logging.warning("You try to test if key {} exist in {} which do not exist"
                            .format(key, bucket))
            return False
        s3 = self.return_resource_session('s3')
        try:
            s3.Object(bucket, key).load()
        except ClientError as e:
            logging.error("Can't load {}:{} or key didn't exist")
            logging.error(e)
            return False
        return True

    def download_file(self, file_name, bucket=None,
                      object_name=None, quiet=False, **kargs):
        """download a file to an S3 bucket
        :param file_name: File to download
        :param bucket: Bucket to download to
        :param object_name: S3 objname. If not specified then file_name is used
        :return: True if file was downloaded, else False
        """
        if not self.test_if_bucket_exist(bucket):
            logging.warning("You try to download from {} which do not exist"
                            .format(bucket))
            return False

        # If S3 object_name was not specified, use file_name
        if object_name is None:
            object_name = file_name

        # Download the file
        s3_client = self.return_client_session('s3')
        # s3_client = s3.client('s3')
        try:
            size = s3_client.head_object(Bucket=bucket,
                                         Key=object_name)
            size = size['ResponseMetadata']['HTTPHeaders']['content-length']
            if not quiet:
                s3_client.download_file(bucket, object_name, file_name,
                            Callback=ProgressPercentage(file_name, int(size)) \
                                    if self.show_progress else None)
                print('')  # just do get a new line
            else:
                s3_client.download_file(bucket, object_name, file_name)

            logging.info("{}:{} have been downloaded to {}"
                         .format(bucket, object_name, file_name))
        except ClientError as e:
            logging.error("A problem occur when downloaded {}:{}"
                          .format(bucket, object_name))
            logging.error(e)
            return False
        return True

    def folder_list(self, bucket, **kwargs):
        s3 = self.return_client_session('s3')
        # s3 = boto3.client('s3')
        if not self.test_if_bucket_exist(bucket):
            logging.warning("You can't list folders from {} if it not exist"
                            .format(bucket))
            return False
        try:
            r = s3.list_objects_v2(Bucket=bucket, Delimiter="/")
            f = []
            for e in r['CommonPrefixes']:
                f.append(e['Prefix'])
            f.sort()
            c = len(f)
            logging.info("{} folder(s) has been found in {}: {}"
                         .format(c, bucket, str(f)))
        except ClientError as e:
            logging.error("Something went wrong when listing folder in {}"
                          .format(bucket))
            logging.error(e)
            return False
        return f

    def folder_size(self, folder, bucket=None, **kwargs):
        if not self.test_if_bucket_exist(bucket):
            logging.warning("You can't get this folder size if {} do not exist"
                            .format(bucket))
            return False
        size = 0
        s3 = self.return_client_session('s3')
        # s3 = boto3.client('s3')
        exclude_pattern = '/(metadata)$'
        try:
            keys = s3.list_objects_v2(Bucket=bucket, Prefix=folder)
            for key in keys['Contents']:
                logging.info("found {}:{} ({} b)".format(bucket, key['Key'],
                                                         key['Size']))
                # first exclude some file(s)
                if re.search(exclude_pattern, key['Key']):
                    logging.info("'{}' is matching '{}': no counting in size"
                                 .format(key['Key'], exclude_pattern))
                    continue
                size += key['Size']
        except ClientError as e:
            logging.error('Something went wrong')
            logging.error(e)
            return False
        return size



    # IAM METHODES ############################################################
    def create_iam_user(self, username, bucketname = None):
        if self.test_if_iamuser_exist(username):
            logging.warning("Trying to create IAM user {} which already exist"
                            .format(username))
            return False
        iampolicy = json.loads(self.iampolicy.format(bucketname=bucketname))
        policyname = "paas_{}_backup".format(username)
        iam = boto3.resource('iam')
        try:
            user = iam.create_user(UserName=username)
            accesskeypair = user.create_access_key_pair()
            user_policy = iam.UserPolicy(username, policyname)
            user_policy.put(PolicyDocument=json.dumps(iampolicy))
            logging.info("IAM user {} is now created".format(username))
        except ClientError as e:
            logging.error("A problem occur when created IAM user {}"
                          .format(username))
            logging.error(e)
            return False
        secretid = "paas_{}_{}_{}".format(self.env, self.accountID,
                                          self.envname)
        self.create_secret(secretid + "_ARN", user.arn)
        self.create_secret(secretid + "_AccessKey", accesskeypair.id)
        self.create_secret(secretid + "_SecretKey", accesskeypair.secret)
        return True

    def delete_iam_user(self, username):
        if not self.test_if_iamuser_exist(username):
            logging.warning("Trying to delete IAM user {} which do not exist"
                            .format(username))
            return False
        iam = boto3.client('iam')
        iamr = boto3.resource('iam')
        policyname = "paas_{}_backup".format(username)
        try:
            for r in iam.list_access_keys(UserName=username)['AccessKeyMetadata']:
                if iam.delete_access_key(UserName=username,
                                         AccessKeyId=r['AccessKeyId']):
                    logging.info("AccessKey {} for IAM user {} is now removed"
                                 .format(r['AccessKeyId'],
                                         username))
            secretid = "paas_{}_{}_{}".format(self.env, self.accountID,
                                              self.envname)
            self.delete_secret(secretid + "_ARN")
            self.delete_secret(secretid + "_AccessKey")
            self.delete_secret(secretid + "_SecretKey")
            user_policy = iamr.UserPolicy(username, policyname)
            user_policy.delete()
            iam.delete_user(UserName=username)
            logging.info("IAM user {} is now deleted".format(username))
        except ClientError as e:
            logging.error("IAM user {} can not be deleted".format(username))
            logging.error(e)
            return False
        return True

    def test_if_iamuser_exist(self, username):
        iam = boto3.client('iam')
        getone = False
        try:
            for u in iam.list_users()['Users']:
                if u['UserName'] == username:
                    getone = True
            if getone:
                logging.info("IAM user {} exist".format(username))
            else:
                logging.info("IAM user {} does not exist".format(username))
        except ClientError as e:
            logging.error("An error occur when trying to determine if {} exist"
                          .format(username))
            logging.error(e)
            return False
        if getone:
            return True
        else:
            return False

    # SECRETS METHODES ########################################################
    def get_secret(self, secretid):
        # if not self.test_if_secret_exist(secretid):
        #     logging.warning('You try to get secret {} which do not exist'
        #                     .format(secretid))
        #     return False
        sm = boto3.client('secretsmanager', region_name=self.region_name)
        try:
            r = sm.get_secret_value(SecretId=secretid)
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                logging.error("The requested secret {} was not found"
                              .format(secretid))
            elif e.response['Error']['Code'] == 'InvalidRequestException':
                logging.error("The request was invalid due to: {}".format(e))
            elif e.response['Error']['Code'] == 'InvalidParameterException':
                logging.error("The request had invalid params: {}".format(e))
            return False
        else:
            if 'SecretString' in r:
                return r['SecretString']
            else:
                return r['SecretBinary']

    def create_secret(self, secretid, secretvalue):
        if self.test_if_secret_exist(secretid):
            logging.warning('You try to create secret {} which already here'
                            .format(secretid))
            return False
        sm = boto3.client('secretsmanager', region_name=self.region_name)
        try:
            sm.create_secret(Name=secretid, SecretString=secretvalue,
                             Tags=self.tags)
        except ClientError as e:
            logging.error("Something goes wrong when creating secret {}: {}"
                          .format(secretid, e))
            return False
        else:
            logging.info("The secret {} is now created".format(secretid))
        return True

    def test_if_secret_exist(self, secretid):
        sm = boto3.client('secretsmanager', region_name=self.region_name)
        try:
            sm.describe_secret(SecretId=secretid)
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                logging.info("The requested secret {} was not found"
                             .format(secretid))
                return False
        else:
            return True

    def delete_secret(self, secretid):
        if not self.test_if_secret_exist(secretid):
            logging.error('You try to delete secret {} chich do not exist'
                          .format(secretid))
            return False
        sm = boto3.client('secretsmanager', region_name=self.region_name)
        try:
            sm.delete_secret(SecretId=secretid,
                             ForceDeleteWithoutRecovery=True)
        except ClientError as e:
            logging.error("Something goes wrong when deleting secret {}i: {}"
                          .format(secretid, e))
            return False
        else:
            logging.info('Secret {} is now deleted'.format(secretid))
            return True
