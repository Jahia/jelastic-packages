#!/bin/bash

# If jstack is already running, we don't start a new process
if (pgrep jstack > /dev/null); then
  echo 'jstack is already running, no new process will be started'
  exit 0
fi

# Be extremely careful when updating this variable as many rm -rf are based on its value
REPO="/root/thread_dumps"

# add jstack to /usr/bin if not present
if [[ ! -f "/usr/bin/jstack" ]]; then
    jstack=$(find /usr/java/openjdk-*/bin -name jstack)
    ln -s $jstack /usr/bin/
fi

# Rotate yesterday dumps if not already done
yesterday=$(date -d "yesterday" +'%m-%d-%Y')
if [[ -d "$REPO/$yesterday" ]]
then
    tar -zcf "$REPO/$yesterday.tar.gz" "$REPO/$yesterday"
    rm -rf "$REPO/$yesterday"
fi

PID=$(pgrep -u tomcat java.orig)
today=$(date +'%m-%d-%Y')
hour=$(date +'%Hh')
minute=$(date +'%M')
mkdir -p "$REPO/$today/$hour"

timeout $(( 15 * 60 )) jstack -l $PID > "$REPO/$today/$hour/$minute"

# remove files older than 7 days
find $REPO -type f -mtime +7 -exec rm -f {} \;
