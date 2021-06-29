from datetime import datetime

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

    def check(self, instance):
        try:
            dict={}
            now = datetime.now().strftime('%d/%b/%Y:%H:%M:%S')
            now_dt = datetime.strptime(now, '%d/%b/%Y:%H:%M:%S')
            new_file_time = "0:0:0"
            new_file_time_dt = datetime.strptime(new_file_time, '%H:%M:%S')
            current_time = datetime.now().strftime('%H:%M:%S')
            current_time_dt = datetime.strptime(current_time, '%H:%M:%S')
            diff = current_time_dt - new_file_time_dt
            diff_in_minutes = diff.total_seconds()/60
            # Run check only if it is 30 minutes past mid-night
            if diff_in_minutes > self.DURATION:
                with open(self.FILENAME, 'r') as f:
                    for line in f.read().splitlines():
                        if self.LOCALHOST not in line and self.PATTERN in line and self.SOURCE in line:
                            ip = line.strip().split(' - - ')[0]
                            date = line.strip().split('[')[1].split(' +0000')[0]
                            dict[ip] = date
                    if len(dict) > 1:
                        count = 0
                        for date in dict.values():
                            date_dt = datetime.strptime(date, '%d/%b/%Y:%H:%M:%S')
                            time_diff = now_dt - date_dt
                            time_diff_minutes = time_diff.total_seconds()/60
                            if time_diff_minutes > self.DURATION:
                                count += 1
                        if count >= 1:
                            self.service_check(
                                self.SERVICE_CHECK_NAME,
                                AgentCheck.CRITICAL,
                                message='Jahia Node missing from pool of one or more HAProxy Nodes'
                            )
                        else:
                            self.service_check(
                                self.SERVICE_CHECK_NAME,
                                AgentCheck.OK,
                                message='Jahia Node present in pool of both HAProxy Nodes'
                            )
                    elif len(dict) == 1:
                        date = dict.values()[0]
                        date_dt = datetime.strptime(date, '%d/%b/%Y:%H:%M:%S')
                        time_diff = now_dt - date_dt
                        time_diff_minutes = time_diff.total_seconds()/60
                        if time_diff_minutes > self.DURATION:
                            self.service_check(
                                self.SERVICE_CHECK_NAME,
                                AgentCheck.CRITICAL,
                                message='Jahia Node missing from pool of both HAProxy Nodes'
                            )
                        else:
                            self.service_check(
                                self.SERVICE_CHECK_NAME,
                                AgentCheck.CRITICAL,
                                message='Jahia Node missing from pool of one HAProxy Node'
                            )
                    else:
                        self.service_check(
                            self.SERVICE_CHECK_NAME,
                            AgentCheck.CRITICAL,
                            message='Jahia Node missing from pool of both HAProxy Nodes'
                        )
            # Ignore check for new Access log file for 30 minutes
            else:
                self.service_check(
                    self.SERVICE_CHECK_NAME,
                    AgentCheck.OK,
                    message='Access log file too young to determine status of Jahia Nodes in HAProxy pool'
                )
        except Exception:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL)
            self.log.exception("Can't get access logs from jahia node.")
            raise
