#!/bin/bash
# Export some envvars so that we can use them in haproxy conf:
grep -E "^(jahia_cfg_healthcheck_token|haproxy_cfg_\w+)=" /.jelenv > /etc/sysconfig/haproxy

haproxy_cfg=/etc/haproxy/haproxy.cfg
jahia_cloud_cfg=/etc/haproxy/haproxy.cfg.jahia/jahia-cloud.cfg
http_error_cfg=/etc/haproxy/haproxy.cfg.jahia/http-errors.cfg
customer_rules_file=/etc/haproxy/haproxy.cfg.jahia/customer.cfg
customer_rules_dir=/etc/haproxy/haproxy.cfg.jahia/customer.configuration.d

[ ! -f $customer_rules_file ] && sudo -u haproxy touch $customer_rules_file
echo "" > $customer_rules_file
for f in $(ls $customer_rules_dir/*.cfg 2>/dev/null); do
    echo "## CUSTOMER_FILENAME $f" >> $customer_rules_file
    cat $f >> $customer_rules_file
done

cp $jahia_cloud_cfg $haproxy_cfg
sed -i "/^##CUSTOMER_RULES_START_HERE##/ r $customer_rules_file" $haproxy_cfg
sed -i "/^##HTTP_ERRORS_START_HERE##/ r $http_error_cfg" $haproxy_cfg
