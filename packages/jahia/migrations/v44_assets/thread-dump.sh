#!/bin/bash

TOMCAT_USER=tomcat

source /.jelenv

dumps_dir=${DUMPS_PATH:-/var/tmp/cloud}

# If jstack is already running, we don't start a new process
if (pgrep jstack > /dev/null); then
  echo 'jstack is already running, no new process will be started'
  exit 0
fi

sudo -u $TOMCAT_USER mkdir -p $dumps_dir/{thread,heap,classes}_dumps

# add jstack to /usr/bin if not present
if [[ ! -f "/usr/bin/jstack" ]]; then
    jstack=$(find /usr/java/openjdk-*/bin -name jstack)
    ln -s $jstack /usr/bin/
fi

PID=$(pgrep -u tomcat java.orig)
today=$(date +'%m-%d-%Y')
hour=$(date +'%Hh')
minute=$(date +'%M')

for dump_type in "thread" "classes"; do
    # Be extremely careful when updating this variable as many rm -rf are based on its value
    REPO=$dumps_dir/${dump_type}_dumps

    # Rotate yesterday dumps if not already done
    yesterday_dir="$REPO/$(date -d "yesterday" +'%m-%d-%Y')"
    if [[ ! -f $yesterday_dir.tar.gz ]]; then
        tar czf ${yesterday_dir}.tar.gz $yesterday_dir --remove-files
        chown ${TOMCAT_USER}: ${yesterday_dir}.tar.gz
    fi

    today_dir="$REPO/$today/$hour"
    mkdir -p $today_dir

    filename="$today_dir/$minute"
    if [ "$dump_type" = "thread" ]; then
        timeout $(( 15 * 60 )) jstack -l $PID > $filename
    else
        timeout $(( 15 * 60 )) jstack $PID GC.class_stats > $filename
    fi

    chown -R $TOMCAT_USER: $today_dir

    # remove files older than the number of days specified in DUMPS_RETENTION_DAYS envvar
    retention_days=${DUMPS_RETENTION_DAYS:-30}
    find $REPO -type f -mtime +$retention_days -exec rm -f {} \;
done
