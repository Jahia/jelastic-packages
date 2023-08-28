# Jelastic Packages

## Overview

This repository contains all manifests and assets used for the Jahia Cloud PaaS platform.

It's a merge of what was in previous _paas_jelastic\_\*_ and _cloud-scripts_ repos.

## Rules

Here are some rules that should be observed:

- packages in `packages/jahia` folder should apply to Jahia envs, and so on
- packages should contain minimum logic, most logic should be deported to actions defined in mixins (for reusability)
  - as a consequence, assets should only be referenced by actions (package > action > asset)
- actions should not rely on global variables
- keep mixin files dependencies to the bare minimum
  - when one mixin depends on another, it must be specified in a comment on top of the file

## Structure

```
.
├── assets
│   ├── common
│   ├── database
│   ├── elasticsearch
│   ├── haproxy
│   ├── jahia
│   └── jcustomer
├── conf
├── mixins
└── packages
    ├── common
    ├── jahia
    ├── jcustomer
    ├── misc
    └── one-shot
```

_Assets_ are files that are used by manifests. They can be configuration files, scripts, images...

The _conf_ folder contains a global configuration file per environment (dev, preprod, prod) that will
be used to create `cloud_conf` nodegroup data on cp nodes.

_Mixins_ files contain Jelastic actions used in diffrerent manifests (used for reusability as manifests can
be imported in any manifest).

_Packages_ (or _Manifests_) are YAML files run on Jelastic infrastructure to create/update/delete resources.

### `deps.py`

This is a script that allows you to do:

- checks
  - check that the actions used by manifest(s) are well defined
    ```console
     $ ./deps.py check packages/one-shot/paas-1982-fix-jessionid.yml
    for manifest './packages/one-shot/paas-1982-fix-jessionid.yml, section 'actions':
    		[checkJahiaVersion] is an action from ['./packages/one-shot/paas-1982-fix-jessionid.yml']
    				[getJahiaVersion] is an action from ['./mixins/jahia.yml']
    				[if] is a keyword
    						[return] is a jelastic keyword with args
    				[getJahiaVersion] is an action from ['./mixins/jahia.yml']
    				[if] is a keyword
    						[return] is a jelastic keyword with args
    		[temporaryWorkaround] is an action from ['./packages/one-shot/paas-1982-fix-jessionid.yml']
    				[if] is a keyword
    					[api] is a jelastic keyword with args
    				[if] is a keyword
    					[api] is a jelastic keyword with args
    for manifest './packages/one-shot/paas-1982-fix-jessionid.yml, section 'events':
    no events detected
    for manifest './packages/one-shot/paas-1982-fix-jessionid.yml, section 'onInstall':
    	[checkJahiaVersion] is an action from ['./packages/one-shot/paas-1982-fix-jessionid.yml']
    	[temporaryWorkaround] is an action from ['./packages/one-shot/paas-1982-fix-jessionid.yml']
    	[foreach] is a keyword
    		[temporaryWorkaround] is an action from ['./packages/one-shot/paas-1982-fix-jessionid.yml']
    ```
    If a called action can't be found, you will have something like this:
    ```console
     $ ./deps.py check packages/one-shot/paas-1982-fix-jessionid.yml
    for manifest './packages/one-shot/paas-1982-fix-jessionid.yml, section 'actions':
            [checkJahiaVersion] is an action from ['./packages/one-shot/paas-1982-fix-jessionid.yml']
                    [getJahiaVersion] is an action from ['./mixins/jahia.yml']
                    [WellStillNotDefinedAnywhere] is an action not defined anywhere !
                    [if] is a keyword
                            [return] is a jelastic keyword with args
                    [getJahiaVersion] is an action from ['./mixins/jahia.yml']
                    [WellStillNotDefinedAnywhere] is an action not defined anywhere !
                    [if] is a keyword
                            [return] is a jelastic keyword with args
            [temporaryWorkaround] is an action from ['./packages/one-shot/paas-1982-fix-jessionid.yml']
                    [if] is a keyword
                        [api] is a jelastic keyword with args
                    [if] is a keyword
                        [api] is a jelastic keyword with args
    for manifest './packages/one-shot/paas-1982-fix-jessionid.yml, section 'events':
    no events detected
    for manifest './packages/one-shot/paas-1982-fix-jessionid.yml, section 'onInstall':
        [checkJahiaVersion] is an action from ['./packages/one-shot/paas-1982-fix-jessionid.yml']
        [temporaryWorkaround] is an action from ['./packages/one-shot/paas-1982-fix-jessionid.yml']
        [IMPrettySureThisActionIsOnMyMixins] is an action not defined anywhere !
        [foreach] is a keyword
            [temporaryWorkaround] is an action from ['./packages/one-shot/paas-1982-fix-jessionid.yml']
    ─────────────────────────────────────────────────────────────────────────────────────────────────────────
    ❌'WellStillNotDefinedAnywhere' from ./packages/one-shot/paas-1982-fix-jessionid.yml isn't defined
    ❌'IMPrettySureThisActionIsOnMyMixins' from ./packages/one-shot/paas-1982-fix-jessionid.yml isn't defined
    ```
  - check for duplicated actions in mixins files
    ```console
    $ ./deps.py mixins_duplicates
    ❌'setJournaldLimit' is duplicated: ['./mixins/common.yml', './mixins/jcustomer.yml']
    ```
- graph dependencies tree from manifest(s)
  ```console
  $ ./deps.py graph -q -o AS_manifest_deps.dot ./packages/jahia/augmented-search-*.yml
  ```
- (really) simple search
  ```console
  $ ./deps.py search --name checkJahiaHealth
  Building data... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 0:00:00
   id    name              kind    section    call  called_by                                                          parent  childs  legit
   99    checkJahiaHealth  action  actions    146   1056,1091,937,1033,1003,1037,974,1165,1104,1073,434,1138,948,1119  86              true
   937   checkJahiaHealth  action  onInstall  99                                                                       393             true
   948   checkJahiaHealth  action  onInstall  99                                                                       398             true
   974   checkJahiaHealth  action  onInstall  99                                                                       410             true
   1003  checkJahiaHealth  action  onInstall  99                                                                       425             true
   1033  checkJahiaHealth  action  onInstall  99                                                                       432             true
   1037  checkJahiaHealth  action  onInstall  99                                                                       444             true
   1056  checkJahiaHealth  action  onInstall  99                                                                       454             true
   1073  checkJahiaHealth  action  onInstall  99                                                                       461             true
   1091  checkJahiaHealth  action  onInstall  99                                                                       472             true
   1104  checkJahiaHealth  action  onInstall  99                                                                       475             true
   1119  checkJahiaHealth  action  onInstall  99                                                                       484             true
   1138  checkJahiaHealth  action  onInstall  99                                                                       498             true
   1165  checkJahiaHealth  action  onInstall  99                                                                       515             true
  ```

In order for the script to work, you need to have:

- `graphviz` and its development files
- gcc
- python 3.8 or higher
  then do a `pip install -r deps_requirements.txt`

#### `PRE-COMMIT` hook

Here is an exemple of what you can have in order to automatically check before committing:

```bash
#!/usr/bin/env bash
echo "PRE-COMMIT check for ${PWD##*/}"

manifest_involved=$(git diff --cached --name-only | grep -v "^.*/?assets/" | grep -E "(mixins|packages)*ya?ml")
mixin_involved=$(echo "${manifest_involved}" | grep "^mixins/")
error=0

if [ -n "${manifest_involved}" ]; then
    if ! (./deps.py check -q ${manifest_involved}); then
        ((error++))
    fi
fi

if [ -n "${mixin_involved}" ]; then
    if ! (./deps.py mixins_duplicates); then
        ((error++))
    fi
fi

echo

if [ $error -gt 0 ]; then
    echo "Can't commit, you must fix previous error(s) before..."
    exit $error
fi

echo "Looks ok, commit can occure..."
```

## Environments

### Infrasctructure overview

#### Jahia env

A Jahia environment contains:

- One or several Haproxy nodes
- Tomcat nodes (each node has a clusterized proxysql instance):
  - One or several Jahia Browsing nodes
  - One Jahia Processing node
- Either one single MariaDB node or three MariaDB nodes clusterized with Galera

Requests on the domain name target the Haproxy node(s) which route them to the Browsing node(s), where a session affinity is set in case there are multiple ones.

The processing node won't receive any request from client as browsing nodes are the only ones defined in Haproxy configuration.

In case of a Galera cluster, queries are all executed on the same MariaDB master node, which is replicated to the other ones.

#### jCustomer env

A jCustomer environment contains:

- One or several jCustomer nodes

Each jCustomer environment is linked to an Elastic Cloud deployment, either dedicated or mutualized.

### Docker images

#### Jahia env

Images used by Jahia environment nodes:

| Node type        | Docker image          |
| ---------------- | --------------------- |
| Haproxy          | jelastic/haproxy      |
| Jahia Browsing   | jahia/jahiastic-jahia |
| Jahia Processing | jahia/jahiastic-jahia |
| MariaDB          | jelastic/mariadb      |

#### jCustomer env

Images used by jCustomer environment nodes:

| Node type     | Docker image              |
| ------------- | ------------------------- |
| jCustomer     | jahia/jahiastic-jcustomer |
| Elasticsearch | jahiadev/elasticsearch    |

## Packages

### common

#### common/auto_backup.yml

Creates an autobackup environment to handle schedule backups.

| parameter               | comment                                     |
| ----------------------- | ------------------------------------------- |
| masterLogin             | login used to connect to Jelastic           |
| masterPwd               | password used to connect to Jelastic        |
| awsAccess               | AWS Access Key                              |
| awsSecret               | AWS Secret Key                              |
| dd_api_key              | Datadog Apikey to use                       |
| paas_autobackup_version | The tag of the paas-autobackup image to use |

#### common/backup.yml

Backups an environment.

Works both for jahia (files + database, Haproxy conf) and jCustomer (Elasticsearch indices).

| parameter   | comment                                          |
| ----------- | ------------------------------------------------ |
| backup_name | Backup Name                                      |
| timestamp   | The backup timestamp in format %Y-%m-%dT%H:%M:00 |
| retention   | How many auto-backups do you want to keep        |
| backtype    | Is this a manual or auto backup                  |

#### common/create-elasticsearch-account.yml

Creates an Elasticsearch account.

| parameter   | comment                                            |
| ----------- | -------------------------------------------------- |
| accountName | New account name                                   |
| password    | Password of the new account                        |
| rolesList   | The list of Kibana roles to add to the new account |

#### common/create-kibana-role.yml

Creates a role on Kibana.

| parameter         | comment                            |
| ----------------- | ---------------------------------- |
| roleName          | New role name                      |
| esPermissions     | Permissions at ElasticSearch level |
| kibanaPermissions | Permissions at Kibana level        |

#### common/create-kibana-space.yml

Creates a space on Kibana.

| parameter | comment        |
| --------- | -------------- |
| spaceName | New space name |

#### common/delete-elasticsearch-account.yml

Deletes an Elasticsearch account.

| parameter   | comment                       |
| ----------- | ----------------------------- |
| accountName | Name of the account to delete |

#### common/delete-kibana-role.yml

Deletes a role on Kibana.

| parameter | comment                    |
| --------- | -------------------------- |
| roleName  | Name of the role to delete |

#### common/delete-kibana-space.yml

Deletes a space on Kibana.

| parameter | comment                     |
| --------- | --------------------------- |
| spaceName | Name of the space to delete |

#### common/restore.yml

Restores a backup. Works both for jahia (files + database, Haproxy conf) and jCustomer (Elasticsearch indices).

| pame           | comment                                          |
| -------------- | ------------------------------------------------ |
| backup_name    | Backup Name                                      |
| cloud_source   | Enviroment source cloud provider                 |
| region_source  | Enviroment source cloud provider region          |
| uid_source     | Environment owner's UID                          |
| envrole_source | Enviroment source mode (dev or prod)             |
| timestamp      | The backup timestamp in format %Y-%m-%dT%H:%M:00 |
| backtype       | Is this a manual or auto backup                  |

#### common/start-nodes.yml

Starts nodes individually (nothing is done at environment level).

| pame         | comment                                                                                               |
| ------------ | ----------------------------------------------------------------------------------------------------- |
| nodesToStart | Nodes id to stop with the following format: {"nodeGroup1": ["XXXX"], "nodeGroup2": ["YYYYY", "ZZZZ"]} |
| dryRun       | Enables dry-run                                                                                       |

#### common/stop-nodes.yml

Stops nodes individually (nothing is done at environment level).

| pame        | comment                                                                                               |
| ----------- | ----------------------------------------------------------------------------------------------------- |
| nodesToStop | Nodes id to stop with the following format: {"nodeGroup1": ["XXXX"], "nodeGroup2": ["YYYYY", "ZZZZ"]} |
| dryRun      | Enables dry-run                                                                                       |

#### common/update-datadog-agent.yml

This manifest allow to update `datadog-agent` package to the latest version.

#### common/update-datadog-apikey.yml

This manifest allow to update a env's DataDog API key.

The script will check that the key currently used is the one you think before set the new key.

| parameter            | comment                |
| -------------------- | ---------------------- |
| currentDataDogApikey | The key currently used |
| newDataDogApikey     | The new API key yo use |

### jahia

#### jahia/augmented-search-install.yml

Installs and configures Augmented Search for the environment.

This involves triggering the creation of the Elastic Cloud deployment if a dedicated one
is needed, and the creation of the Elastic Cloud account/role.

#### jahia/augmented-search-uninstall.yml

Uninstalls and clean Augmented Search from the environment.

This involves triggering the deletion of the Elastic Cloud deployment if a dedicated one
was used, and the deletion of the Elastic Cloud account/role and indices.

#### jahia/check_jexperience.yml

Check if a jahia env is alowed to talk with is linked jcustomer env.

#### jahia/configure-apm.yml

Enables or disables the Datadog APM on the Tomcat nodes.

| parameter  | comment                                        |
| ---------- | ---------------------------------------------- |
| apmEnabled | `true` or `false` to enable or disable the APM |

#### jahia/consistency-check.yml

Checks the consistency of a Jahia environment
(to make sure that required modules are installed and running with the correct version).

#### jahia/galera-restart-nodes.yml

This manifest will gracefuly restart all galera nodes with the jahia's Full ReadOnly mode enabled.

#### jahia/install.yml

The base JPS, called by Jahia Cloud to create an environment.

Takes as parameters:

| parameter          | comment                                                                                  |
| ------------------ | ---------------------------------------------------------------------------------------- |
| productVersion     | Jahia version (eg: `8.0.2.0`)                                                            |
| rootpwd            | Jahia root password                                                                      |
| haproxyNodeCount   | Number of HAProxy nodes                                                                  |
| browsingNodeCount  | Number of Jahia browsing nodes                                                           |
| browsingNodeSize   | Size of Jahia browsing nodes (`small`, `medium` or `large`)                              |
| processingNodeSize | Size of Jahia processing node (`small`, `medium` or `large`)                             |
| sqldbNodeCount     | Number of MariaDB nodes                                                                  |
| sqldbNodeSize      | Size of MariaDB nodes (`small`, `medium` or `large`)                                     |
| shortdomain        | Environment name                                                                         |
| ddogApikey         | Datadog Apikey to use                                                                    |
| jahiaDockerImage   | Hidden settings for use a docker image instead of a tag of the jahia's jelastic template |
| dockerTagSuffix    | Suffix to add to the Docker tag                                                          |
| vaultRoleId        | Vault's Role Id to use                                                                   |
| vaultSecretId      | Vault Role Id secret to use                                                              |
| vaultClusterUrl    | The Vault server to use                                                                  |
| papiHostname       | Papi's hostname                                                                          |
| papipapiApiVersion | Papi's API version                                                                       |
| papiEnvId          | The Environment ID on Papi                                                               |

#### jahia/ipsec.yml

This manifest will create or update a Strongswan IPSec connection on each tomcat's nodes.

| parameter       | comment                                                           |
| --------------- | ----------------------------------------------------------------- |
| ipsec_should_be | Boolean.<br>Tell if the previous connection should be up or down. |

#### jahia/jahia-full-read-only.yml

The manifest will enable or disable Jahia's Full ReadOnly mode.

| parameter | comment  |
| --------- | -------- |
| enableFRO | Boolean. |

#### jahia/jahia-rolling-redeploy.yml

This manifest will perform a rolling redeployment of all Jahia nodes (cp & proc).

Be aware that is it not a simple restart, the Tomcat nodes are redeployed.

#### jahia/jahia-rolling-restart.yml

This manifest will perform a rolling restart of all Jahia nodes (cp & proc).

Be aware that is it not a redeployment, only tomcat services are restarted.

#### jahia/link-to-customer.yml

This manifest is launched against a Jahia env and will link it to a jCustomer environment by installing and configure _jExperience_ module as well as putting a metadata `envLink` on nodegroups _proc_ and _cp_. It also allow Jahia env tomcat's IPs in _jCustomer_ configuration.

| parameter | comment                                                  |
| --------- | -------------------------------------------------------- |
| unomienv  | The jCustomer env to be linked to the targeted Jahia env |

#### jahia/manage-auth-basic.yml

Enables or disables Basic Authentication at Haproxy level.

| parameter | comment                                       |
| --------- | --------------------------------------------- |
| enable    | Boolean.<br>Enable or disable the Auth Basic. |
| login     | User name to use.                             |
| pwd       | Password to use.                              |

#### jahia/redeploy-galera-nodes.yml

This manifest will redeploy all galera nodes with the jahia's Full ReadOnly mode enabled.

| parameter       | comment                                                                  |
| --------------- | ------------------------------------------------------------------------ |
| targetDockerTag | Jelastic Mariadb-dockerized template tag to use.<br>(default: `10.4.13`) |

#### jahia/reset-haproxy-backends.yml

This will reset backends on Haproxy.

#### jahia/rewrite-rules.yml

This will add customer's custom rule to HAProxy configuration.

| parameter | comment                                                                   |
| --------- | ------------------------------------------------------------------------- |
| md5sum    | For compare the rules at Cloud's front level and what is stored in Vault. |

#### jahia/set-galera-master.yml

Changes the Galera master node.

| parameter | comment                              |
| --------- | ------------------------------------ |
| nodeIndex | Node index of the new master (1,2,3) |

#### jahia/set-jahia-root-password.yml

Prepare a jahia's env root password update by setting a file on the processing node. Customers will still have to restart the processing node for being effective.

| parameter | comment              |
| --------- | -------------------- |
| rootpwd   | The password to set. |

#### jahia/set-jahia-tools-password.yml

Prepare a jahia's env _/tools_ password update on each tomcat nodes. Customers will still have to restart all tomcat nodes for being fully effective.

| parameter | comment              |
| --------- | -------------------- |
| tools_pwd | The password to set. |

#### jahia/set-jcustomer-password-in-jahia.yml

This manifest will update the _jExperience_ module's configuration with the provided password.

| parameter | comment                                                 |
| --------- | ------------------------------------------------------- |
| pwd_b64   | The password _jExperience_ have to use (base64 encoded) |

#### jahia/unlink-jahia-jcustomer.yml

Breaks the link between a Jahia and jCustomer environment.

| parameter          | comment                                                                                 |
| ------------------ | --------------------------------------------------------------------------------------- |
| isUnomiEnvDeletion | `true` if the jCustomer environment is being deleted (OPTIONAL, default value is false) |
| jCustomerEnv       | Linked jCustomer env (OPTIONAL, if not set then the envname will be retrieved)          |
| jahiaEnvStatus     | Jahia Env Status (Eg- 1(running), 2(stopped))                                           |

#### jahia/update-events.yml

Describes actions associated to the Jelastic events on the environment.

#### jahia/upgrade.yml

This _upgrade_ package aims at upgrading the version of Jahia by redeploying Jahia nodes with the target Jahia version tag.

| parameter       | comment               |
| --------------- | --------------------- |
| targetVersion   |                       |
| dockerTagSuffix | The Docker tag suffix |

### jcustomer

#### jcustomer/configure-apm.yml

Enables or disables the Datadog APM on the Tomcat nodes.

| parameter  | comment                                        |
| ---------- | ---------------------------------------------- |
| apmEnabled | `true` or `false` to enable or disable the APM |

#### jcustomer/geolite-database-update.yml

Updates the Geolite database with the most up-to-date version from Maxmind website.

Be aware that this will restart jCustomer nodes.

#### jcustomer/geolite-index-and-aliases-update.yml

Updates the Geolite indices and aliases.

Be aware that this will restart jCustomer nodes.

#### jcustomer/get-kibana-endpoint.yml

Returns the Kibana endpoint of the Elastic Cloud deployment used by the environment.

#### jcustomer/install.yml

This manifest will create a jCustomer environment.

| parameter                | comment                                                    |
| ------------------------ | ---------------------------------------------------------- |
| productVersion           | jCustomer version (eg: `1.5.4`)                            |
| jCustomerNodeCount       | Number of jCustomer nodes (from `1` to `7`)                |
| jCustomerNodeSize        | Size of jCustomer nodes (`small`, `medium` or `large`)     |
| jCustomerDockerTagSuffix | A suffix to add the the Docker tag                         |
| ddogApikey               | Datadog Apikey to use                                      |
| rootPassword             | The jCustomer karaf's password                             |
| esNodeCount              | Number of Elasticsearch nodes (`1`, `3` or `5`)            |
| esNodeSize               | Size of Elasticsearch nodes (`small`, `medium` or `large`) |
| vaultRoleId              | Vault's Role Id to use                                     |
| vaultSecretId            | Vault Role Id secret to use                                |
| vaultClusterUrl          | The Vault server to use                                    |
| papiHostname             | Papi's hostname                                            |
| papipapiApiVersion       | Papi's API version                                         |
| papiEnvId                | The Environment ID on Papi                                 |

#### jcustomer/jcustomer-rolling-redeploy.yml

This manifest will perform a rolling redeployment of all the jCustomer nodes.

Be aware that it is not a simple restart, the nodes will be redeployed.

#### jcustomer/jcustomer-rolling-restart.yml

This manifest will perform a rolling restart of all the jCustomer nodes.

Be aware that it is not a redeployment, only karaf services are restarted.

#### jcustomer/maxmind-key-update.yml

This manifest will update the Maxmind key on all jCustomer nodes.

| parameter     | comment             |
| ------------- | ------------------- |
| newMaxmindKey | The new Maxmind key |

#### jcustomer/reindexation.yml

Performs a reindexation of jCustomer indices.

| parameter     | comment                    |
| ------------- | -------------------------- |
| shards_target | Number of shards per index |

#### jcustomer/reset-password-of-customer-kibana-user.yml

Resets the password of the Kibana user used by the customers.

| parameter | comment                      |
| --------- | ---------------------------- |
| jahiaenv  | The target Jahia environment |

#### jcustomer/set-unomi-root-password.yml

Sets a new karaf's password in all jCustomer nodes and restart them.

| parameter | comment                        |
| --------- | ------------------------------ |
| rootpwd   | The jCustomer karaf's password |

#### jcustomer/update-events.yml

Describes actions associated to the Jelastic events on the environment.

#### jcustomer/upgrade.yml

This _upgrades_ package aims at upgrading jCustomer nodes to the specified version.

Be aware that Elasticsearch version need to be compliant with the new jCustomer version otherwise the manifest will not allow the upgrade.

| parameter                | comment                            |
| ------------------------ | ---------------------------------- |
| targetVersion            |                                    |
| jCustomerDockerTagSuffix | A suffix to add the the Docker tag |

## Monitoring

Each node is monitored on Datadog thanks to an agent directly installed on containers.

Datadog API key (pointing to a specific organization) is set as an envvar, and a periodic script updates Datadog configuration in case this envvar or any tag is changed so that the agent still sends metrics to the right place.

## Specific

### Performance tests

In order to run performance tests against a Jahia Cloud environment, required steps must be completed first by running `jahia/perf-test-step1.yml` and `jahia/perf-test-step2.yml` to the environment.

The `jahia/perf-test-step1.yml` package will trigger asynchrounous actions (site import on Jahia) which can take a lot of time, so you have to wait for the processing's tomcat logs to go silent before proceeding to the next step.

Once it is completed, you need to apply `jahia/perf-test-step2.yml` package to the environment. It will also trigger asychronous actions so you will have to wait for the processing's tomcat logs to go silent again before running any performance test.

### Backup/restore

#### Scheduled Backup

Automated backups are handled by a specific _Jelastic_ environment scheduling backups with Cron, and accessible through an API (add, list, delete).

The `common/auto_backup.yml` will create an environment with a single _cp_ node using this image: [jahia/paas_autobackup](https://hub.docker.com/repository/docker/jahia/paas_autobackup)

Note: only _one_ _scheduled backup env_ is needed by _Jelastic_ cluster.

#### Assets

There is a significant amount of assets used by manifests but here are the most notable ones:

##### common/backrest.py

Can execute multiple tasks like :

- upload a backup
- download a backup
- add backup metadata
- remove backup metadata
- rotate backups

| parameter         | comment                                                                         |
| ----------------- | ------------------------------------------------------------------------------- |
| -a, _--action_    | The operation you want to do (upload, download, list, addmeta, delmeta, rotate) |
| _--accesskey_     | The AWS Access key                                                              |
| _--secretkey_     | The AWS Secret access key                                                       |
| _--backupname_    | The backup name                                                                 |
| _--bucketname_    | The bucket name you want to use                                                 |
| _--displayname_   | The environment display name (for metadata)                                     |
| -f, _--file_      | The local file you want to upload or download                                   |
| -F, _--foreign_   | If the backup is from another cloud/region/role ex: aws,eu-west-1,prod          |
| -k, _--keep_      | How many auto backups you want to keep (in case of backup rotation)             |
| -m, _--mode_      | The backup mode: manual or auto                                                 |
| -p, _--progress_  | To show a progress bar or not                                                   |
| _--size_          | The backup size in Bytes (used for the metadata file)                           |
| -t, _--timestamp_ | Backup timestamp in format %%Y-%%m-%%dT%%H:%%M:00                               |

##### common/check_before_hn_upgrade.py

This script is used to check if the anti-affinity rule is respected for a specific Jelastic region,
meaning that nodes from the same nodegroup in the same environment should be located on
different Hardware Nodes.

This is particularly useful before running the Hardware Node upgrade script.

| parameter         | comment                                                                                   |
| ----------------- | ----------------------------------------------------------------------------------------- |
| -u, _--user_      | The Jelastic admin user. Optional if the `juser` environment variable is defined          |
| -p, _--password_  | The Jelastic user's password. Optional if the `jpassword` environment variable is defined |
| -j, _--jelastic_  | The Jelastic cluster's DNS. Optional if the `jserver` environment variable is defined     |
| -r, _--region_    | The Jelastic region to check                                                              |
| _--papi-token_    | Papi admin token. Optional if the `PAPI_TOKEN` environment variable is defined            |
| _--papi-hostname_ | Papi hostname. Optional if the `PAPI_HOSTNAME` environment variable is defined            |

##### common/hn_upgrade.py.py

This script prepares a Hardware Node to be upgraded. It does the following actions:

- Sets the HN in MAINTENANCE mode
- Mutes the node in Datadog
- Stops the nodes running on the HN
- Waits for the HN to be upgraded and restarted
- Starts the nodes running on the HN
- Unmutes the node in Datadog
- Sets the HN in ACTIVE mode

| parameter                           | comment                                                                                                                                                                                              |
| ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| _--dry-run_                         |                                                                                                                                                                                                      |
| _--jelastic-hardware-node-hostname_ | The hardware node hostname on Jelastic. Optional if the `JELASTIC_HARDWARE_NODE_HOSTNAME` environment variable is defined                                                                            |
| _--datadog-hardware-node-hostname_  | The hardware node hostname on Datadog. Optional if the `DATADOG_HARDWARE_NODE_HOSTNAME` environment variable is defined                                                                              |
| _--juser_                           | The Jelastic admin user. Optional if the `JELASTIC_USER` environment variable is defined                                                                                                             |
| _--jpassword_                       | The Jelastic user's password. Optional if the `JELASTIC_PASSWORD` environment variable is defined                                                                                                    |
| _--jserver_                         | The Jelastic cluster's DNS. Optional if the `JELASTIC_SERVER` environment variable is defined                                                                                                        |
| _--region_                          | The Jelastic region where the HN is located. Optional if the `JELASTIC_REGION` environment variable is defined                                                                                       |
| _--dd-app-key_                      | An Application key for the JC Infra Datadog organization. Optional if the `DD_APP_KEY` environment variable is defined                                                                               |
| _--dd-api-key_                      | An API key for the JC Infra Datadog organization. Optional if the `DD_API_KEY` environment variable is defined                                                                                       |
| _--papi-token_                      | Papi token. Optional if the `PAPI_TOKEN` environment variable is defined                                                                                                                             |
| _--papi-hostname_                   | Papi hostname. Optional if the `PAPI_HOSTNAME` environment variable is defined                                                                                                                       |
| _--state-file-path_                 | The path of the state file used to save the list of nodes and their status                                                                                                                           |
| _--recover-state_                   | If this parameter is set, the state file won't be created/updated (useful if the script has been stopped before restarting the nodes during a previous run for instance and the file already exists) |
| _--skip-stop_                       | If this parameter is set, the script won't check the cluster state nor stop nodes on the HN. It can't be used if --recover-state is not set                                                          |

##### common/lib_aws.py

The `PlayWithIt` class in this Python file contains a number of methods used by multiple Python scripts to interact with AWS resources.

##### common/papi.py

Python library to interact with Papi.

| parameter           | comment                                                                              |
| ------------------- | ------------------------------------------------------------------------------------ |
| -e, _--hostname_    | Papi hostname. Optional if the `PAPI_HOSTNAME` environment variable is defined       |
| -a, _--api-version_ | Papi API version. Optional if the `PAPI_API_VERSION` environment variable is defined |
| -t, _--token_       | Papi API version. Optional if the `PAPI_TOKEN` environment variable is defined       |
| -X, _--method_      | The HTTP method to use (GET, POST...)                                                |
| -d, _--data_        | The data to include to the request if it is a POST/PUT request                       |
| _path_              | The URL path of the resource on Papi                                                 |

##### common/revisionNode.py

Creates revisionNode file

| parameter      | comment                              |
| -------------- | ------------------------------------ |
| -n, _--number_ | Decimal number to set in file        |
| -f, _--file_   | File path                            |
| -r, _--read_   | Reads the file instead of writing it |
