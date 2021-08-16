from os import system
import subprocess
import re

# the following try/except block will make the custom check compatible with any Agent version
try:
    # first, try to import the base class from old versions of the Agent...
    from checks import AgentCheck
except ImportError:
    # ...if the above failed, the check is running in Agent version 6 or later
    from datadog_checks.base import AgentCheck

__version__ = "1.0.0"


class CheckStrongswanConnections(AgentCheck):

    SERVICE_CHECK_NAME = "ipsec_status"
    __NAMESPACE__ = "strongswan"
    SYSTEMD_UNIT_NAME = 'strongswan'
    CHECK_MESSAGES = {
        "disabled": "Strongswan service is disabled, no ipsec connection to check.",
        "established": "All connections are established.",
        "inactive": "Strongswan service is enabled but not running.",
        "not_established": "At least one connection is not established.",
    }

    def check(self, instance):
        try:
            if not self.__checkServiceRunning():
                return
        except Exception:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL)
            self.log.exception("Can't get strongswan service status.")
            raise
        try:
            self.__checkConnections()
        except Exception:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL)
            self.log.exception("Can't get strongswan connections status.")
            raise

    def __checkServiceRunning(self):
        # If strongswan service is not enabled, it means there is no connection, so successful check
        service_enabled = system(
            'systemctl -q is-enabled ' + self.SYSTEMD_UNIT_NAME)
        if service_enabled != 0:
            self.service_check(
                self.SERVICE_CHECK_NAME, AgentCheck.OK, message=self.CHECK_MESSAGES['disabled'])
            return False
        # If strongswan service is enabled but not active, it is a problem
        service_active = system(
            'systemctl -q is-active ' + self.SYSTEMD_UNIT_NAME)
        if service_active != 0:
            self.service_check(
                self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, message=self.CHECK_MESSAGES['inactive'])
            return False
        return True

    def __checkConnections(self):
        # We get the status of all connections
        strongswan_status = subprocess.Popen(
            ['sudo', '/usr/sbin/strongswan', 'statusall'], stdout=subprocess.PIPE).communicate()[0]
        r_existing = re.compile('.*child:.*TUNNEL.*')
        r_established = re.compile('.*: ESTABLISHED.*')
        # get uniq rightsubnet from existing routed list
        # (we get uniq because if "HA"-like connections may exist
        # with the same subnet as the main conections, so the HA connection
        # is displayed as "routed" while not established)
        subnets_set = set()
        ip_regex = r"^.* === ((\d{1,3}\.){3}\d{1,3}/\d{1,2}) .*$"
        for tunnel in re.findall(r_existing, strongswan_status):
            subnets_set.add(re.search(ip_regex, tunnel).group(1))
        conn_existing_num = len(subnets_set)
        # Number of running connections
        conn_established_num = len(re.findall(r_established, strongswan_status))
        if conn_existing_num != conn_established_num:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                                message=self.CHECK_MESSAGES['not_established'])
        else:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK,
                                message=self.CHECK_MESSAGES['established'])
