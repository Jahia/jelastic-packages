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
        "installed": "{} out of {} connection(s) is/are installed.",
        "inactive": "Strongswan service is enabled but not running.",
        "not_installed": "None of the {} connection(s) is/are installed.",
    }

    def check(self, instance):
        try:
            if not self.__checkServiceRunning():
                return
        except Exception:
            message = "Can't get strongswan service status."
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, message=message)
            return
        try:
            self.__checkConnections()
        except Exception:
            message = "Can't get strongswan connections status."
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, message=message)
            return

    def __checkServiceRunning(self):
        # If strongswan service is not enabled, it means there is no connection, so successful check
        service_enabled = subprocess.run(
            f'systemctl -q is-enabled {self.SYSTEMD_UNIT_NAME}',
            shell=True,
            capture_output=True
        ).returncode
        if service_enabled != 0:
            self.service_check(
                self.SERVICE_CHECK_NAME, AgentCheck.OK, message=self.CHECK_MESSAGES['disabled'])
            return False
        # If strongswan service is enabled but not active, it is a problem
        service_active = subprocess.run(
            f'systemctl -q is-active {self.SYSTEMD_UNIT_NAME}',
            shell=True,
            capture_output=True
        ).returncode
        if service_active != 0:
            self.service_check(
                self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, message=self.CHECK_MESSAGES['inactive'])
            return False
        return True

    def __checkConnections(self):
        # We get the status of all connections
        strongswan_status = subprocess.run(
            'sudo /usr/sbin/strongswan statusall',
            shell=True,
            capture_output=True
        ).stdout.decode("utf-8")
        r_existing = re.compile('.*child:.*TUNNEL.*')
        r_installed = re.compile('.*:\s\sINSTALLED.*')
        # get uniq rightsubnet from existing routed list
        # (we get uniq because if "HA"-like connections may exist
        # with the same subnet as the main conections, so the HA connection
        # is displayed as "routed" while not established and even less installed)
        subnets_set = set()
        ip_regex = r"^.* === ((\d{1,3}\.){3}\d{1,3}/\d{1,2}) .*$"
        for tunnel in re.findall(r_existing, strongswan_status):
            subnets_set.add(re.search(ip_regex, tunnel).group(1))
        conn_existing_num = len(subnets_set)
        # Number of running connections
        conn_installed_num = len(re.findall(r_installed, strongswan_status))
        if conn_installed_num:
            self.service_check(
                self.SERVICE_CHECK_NAME,
                AgentCheck.OK,
                message=self.CHECK_MESSAGES['installed'].format(conn_installed_num, conn_existing_num)
            )
        else:
            self.service_check(
                self.SERVICE_CHECK_NAME,
                AgentCheck.CRITICAL,
                message=self.CHECK_MESSAGES['not_installed'].format(conn_existing_num)
            )
