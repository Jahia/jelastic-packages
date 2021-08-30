from datetime import datetime
import os

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
    PATTERN = "modules/healthcheck?token="
    SOURCE = "HAProxy"
    FILENAME = "/opt/tomcat/logs/access_log.txt"
    DURATION = float(30)
    HAPROXY_NODES_COUNT = int(os.environ["HAPROXY_NODES_COUNT"])

    def check(self, instance):
        try:
            haproxy_ips = {}
            now = datetime.now().strftime('%d/%b/%Y:%H:%M:%S')
            now_dt = datetime.strptime(now, '%d/%b/%Y:%H:%M:%S')
            new_file_time = "0:0:0"
            new_file_time_dt = datetime.strptime(new_file_time, '%H:%M:%S')
            current_time = datetime.now().strftime('%H:%M:%S')
            current_time_dt = datetime.strptime(current_time, '%H:%M:%S')
            diff = current_time_dt - new_file_time_dt
            diff_in_minutes = diff.total_seconds()/60
            node_uptime = float(open('/proc/uptime').read().split()[0])
            node_uptime_mins = node_uptime/60
            # Run check if it is 30 minutes past mid-night and node is up over 30 minutes
            if diff_in_minutes > self.DURATION and node_uptime_mins > self.DURATION:
                with open(self.FILENAME, 'r') as f:
                    for line in f.read().splitlines():
                        if self.LOCALHOST not in line and self.PATTERN in line and self.SOURCE in line:
                            haproxy_ip = line.strip().split(' - - ')[0]
                            date = line.strip().split('[')[1].split(' +0000')[0]
                            haproxy_ips[haproxy_ip] = date
                    count = 0
                    for date in haproxy_ips.values():
                        date_dt = datetime.strptime(date, '%d/%b/%Y:%H:%M:%S')
                        time_diff = now_dt - date_dt
                        time_diff_minutes = time_diff.total_seconds()/60
                        if time_diff_minutes < self.DURATION:
                            count += 1

                    if count == self.HAPROXY_NODES_COUNT:
                        self.service_check(
                            self.SERVICE_CHECK_NAME,
                            AgentCheck.OK,
                            message='Jahia Node present in pool of all HAProxy Nodes'
                        )
                    elif count < self.HAPROXY_NODES_COUNT:
                        self.service_check(
                            self.SERVICE_CHECK_NAME,
                            AgentCheck.CRITICAL,
                            message='Jahia Node missing from pool of a least 1 HAProxy Nodes'
                        )
                    else:
                        # WTF ?
                        self.service_check(
                            self.SERVICE_CHECK_NAME,
                            AgentCheck.CRITICAL,
                            message='Jahia Node is present in more HAProxy Nodes pool than it should be'
                        )
        except Exception:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL)
            self.log.exception("Can't get access logs from jahia node.")
            raise
