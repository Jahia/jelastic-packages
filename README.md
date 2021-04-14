# Jelastic Packages

## Overview

This repo (not yet) contains all manifests and assets used for the Jahia Cloud PAAS platform.

It's a merge of what where in previous _paas_*_ and _cloud-scripts_ repos.

Progress report:
| repo                       | state              | comment                      |
|----------------------------|--------------------|------------------------------|
| paas_jelastic_dx_universal | :heavy_check_mark: | missing `region_migrate.yml` |
| paas_jelastic_unomi        | :heavy_check_mark: | missing `region_migrate.yml` |
| paas-jelastic-dx-perf-test | :heavy_check_mark: |                              |
| paas_jelastic_backup       | :heavy_check_mark: |                              |

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
│   ├── common
│   ├── database
│   ├── elasticsearch
│   ├── haproxy
│   ├── jahia
│   └── jcustomer
├── mixins
└── packages
    ├── augsearch
    ├── common
    ├── jahia
    ├── jcustomer
    └── one-shot
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

#### JCustomer env

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
| env            | Enviroment mode (dev or prod)                    |
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
| env            | Enviroment mode (dev or prod) |

#### common/update-datadog-apikey.yml

This manifest allow to update a env's DataDog API key.

The script will check that the key currently used is the one you think before set the new key.

| parameter            | comment                |
|----------------------|------------------------|
| currentDataDogApikey | The key currently used |
| newDataDogApikey     | The new API key yo use |

#### common/reset-polling.yml

Used by Jahia Cloud to reset polling when an action fails (especially during backup/restore). It generates a *finished* action on Jelastic Console so the frontend can be aware that there was an issue with previous JPS execution.

| parameter | comment          |
|-----------|------------------|
| feature   | Feature involved |
| datetime  | Date & Time      |

#### common/restore.yml

Restores a backup. Works both for jahia (files + database, Haproxy conf) and jCustomer (Elasticsearch indices).

| pame           | comment                                                             |
|----------------|---------------------------------------------------------------------|
| backup_name    | Backup Name                                                         |
| aws_access_key | AWS Access Key                                                      |
| aws_secret_key | AWS Secret Key                                                      |
| env            | Enviroment mode (dev or prod)                                       |
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

| parameter        | comment                                                                                                                                                       |
|------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------|
| productVersion   | Jahia version (eg: `8.0.2.0`)                                                                                                                                 |
| rootpwd          | Jahia root password                                                                                                                                           |
| toolspwd         | jahia tools password                                                                                                                                          |
| browsingCount    | Number of jahia browsing nodes                                                                                                                                |
| shortdomain      | Environment name                                                                                                                                              |
| mode             | The topology type: `production` or `development`<br>Involves several things like:<ul><li>cloudlets</li><li>1 or 3 galera nodes</li><li>_Xmx_ values</li></ul> |
| ddogApikey       | Datadog Apikey to use                                                                                                                                         |
| jahiaDockerImage | Hidden settings for use a docker image instead of a tag of the jahia's jelastic template                                                                      |
| vaultClusterUrl  | The Vault server to use                                                                                                                                       |
| vaultRoleId      | Vault's Role Id to use                                                                                                                                        |
| vaultSecretId    | Vault Role Id secret to use                                                                                                                                   |

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

| parameter | comment                                |
|-----------|----------------------------------------|
| pwd       | The password _jExperience_ have to use |

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

### jcustomer

#### jcustomer/install.yml

This manifest will create a jCustomer environment.

| parameter      | comment                                            |
|----------------|----------------------------------------------------|
| productVersion | jCustomer version (eg: `1.5.4`)                    |
| UnomiMode      | Number of jCustomer nodes<br>(from `1` to `7`)     |
| ESMode         | Number of Elasticsearch nodes<br>(`1`, `3` or `5`) |
| mode           | The env type: `production` or `development`        |
| ddogApikey     | Datadog Apikey to use                              |
| rootPassword   | The jCustomer karaf's password                     |

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
