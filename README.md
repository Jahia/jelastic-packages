# Jelastic Packages

## Overview
This repo (not yet) contains all manifests and assets used for the Jahia Cloud PAAS platform.
It's a merge of what where in previous _paas_*_ and _cloudr-scripts_ repos.

Progress report:
| repo                       | state              | comment                      |
|----------------------------|--------------------|------------------------------|
| paas_jelastic_dx_universal | :heavy_check_mark: | missing `region_migrate.yml` |
| paas_jelastic_unomi        | :heavy_check_mark: | missing `region_migrate.yml` |

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

## Jahia Environments

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

#### JCustomer

A jCustomer environment contains:
- One or two jCustomer nodes
- One or thress Elasticsearch nodes

Nodes numbers depend of the environment purpose: _development_ or _production_.

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

#### common/reset-polling.yml

Used by Jahia Cloud to reset polling when an action fails (especially during backup/restore). It generates a *finished* action on Jelastic Console so the frontend can be aware that there was an issue with previous JPS execution.

| parameter | comment          |
|-----------|------------------|
| feature   | Feature involved |
| datetime  | Date & Time      |

### jahia

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


#### jahia/jahia-rolling-restart.yml

This manifest will rolling restart all Jahia nodes (cp & proc).
Be Aware that is it not a redployment, only tomcat service is restarted.

#### jahia/redeploy-galera-nodes.yml
This manifest will redeploy all galera nodes whith the jahia's Full ReadOnly mode enabled.

| parameter       | comment                                                                  |
|-----------------|--------------------------------------------------------------------------|
| targetDockerTag | Jelastic Mariadb-dockerized template tag to use.<br>(default: `10.4.13`) |

#### jahia/update-events.yml
Describe actions associated to severals jelastic's event on the environment.

#### jahia/upgrade.yml

This *upgrade* package aims at upgrading Jahia version by redeploying Jahia nodes with the target Jahia version tag, but since it takes the tag as a parameter, it is also used to do a rolling redeploy of Tomcat nodes.

| parameter      | comment                                                                                                            |
|----------------|--------------------------------------------------------------------------------------------------------------------|
| targetVersion  | Optional.<br>If you don't specify a version, the current Jahia version of the target environment will be selected. |
| rollingUpgrade | Boolean value<br>For now has to be set to `false`.                                                                 |

#### jahia/check_jexperience.yml

Check if a jahia env is alowed to talk with is linked jcustomer env.

#### jahia/ipsec.yml

This manifest will create or update a Strongswan IPSec connection on each tomcat's nodes.

| parameter         | comment                                                           |
|-------------------|-------------------------------------------------------------------|
| vault_secret_path | The Vault path where the connection conf is stored.               |
| ipsec_should_be   | Boolean.<br>Tell if the previous connection should be up or down. |

#### jahia/manage-auth-basic.yml

Enable or disable an Auth Basic at haproxy level.

| parameter | comment                                       |
|-----------|-----------------------------------------------|
| enable    | Boolean.<br>Enable or disable the Auth Basic. |
| login     | User name to use.                             |
| pwd       | Password to use.                              |

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


## Monitoring

Each node is monitored on Datadog thanks to an agent directly installed on containers.

Datadog API key (pointing to a specific organization) is set as an envvar, and a periodic script update Datadog conf in case this envvar or any tag is changed so that the agent is still sending metrics to the right place.
