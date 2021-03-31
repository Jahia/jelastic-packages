# Jelastic Packages

## Overview
This repo (not yet) contains all manifests and assets used for the Jahia Cloud PAAS platform.

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
│   │   ├── dd_agent_jelastic_package_conf.yml
│   │   ├── log_events.sh
│   │   ├── set_dd_tags_cron
│   │   └── set_dd_tags.sh
│   ├── database
│   │   ├── galera.cnf
│   │   ├── logrotate_mysql
│   │   └── mysql-init.d
│   ├── elasticsearch
│   ├── haproxy
│   │   ├── 502.http
│   │   ├── dd_agent_haproxy_conf.yml
│   │   ├── dd_agent_process_conf.yml
│   │   ├── haproxy-00-global.cfg
│   │   ├── haproxy-10-jahia.cfg
│   │   ├── haproxy-11-proc.cfg
│   │   ├── haproxy-sysconfig
│   │   ├── logrotate_haproxy
│   │   ├── manage-auth-basic.py
│   │   └── rsyslog_haproxy
│   ├── jahia
│   │   ├── jahia-logo-70x70.png
│   │   ├── jahia.properties
│   │   ├── reset-jahia-tools-manager-password.py
│   │   └── success_install.md
│   └── jcustomer
├── mixins
│   ├── common.yml
│   ├── haproxy.yml
│   ├── jahia.yml
│   ├── jcustomer.yml
│   └── mariadb.yml
├── packages
│   ├── augsearch
│   ├── common
│   ├── jahia
│   │   ├── install.yml
│   │   ├── jahia-rolling-restart.yml
│   │   ├── redeploy-galera-nodes.yml
│   │   ├── update-events.yml
│   │   └── upgrade.yml
│   ├── jcustomer
│   └── one-shot
│       ├── check_jexperience.yml
│       ├── ipsec.yml
│       ├── manage-auth-basic.yml
│       ├── reset-polling.yml
│       ├── rewrite-rules.yml
│       ├── set-jahia-root-password.yml
│       └── set-jahia-tools-password.yml
└── README.md
```

## Jahia Environments

This repository hosts all packages, scripts & config files needed to create a Jahia environment on Jelastic.

### Infrasctructure overview

A Jahia environment contains:
- Two Haproxy nodes
- One or several Jahia Browsing nodes
- One Jahia Processing node
- On each tomcat node, a clusterized proxysql instance
- Either one single MariaDB node or three MariaDB nodes clusterized with Galera

Requests on the domain name target Haproxy nodes (load balanced) which route them to Browsing node(s), where a session affinity is set in case there are multiple ones.

The processing node won't receive any request from client as browsing nodes are the only ones defined in Haproxy configuration.

In case of a Galera cluster, queries are all executed on the same MariaDB master node, which is replicated to the other ones.

### Docker images

Images used by Jahia environment nodes:

| Node type        | Docker image          |
| ---------------- | --------------------- |
| Haproxy          | jelastic/haproxy      |
| Jahia Browsing   | jahia/jahiastic-jahia |
| Jahia Processing | jahia/jahiastic-jahia |
| MariaDB          | jelastic/mariadb      |

## Packages
### jahia
#### jahia/install.yml

The base JPS, called by Jahia Cloud to create an environment. It contains *only* nodes and events definition since actions are all defined in mixins JPS.

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

### one-shot
#### one-shot/reset-polling.yml

Used by Jahia Cloud to reset polling when an action fails (especially during backup/restore). It generates a *finished* action on Jelastic Console so the frontend can be aware that there was an issue with previous JPS execution.

| parameter | comment          |
|-----------|------------------|
| feature   | Feature involved |
| datetime  | Date & Time      |

#### one-shot/check_jexperience.yml

Check if a jahia env is alowed to talk with is linked jcustomer env.

#### one-shot/ipsec.yml

This manifest will create or update a Strongswan IPSec connection on each tomcat's nodes.

| parameter         | comment                                                           |
|-------------------|-------------------------------------------------------------------|
| vault_secret_path | The Vault path where the connection conf is stored.               |
| ipsec_should_be   | Boolean.<br>Tell if the previous connection should be up or down. |

#### one-shot/manage-auth-basic.yml

Enable or disable an Auth Basic at haproxy level.

| parameter | comment                                       |
|-----------|-----------------------------------------------|
| enable    | Boolean.<br>Enable or disable the Auth Basic. |
| login     | User name to use.                             |
| pwd       | Password to use.                              |

#### one-shot/rewrite-rules.yml

This will add customer's custom rule to HAProxy configuration.

| parameter         | comment                                                                   |
|-------------------|---------------------------------------------------------------------------|
| vault_secret_path | The Vault path where the connection conf is stored.                       |
| md5sum            | For compare the rules at Cloud's front level and what is stored in Vault. |

#### one-shot/set-jahia-root-password.yml

Prepare a jahia's env root password update by setting a file on the processing node. Customers will still have to restart the processing node for being effective.

| parameter | comment              |
|-----------|----------------------|
| rootpwd   | The password to set. |

#### one-shot/set-jahia-tools-password.yml
Prepare a jahia's env _/tools_ password update on each tomcat nodes. Customers will still have to restart all tomcat nodes for being fully effective.

| parameter | comment              |
|-----------|----------------------|
| tools_pwd | The password to set. |

## Monitoring

Each node is monitored on Datadog thanks to an agent directly installed on containers.

Datadog API key (pointing to a specific organization) is set as an envvar, and a periodic script update Datadog conf in case this envvar or any tag is changed so that the agent is still sending metrics to the right place.
