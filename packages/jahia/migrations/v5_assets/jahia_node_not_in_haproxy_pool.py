from datetime import datetime
import re

# the following try/except block will make the custom check compatible with any Agent version
try:
    # first, try to import the base class from old versions of the Agent...
    from checks import AgentCheck
except ImportError:
    # ...if the above failed, the check is running in Agent version 6 or later
    from datadog_checks.base import AgentCheck

__version__ = "1.0.0"


class CheckJahiaNodeNotInHaproxyPool(AgentCheck):
    __NAMESPACE__ = "jahia"
    SERVICE_CHECK_NAME = "jahia_node_not_in_haproxy_pool"
    LOCALHOST = "127.0.0.1"
    PATTERN = "healthcheck"
    FILENAME = "/opt/tomcat/logs/access_log.txt"

    def check(self, instance):
        try:
            with open(self.FILENAME, 'r') as f:
                line = f.read().splitlines()
                # Get lines that match healthcheck and not from localhost
                res = [x for x in line if not re.search(
                    self.LOCALHOST, x) and re.search(
                        self.PATTERN, x)][-2:]
                # Get last 2 IP's of healthcheck request
                ip_1 = re.split(' - - ', res[0])[0]
                ip_2 = re.split(' - - ', res[1])[0]
                # check for distinct IP's from 2 haproxy nodes
                if ip_1 != ip_2:
                    last_time = re.split(']', res[0])[0].split('[')[1].split(' +0000')[0]
                    last_time_dt = datetime.strptime(last_time, '%d/%b/%Y:%H:%M:%S')
                    now = datetime.now().strftime('%d/%b/%Y:%H:%M:%S')
                    now_dt = datetime.strptime(now, '%d/%b/%Y:%H:%M:%S')
                    diff = now_dt - last_time_dt
                    diff_in_minutes = diff.total_seconds()/60
                    # check if last healthcheck request received is over 30 minutes
                    if diff_in_minutes > 30:
                        self.service_check(
                            self.SERVICE_CHECK_NAME,
                            AgentCheck.CRITICAL,
                            message='Jahia Node missing from Haproxy pool'
                        )
                    else:
                        self.service_check(
                            self.SERVICE_CHECK_NAME,
                            AgentCheck.OK,
                            message='Jahia Node present in Haproxy pool'
                        )
                else:
                    self.service_check(
                        self.SERVICE_CHECK_NAME,
                        AgentCheck.CRITICAL,
                        message='Jahia Node missing from Haproxy pool'
                    )
        except Exception:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL)
            self.log.exception("Can't get access logs from jahia node.")
            raise
