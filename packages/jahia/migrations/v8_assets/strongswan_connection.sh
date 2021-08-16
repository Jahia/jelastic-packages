#!/usr/bin/bash

sub="/"

for network in $(ip route list table 220 | cut -d' ' -f1); do
  if [[ "$network" == *"$sub"* ]]; then
    ping -c1 -W1 -b $(ipcalc -b $network | cut -d'=' -f2) || exit 0
  else
    ping -c1 -W1 $network || exit 0
  fi
done
