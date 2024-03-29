#!/usr/bin/bash -l
#

tmpfile=/tmp/set_dd_tags.tmp
ddconffile=/etc/datadog-agent/datadog.yaml
hn_metadata=/metadata_from_HOST

source ${hn_metadata}

{
echo "api_key: $DATADOGAPIKEY"
echo "hostname: $(echo $_ROLE| tr [A-Z] [a-z] |sed 's/_//g')."$(hostname | sed 's/^[[:alpha:]]\+\([[:digit:]]\+\).*/\1/' | tr [A-Z] [a-z])
echo "apm_config:"
echo "  enabled: ${DATADOG_APM_ENABLED:-true}"
echo "  obfuscation:"
echo "    elasticsearch:"
echo "      enabled: true"
echo "logs_enabled: true"
echo "log_level: WARN"
echo "logs_config:"
echo "  processing_rules:"
echo "    - type: mask_sequences"
echo "      name: mask_password"
echo "      pattern: (PASSWORD=)(\w+)"
echo "      replace_placeholder: \"PASSWORD=[masked_password]\""
echo "    - type: mask_sequences"
echo "      name: mask_token"
echo "      pattern: APIToken\s(\S+)"
echo "      replace_placeholder: \"APIToken [masked_token]\""
echo "tags:"
echo " - product:${_PROVIDE}"
echo " - envname:${envName}"
echo " - provide:${_PROVIDE}"
echo " - version:${DX_VERSION}"
echo " - role:${_ROLE}"
echo " - envmode:${envmode}"
echo " - availability-zone:${JEL_AVAILABILITYZONE}"
echo " - region:${JEL_REGION}"
echo " - cloud-provider:${JEL_CLOUDPROVIDER}"
echo " - hardware_node:${JEL_HOST_WHERE}"
echo " - hn_hostname:${JEL_HOST_HOSTNAME}"
echo " - cluster_role:${JEL_ENV_ROLE}"
} > $tmpfile

md5_tmp=$(md5sum $tmpfile | awk '{print $1}')
md5_dd=$(md5sum $ddconffile| awk '{print $1}')

if [ "$md5_tmp" == "$md5_dd" ]; then
    echo "Tags are up to date, exiting."
else
    echo "Change detected in tag(s), updating Datadog conf..."
    cp -f $tmpfile $ddconffile && sleep 2 && systemctl restart datadog-agent
fi

