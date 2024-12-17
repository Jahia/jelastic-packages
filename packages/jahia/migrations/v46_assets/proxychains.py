import subprocess

# the following try/except block will make the custom check compatible with any Agent version
try:
    # first, try to import the base class from old versions of the Agent...
    from checks import AgentCheck
except ImportError:
    # ...if the above failed, the check is running in Agent version 6 or later
    from datadog_checks.checks import AgentCheck, ConfigurationError

__version__ = "1.0.0"


class ProxychainsCheck(AgentCheck):

    SERVICE_CHECK_NAME = "proxyfication"
    __NAMESPACE__ = "proxychains"

    def check(self, instance):
        try:
            is_loaded_cmd = "sudo lsof -p$(pgrep -u tomcat java) | grep proxychains"
            process = subprocess.run(is_loaded_cmd, shell=True)
            if process.returncode != 0:
                message = "Tomcat is not using proxychains"
                self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, message=message)
                return

            is_closed_cmd = "proxychains nc -vz forbidden.com.com 443"
            process = subprocess.run(is_closed_cmd, shell=True)
            if process.returncode != 1:
                message = "proxychains forbidden endpoint is reachable"
                self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, message=message)
                return

            is_open_cmd = "proxychains nc -vz repository.apache.org 443"
            process = subprocess.run(is_open_cmd, shell=True)
            if process.returncode != 0:
                message = "proxychains whitelisted endpoint is unreachable"
                self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, message=message)
                return

            # Getting there means it's all good
            message = "proxychains checks are ok"
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK, message=message)

        except Exception as e:
            message = "proxychains check failed"
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, message=message)
