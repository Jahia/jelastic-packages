#!/bin/bash

. /.jelenv

nodeId=$(hostname | sed -r 's/^node([0-9]+)-.*$/\1/')

case "$_PROVIDE" in
    haproxy)
        log_path=/var/log/haproxy/
        include='--include="haproxy.log*.gz"'
        ;;
    jahia)
        log_path=/opt/tomcat/logs/
        include='--include="catalina.out*.gz" --include="access_log.txt*.gz"'
        ;;
    unomi)
        log_path=/opt/jcustomer/jcustomer/data/log
        include='--include="karaf.log*.gz"'
        ;;
    *)
        exit 0
        ;;
esac

sendLogs(){
    eval rclone copy $log_path $include logsbucket:$logs_s3_bucket_name/$envName/$_ROLE/$nodeId/
}

# we try twice if necessary
sendLogs || (sleep 666; sendLogs)
