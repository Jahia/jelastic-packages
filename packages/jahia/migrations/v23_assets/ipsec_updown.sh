#!/usr/bin/bash
#

dns_source=/etc/strongswan/resolv.conf
conn_dir=/etc/strongswan/ipsec.d
dnsmasq_dir=/etc/dnsmasq.d
logfile=/var/log/jelastic-packages/ipsec.log
conn_name=$(echo $PLUTO_CONNECTION | sed 's/\//_/g')
dnsmasq_conf=$dnsmasq_dir/$conn_name
infra_conf=$dnsmasq_dir/infra_internals
infra_root_dns=(j.jahia.com cloud.jahia.com)
[ -f $logfile ] && rm $logfile

log(){
  echo "$(date +'%F %T') - $1" | tee -a $logfile
}

up(){
  log "Connexion name is $PLUTO_CONNECTION"
  conn_file=$(grep -l $PLUTO_CONNECTION $conn_dir/*conf)
  internal_dns_list=($(awk -F'=' '/## *internal_domains *=/ {print gensub(/,/, " ", "g", $NF)}' $dconn_dir/$conn_file))

  if [ ${#internal_dns_list} -eq 0 ]; then
    log "didn't found internal dns to use through the ipsec connection"
  else
    log "internal dns found: ${internal_dns_list[*]}"
  fi

  conn_dns_list=($(awk '{printf "%s ",$2}' $dns_source))
  log "connection dns list: ${conn_dns_list[*]}"

  [ -f $dnsmasq_conf ] && rm $dnsmasq_conf
  for vpn_dns in ${conn_dns_list[*]}; do
    for internal_domain in ${internal_dns_list[*]}; do
      line="server=/$internal_domain/$vpn_dns"
      log "add this line in $dnsmasq_conf: $line"
      echo "$line" >> $dnsmasq_conf
    done
  done

  [ -f $infra_conf ] && rm $infra_conf
  awk '$1=="nameserver" && $2!~/^(127\.|8\.8\.)/ {print $2}' /etc/resolv.conf | while read dns_infra; do
    for internal_dns in ${infra_root_dns[*]}; do
      line="server=/$internal_dns/$dns_infra"
      log "add this line in $infra_conf: $line"
      echo "$line" >> $infra_conf
    done
  done

  if (systemctl -q is-active dnsmasq || systemctl start dnsmasq); then
    sed -e '1 i nameserver 127.0.0.1' -e '/127.0.0.1/d' -i /etc/resolv.conf
  else
    log "an error occured while starting dnsmasq, no change made to /etc/resolv.conf"
  fi
}

down(){
  log "Connexion name is $PLUTO_CONNECTION"
  if (grep -q "nameserver 127.0.0.1" /etc/resolv.conf); then
    log "/etc/resolv.conf is using dnsmasq, now remove this..."
    sed '/nameserver 127.0.0.1/d' -i /etc/resolv.conf
  else
    log "/etc/resolv.conf isn't using dnsmasq, nothing to do"
  fi
  if (systemctl -q is-active dnsmasq); then
    log "dnsmasq daemon is active, now stopping it..."
    systemctl stop dnsmasq
    log "now removing dnsmasq conf $dnsmasq_conf"
    [ -f $dnsmasq_conf ] && rm $dnsmasq_conf
    log "now removing infra dns conf $infra_conf"
    [ -f $infra_conf ] && rm $infra_conf
  else
    log "dnsmasq daemon isn't active, nothing to do"
  fi
}

case "$PLUTO_VERB" in
  "up-client")
    log "Connection $PLUTO_CONNECTION is activated"
    up
    ;;
  "down-client")
    log "Connection $PLUTO_CONNECTION is disabled"
    down
    ;;
esac
