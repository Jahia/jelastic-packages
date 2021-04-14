#!/usr/bin/env python
#
import logging
import os
import sys
import adal
from azure.common.client_factory import get_client_from_cli_profile
from azure.common.client_factory import get_client_from_auth_file
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.mgmt.storage.models import StorageAccountCreateParameters
from azure.mgmt.storage.models import (StorageAccountCreateParameters,
                                       StorageAccountUpdateParameters,
                                       Sku,
                                       SkuName,
                                       Kind)

from azure.storage.blob import BlockBlobService
from msrestazure.azure_active_directory import AdalAuthentication
from msrestazure.azure_cloud import AZURE_PUBLIC_CLOUD

# client = get_client_from_cli_profile(ComputeManagementClient)


LOG_FORMAT = "%(asctime)s %(levelname)s: [%(funcName)s] %(message)s"
logging.basicConfig(format=LOG_FORMAT, level=logging.INFO, stream=sys.stdout)

RG = "testlfu"
STO_ACCOUNT = "testlfu"

class PlayWithIt():
    def __init__(self, envname='testenv', accountID='testID',
                 region_name='us-central-1', env='prod',
                 accesskey=None, secretkey=None, **kwargs):
        self.envname = envname
        self.accountID = accountID
        self.region_name = region_name
        self.env = env
        self.accesskey = accesskey
        self.secretkey = secretkey
        self.sto_cont_name = kwargs['sto_cont_name']
        self.sto_account = kwargs['sto_account']
        self.rg = kwargs['rg']
        self.authpath = kwargs['authpath']
        self.tags = []

    def return_session(self, classname, method="authfile"):
        try:
            if method == "client":
                session = get_client_from_cli_profile(classname)
            elif method == "authfile":
                session = get_client_from_auth_file(classname,
                                                    auth_path=self.authpath)
        except:
            logging.error("Cannot get a session (class: {}, method: {})"
                          .format(classname, method))
            return False
        return session

    def get_sto_account_key(self):
        client = self.return_session(StorageManagementClient)
        sto_keys = client.storage_accounts.list_keys(self.rg, self.sto_account)
        sto_keys = {v.key_name: v.value for v in sto_keys.keys}
        return sto_keys['key1']

    def check_if_sto_name_is_ok(self):
        cl = self.return_session(StorageManagementClient)
        resp = cl.storage_accounts.check_name_availability(self.sto_account)
        if resp.reason:
            logging.error(resp.message)
            return resp.name_available
        else:
            logging.info(resp)
            return True

    def check_if_sto_acc_exist(self):
        cl = self.return_session(StorageManagementClient)
        for sto in cl.storage_accounts.list_by_resource_group(self.rg):
            if sto.name == self.sto_account:
                logging.info("Storage Account {} already exist in {}"
                             .format(self.sto_account, self.rg))
                return True
        logging.info("Storage Account {} do not exist in {}"
                        .format(self.sto_account, self.rg))
        return False

    def create_sto_container(self):
        key = self.get_sto_account_key()
        try:
            blob = BlockBlobService(self.sto_account, key)
        except:
            return False
        return blob.create_container(self.sto_cont_name)

    def delete_sto_container(self):
        key = self.get_sto_account_key()
        try:
            blob = BlockBlobService(self.sto_account, key)
        except:
            return False
        return blob.delete_container(self.sto_cont_name)

    def create_sto_account(self):
        if self.check_if_sto_acc_exist():
            return False
        if self.env == 'prod':
            tag = {'project': 'jahia_cloud_prod'}
        else:
            tag = {'project': 'jahia_cloud_dev'}
        client = self.return_session(StorageManagementClient)
        sto_async_operation = client.storage_accounts.create(
            self.rg, self.sto_account,
            StorageAccountCreateParameters(
                sku=Sku(name=SkuName.standard_ragrs),
                kind=Kind.storage_v2,
                location=self.region_name,
                tags=tag
            )
        )
        if sto_async_operation.result():
            logging.info("Storage {} is now created in {} on location {}"
                         .format(self.sto_account, self.rg,
                                 self.region_name))
            logging.debug(sto_async_operation.result())
            return True
        else:
            logging.error("Cannot create Storage Account {} in {}"
                          .format(self.sto_account, self.rg))
            logging.error(sto_async_operation.result())
            return False

    def delete_sto_account(self):
        client = self.return_session(StorageManagementClient)
        try:
            sto_async_operation = client.storage_accounts.delete(
                self.rg, self.sto_account)
            logging.info("Storage {} is now deleted on {}"
                         .format(self.sto_account, self.rg))
        except:
            logging.error("Cannot delete Storage Account {} on {}")
            return False
        return True

    def test_if_obj_exist(self, object_name=None):
        sto_key = self.get_sto_account_key()
        blob = BlockBlobService(self.sto_account, sto_key)
        return blob.exists(self.sto_cont_name, object_name)


    def upload_file(self, file_name, object_name=None, **kwargs):
        if not self.check_if_sto_acc_exist():
            logging.info("I will create storage account {} in rg {} for you"
                         .format(self.sto_account, self.rg))
            self.create_sto_account()
        if not self.test_if_obj_exist(object_name=self.sto_cont_name):
            logging.info("I will create {}:{}:{} for you"
                         .format(self.rg, self.sto_account,
                                 self.sto_cont_name))
            self.create_sto_container()

        # if blob object name was not specified, use file_name
        if object_name is None:
            object_name = file_name

        sto_key = self.get_sto_account_key()
        blob = BlockBlobService(self.sto_account, sto_key)
        try:
            blob.create_blob_from_path(self.sto_cont_name, object_name,
                                       file_name)
            logging.info("File {} successfully uploaded to {}:{}:{}"
                         .format(file_name, self.sto_account,
                                 self.sto_cont_name, object_name))
        except:
            logging.error("Cannot upload {} to {}:{}:{}"
                          .format(file_name, self.sto_account,
                                  self.sto_cont_name, object_name))
            return False
        return True

    def delete_folder(self, folder, **kwargs):
        sto_key = self.get_sto_account_key()
        blob = BlockBlobService(self.sto_account, sto_key)
        folders = [b for b in blob.list_blobs(self.sto_cont_name)
                   if b.name.startswith(folder)]
        if len(folders) > 0:
            try:
                for f in folders:
                    blob.delete_blob(self.sto_cont_name, f.name)
                    logging.info("{}:{}:{} is now deleted"
                                 .format(self.sto_account, self.sto_cont_name,
                                        f.name))
            except:
                logging.error("Error while deleting {}:{}:{}"
                              .format(self.sto_account, self.sto_cont_name,
                                      f.name))
                return False
        return True

    def folder_size(self, folder, **kwargs):
        sto_key = self.get_sto_account_key()
        blob = BlockBlobService(self.sto_account, sto_key)
        objects = [b for b in blob.list_blobs(self.sto_cont_name)
                   if b.name.startswith(folder + '/')]
        size = 0
        if len(objects) > 0:
            try:
                for f in objects:
                    size = size + f.properties.content_length
            except:
                logging.error("Something bad happened")
        return size

    def folder_list(self, **kwargs):
        sto_key = self.get_sto_account_key()
        blob = BlockBlobService(self.sto_account, sto_key)
        fl = []
        for obj in blob.list_blob_names(self.sto_cont_name):
            backup_root_dir = obj.split('/')[0]
            if backup_root_dir != 'metadata' and backup_root_dir not in fl:
                fl.append(backup_root_dir)
        fl.sort
        return fl

    def download_file(self, file_name, object_name=None,
                      quiet=None, **kwargs):
        sto_key = self.get_sto_account_key()
        blob = BlockBlobService(self.sto_account, sto_key)
        try:
            blob.get_blob_to_path(self.sto_cont_name, object_name,
                                       file_name)
            logging.info("File {} successfully downloaded from {}:{}"
                         .format(file_name, self.sto_account,
                                 self.sto_cont_name))
        except:
            logging.error("Cannot download {}:{}:{}"
                          .format(self.sto_account, self.sto_cont_name,
                                  object_name))
            os.remove(file_name)
            return False
        return True

