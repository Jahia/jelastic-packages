# Jelastic Packages

## Overview

This repo contains all manifests and assets used for the Jahia Cloud PaaS platform.

It's a merge of what was in previous _paas_jelastic_*_ and _cloud-scripts_ repos.

## Rules

Here are some rules that should be observed:
* packages in `packages/jahia` folder should apply to Jahia envs, and so on
* packages contain minimum logic, most logic should be deported to actions defined in mixins (for reusability)
	* as a consequence, assets should only be referenced by actions (package > action > asset)
* actions should not rely on global variables
* keep mixin files dependencies to the bare minimum
	* when one mixin depends on another, it must be specified in a comment on top of the file

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
├── mixins
└── packages
    ├── augsearch
    ├── common
    ├── jahia
    ├── jcustomer
    └── one-shot
```
### `deps.py`

This is a script that allows you to do:
* checks
    * check that the actions used by manifest(s) are well defined
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
    * check for duplicated actions in mixins files
        ```console
        $ ./deps.py mixins_duplicates
        ❌'setJournaldLimit' is duplicated: ['./mixins/common.yml', './mixins/jcustomer.yml']
        ```
* graph dependencies tree from manifest(s)
    ```console
    $ ./deps.py graph -q -o AS_manifest_deps.dot ./packages/jahia/augmented-search-*.yml
    ```
* (really) simple search
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
* `graphviz` and its development files
* gcc
* python 3.8 or higher
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
- Two Haproxy nodes
- One or several Jahia Browsing nodes
- One Jahia Processing node
- On each tomcat node, a clusterized proxysql instance
- Either one single MariaDB node or three MariaDB nodes clusterized with Galera

Requests on the domain name target Haproxy nodes (load balanced) which route them to Browsing node(s), where a session affinity is set in case there are multiple ones.

The processing node won't receive any request from client as browsing nodes are the only ones defined in Haproxy configuration.

In case of a Galera cluster, queries are all executed on the same MariaDB master node, which is replicated to the other ones.

#### jCustomer env

A jCustomer environment contains:
- One or several jCustomer nodes
- One, three or five Elasticsearch nodes

### Docker images

#### Jahia env

Images used by Jahia environment nodes:

| Node type        | Docker image          |
|------------------|-----------------------|
| Haproxy          | jelastic/haproxy      |
| Jahia Browsing   | jahia/jahiastic-jahia |
| Jahia Processing | jahia/jahiastic-jahia |
| MariaDB          | jelastic/mariadb      |


#### jCustomer env

Images used by jCustomer environment nodes:

| Node type     | Docker image              |
|---------------|---------------------------|
| jCustomer     | jahia/jahiastic-jcustomer |
| Elasticsearch | jahiadev/elasticsearch    |

## Packages

### common

#### common/auto_backup.yml

Creates an autobackup environment to handle schedule backups.

| parameter   | comment                                                                      |
|-------------|------------------------------------------------------------------------------|
| masterLogin | login used to connect to Jelastic                                            |
| masterPwd   | password used to connect to Jelastic                                         |
| awsAccess   | AWS Access Key                                                               |
| awsSecret   | AWS Secret Key                                                               |
| dd_api_key  | Datadog Apikey to use                                                        |

#### common/auto_backup_control.yml

Allows to interact with the autobackup environment API.

##### Add a new scheduled backup

| parameter  | comment                                                                      |
|------------|------------------------------------------------------------------------------|
| action     | `add`                                                                        |
| schedule   | _cron_ schedule style<br>eg: `* */8 * * *`                                   |
| envname    | the _envName_ you want to get scheduled backup<br>eg: `mysuperenv`           |
| region     | the _Jelastic_'s region where the targeted env is<br>eg: `default_hn_region` |
| sudo       | the targeted env's owner mail<br>eg: `iamanuser@mydomain.com`                |
| uid        | the targeted env's owner UID<br>eg: `21135`                                  |
| backupname | how to call this scheduled backup<br>eg: `myregularautobackup`               |
| retention  | how many backups do we keep<br>eg: `15`                                      |


##### Del a scheduled backup

| parameter | comment                                                              |
|-----------|----------------------------------------------------------------------|
| action    | `del`                                                                |
| envname   | for which _envName_ do you want to remove backup<br>eg: `mysuperenv` |


##### List scheduled backup

| parameter | comment |
|-----------|---------|
| action    | `list`  |

#### common/backup.yml

Backups an environment. Works both for jahia (files + database, Haproxy conf) and jCustomer (Elasticsearch indices).

| parameter      | comment                                          |
|----------------|--------------------------------------------------|
| backup_name    | Backup Name                                      |
| aws_access_key | AWS Access Key                                   |
| aws_secret_key | AWS Secret Key                                   |
| timestamp      | The backup timestamp in format %Y-%m-%dT%H:%M:00 |
| retention      | How many auto-backups do you want to keep        |
| backtype       | Is this a manual or auto backup                  |

#### common/listbackup.yml

__DEPRECATED__
List backups for a given user.

| parameter      | comment                       |
|----------------|-------------------------------|
| aws_access_key | AWS Access Key                |
| aws_secret_key | AWS Secret Key                |

#### common/update-datadog-apikey.yml

This manifest allow to update a env's DataDog API key.

The script will check that the key currently used is the one you think before set the new key.

| parameter            | comment                |
|----------------------|------------------------|
| currentDataDogApikey | The key currently used |
| newDataDogApikey     | The new API key yo use |

#### common/restore.yml

Restores a backup. Works both for jahia (files + database, Haproxy conf) and jCustomer (Elasticsearch indices).

| pame           | comment                                                             |
|----------------|---------------------------------------------------------------------|
| backup_name    | Backup Name                                                         |
| aws_access_key | AWS Access Key                                                      |
| aws_secret_key | AWS Secret Key                                                      |
| source_env     | Source environment appid (if still exists)                          |
| envrole_source | [If source_env not defined] Enviroment source mode (dev or prod)    |
| cloud_source   | [If source_env not defined] Enviroment source cloud provider        |
| region_source  | [If source_env not defined] Enviroment source cloud provider region |
| uid_source     | [If source_env not defined] Environment owner's UID                 |
| timestamp      | The backup timestamp in format %Y-%m-%dT%H:%M:00                    |
| retention      | How many auto-backups do you want to keep                           |
| backtype       | Is this a manual or auto backup                                     |
| removeEnvlink  | Remove (1) or keep (0) Env links                                    |

### jahia

#### jahia/check_jexperience.yml

Check if a jahia env is alowed to talk with is linked jcustomer env.

#### jahia/install.yml

The base JPS, called by Jahia Cloud to create an environment.

Takes as parameters:

| parameter          | comment                                                                                  |
|--------------------|------------------------------------------------------------------------------------------|
| productVersion     | Jahia version (eg: `8.0.2.0`)                                                            |
| rootpwd            | Jahia root password                                                                      |
| toolspwd           | Jahia tools password                                                                     |
| haproxyNodeCount   | Number of HAProxy nodes                                                                  |
| browsingNodeCount  | Number of Jahia browsing nodes                                                           |
| browsingNodeSize   | Size of Jahia browsing nodes (`small`, `medium` or `large`)                              |
| processingNodeSize | Size of Jahia processing node (`small`, `medium` or `large`)                             |
| sqldbNodeCount     | Number of MariaDB nodes                                                                  |
| sqldbNodeSize      | Size of MariaDB nodes (`small`, `medium` or `large`)                                     |
| shortdomain        | Environment name                                                                         |
| ddogApikey         | Datadog Apikey to use                                                                    |
| jahiaDockerImage   | Hidden settings for use a docker image instead of a tag of the jahia's jelastic template |
| vaultClusterUrl    | The Vault server to use                                                                  |
| vaultRoleId        | Vault's Role Id to use                                                                   |
| vaultSecretId      | Vault Role Id secret to use                                                              |

#### jahia/ipsec.yml

This manifest will create or update a Strongswan IPSec connection on each tomcat's nodes.

| parameter         | comment                                                           |
|-------------------|-------------------------------------------------------------------|
| vault_secret_path | The Vault path where the connection conf is stored.               |
| ipsec_should_be   | Boolean.<br>Tell if the previous connection should be up or down. |

#### jahia/galera-restart-nodes.yml

This manifest will gracefuly restart all galera nodes with the jahia's Full ReadOnly mode enabled.

#### jahia/jahia-full-read-only.yml

The manifest will enable or disable Jahia's Full ReadOnly mode.

| parameter | comment  |
|-----------|----------|
| enableFRO | Boolean. |

#### jahia/jahia-rolling-restart.yml

This manifest will rolling restart all Jahia nodes (cp & proc).

Be aware that is it not a redeployment, only tomcat services are restarted.

#### jahia/link-to-customer.yml

This manifest is launched against a Jahia env and will link it to a jCustomer environment by installing and configure _jExperience_ module  as well as putting a metadata `envLink` on nodegroups _proc_ and _cp_. It also allow Jahia env tomcat's IPs in _jCustomer_ configuration.

| parameter | comment                                                  |
|-----------|----------------------------------------------------------|
| unomienv  | The jCustomer env to be linked to the targeted Jahia env |

#### jahia/manage-auth-basic.yml

Enable or disable an Auth Basic at haproxy level.

| parameter | comment                                       |
|-----------|-----------------------------------------------|
| enable    | Boolean.<br>Enable or disable the Auth Basic. |
| login     | User name to use.                             |
| pwd       | Password to use.                              |

#### jahia/redeploy-galera-nodes.yml

This manifest will redeploy all galera nodes with the jahia's Full ReadOnly mode enabled.

| parameter       | comment                                                                  |
|-----------------|--------------------------------------------------------------------------|
| targetDockerTag | Jelastic Mariadb-dockerized template tag to use.<br>(default: `10.4.13`) |

#### jahia/perf-test-step1.yml

First step to install the performance tests site on Jahia.

It will:
- Install required modules (calendar, event, ldap, news, publication, remotepublish, sitemap, templates-web-blue-qa-2.0.2-SNAPSHOT)
- Install required Linux packages (ImageMagick-devel, libreoffice, ffmpeg)
- Update jahia.properties conf
- Add LDAP provider (org.jahia.services.usermanager.ldap-cloud-perf.cfg)
- Retrieve performance tests site archive and import it in Jahia
    - https://github.com/Jahia/paas-jelastic-dx-perf-test/raw/master/assets/DXPerformanceTestSite_staging_7231.zip

| parameter       | comment                                                                       |
|-----------------|-------------------------------------------------------------------------------|
| rootCredentials | The environment's root credentials seperated by a colon, e.g. "root:password" |

#### jahia/perf-test-step2.yml

Second step to install the performance tests site on Jahia.

It will:
- Pre-compile all servlets
- Update Spell-Checker index
- Restart Tomcat

| parameter     | comment                                                                           |
|---------------|-----------------------------------------------------------------------------------|
| toolsPassword | The environment's tools credentials seperated by a colon, e.g. "manager:password" |

#### jahia/rewrite-rules.yml

This will add customer's custom rule to HAProxy configuration.

| parameter         | comment                                                                   |
|-------------------|---------------------------------------------------------------------------|
| vault_secret_path | The Vault path where the connection conf is stored.                       |
| md5sum            | For compare the rules at Cloud's front level and what is stored in Vault. |

#### jahia/set-jahia-root-password.yml

Prepare a jahia's env root password update by setting a file on the processing node. Customers will still have to restart the processing node for being effective.

| parameter | comment              |
|-----------|----------------------|
| rootpwd   | The password to set. |

#### jahia/set-jahia-tools-password.yml

Prepare a jahia's env _/tools_ password update on each tomcat nodes. Customers will still have to restart all tomcat nodes for being fully effective.

| parameter | comment              |
|-----------|----------------------|
| tools_pwd | The password to set. |

#### jahia/update-events.yml

Describe actions associated to severals jelastic's event on the environment.

#### jahia/upgrade.yml

This *upgrade* package aims at upgrading Jahia version by redeploying Jahia nodes with the target Jahia version tag, but since it takes the tag as a parameter, it is also used to do a rolling redeploy of Tomcat nodes.

| parameter      | comment                                                                                                            |
|----------------|--------------------------------------------------------------------------------------------------------------------|
| targetVersion  | Optional.<br>If you don't specify a version, the current Jahia version of the target environment will be selected. |
| rollingUpgrade | Boolean value<br>For now has to be set to `false`.                                                                 |

#### jahia/set-jcustomer-password-in-jahia.yml

This manifest will update the _jExperience_ module's configuration with the provided password.

| parameter | comment                                                     |
|-----------|-------------------------------------------------------------|
| pwd_b64       | The password _jExperience_ have to use (base64 encoded) |

#### jahia/set-jahia-tools-password.yml

Prepare a jahia's env _/tools_ password update on each tomcat nodes. Customers will still have to restart all tomcat nodes for being fully effective.

| parameter | comment              |
|-----------|----------------------|
| tools_pwd | The password to set. |

### jcustomer

#### jcustomer/install.yml

This manifest will create a jCustomer environment.

| parameter          | comment                                                    |
|--------------------|------------------------------------------------------------|
| productVersion     | jCustomer version (eg: `1.5.4`)                            |
| jCustomerNodeCount | Number of jCustomer nodes (from `1` to `7`)                |
| jCustomerNodeSize  | Size of jCustomer nodes (`small`, `medium` or `large`)     |
| esNodeCount        | Number of Elasticsearch nodes (`1`, `3` or `5`)            |
| esNodeSize         | Size of Elasticsearch nodes (`small`, `medium` or `large`) |
| ddogApikey         | Datadog Apikey to use                                      |
| rootPassword       | The jCustomer karaf's password                             |

#### jcustomer/jcustomer-rolling-restart.yml

This manifest will rolling restart all jCustomer nodes (not the Elasticsearch nodes).

Be aware that it is not a redeployment, only karaf service are restarted.

#### jcustomer/redeploy-es-nodes.yml

This manifest will redeploy Elasticsearch nodes.

#### jcustomer/set-unomi-root-password.yml

Set a new karaf's password in all jCustomer nodes and restart them.

| parameter    | comment                        |
|--------------|--------------------------------|
| rootPassword | The jCustomer karaf's password |

#### jcustomer/update-events.yml

Describe actions associated to severals jelastic's event on the environment.

#### jcustomer/upgrade.yml

This *upgrade* package aims at upgrading jCustomer nodes to the specified version.

Be aware that Elasticsearch version need to be compliant with the new jCustomer version otherwise the manifest will not allow the upgrade.

| parameter     | comment                                                                                                                |
|---------------|------------------------------------------------------------------------------------------------------------------------|
| targetVersion | Optional.<br>If you don't specify a version, the current jCustomer version of the target environment will be selected. |

## Monitoring

Each node is monitored on Datadog thanks to an agent directly installed on containers.

Datadog API key (pointing to a specific organization) is set as an envvar, and a periodic script update Datadog conf in case this envvar or any tag is changed so that the agent is still sending metrics to the right place.

## Specific

### Performance tests

In order to run performance tests against a Jahia Cloud environment, required steps must be completed first by running `jahia/perf-test-step1.yml` and `jahia/perf-test-step2.yml` to the environment.

The `jahia/perf-test-step1.yml` package will trigger asynchrounous actions (site import on Jahia) which can take a lot of time, so you have to wait for the processing's tomcat logs to go silent before proceeding to the next step.

Once it is completed, you need to apply `jahia/perf-test-step2.yml` package to the environment. It will also trigger asychronous actions so you will have to wait for the processing's tomcat logs to go silent again before running any performance test.

### Backup/restore

#### Scheduled Backup

Automated backups are handled by a specific _Jelastic_ environment scheduling backups with Cron, and accessible through an API (add, list, delete).

The `common/auto_backup.yml` will create an environment with a single _cp_ node using this image: [jahia/paas_autobackup](https://hub.docker.com/repository/docker/jahia/paas_autobackup)

Note: only *one* _scheduled backup env_ is needed by _Jelastic_ cluster.

#### Assets

##### common/backrest.py

Can execute multiple tasks like :

- upload a backup
- download a backup
- add backup metadata
- remove backup metadata
- list backups __DEPRECATED__
- rotate backups

| parameter        | comment                                                                         |
|------------------|---------------------------------------------------------------------------------|
| -a _--action_    | The operation you want to do (upload, download, list, addmeta, delmeta, rotate) |
| _--bucketname_   | The bucket name you want to use                                                 |
| _--backupname_   | The backup name                                                                 |
| _--displayname_  | The environment display name (for metadata)                                     |
| -f _--file_      | The local file you want to upload or download                                   |
| -k _--keep_      | How many auto backups you want to keep (in case of backup rotation)             |
| -F _--foreign_   | If the backup is from another cloud/region/role ex: aws,eu-west-1,prod          |
| -t _--timestamp_ | Backup timestamp in format %%Y-%%m-%%dT%%H:%%M:00                               |
| -m _--mode_      | The backup mode: manual or auto                                                 |

##### common/elasticsearch.py

Used to backup jCustomer environments. Retrieves azure secrets if necessary and create folders if not existing

| parameter            | comment                         |
|----------------------|---------------------------------|
| _--bucketname_       | The bucket name you want to use |
| _--backupname_       | The backup name                 |
| -c _--cloudprovider_ | The backup cloudprovider        |
| -o _--operation_     | backup or restore               |


##### common/revisionNode.py

Creates revisionNode file

| parameter     | comment                              |
|---------------|--------------------------------------|
| -n _--number_ | Decimal number to set in file        |
| -f _--file_   | File path                            |
| -r _--read_   | Reads the file instead of writing it |


##### common/lib_aws.py & common/lib_azure.py

Python libs used to handle authentication and manipulate files on AWS S3 buckets and Azure Resource Groups.
