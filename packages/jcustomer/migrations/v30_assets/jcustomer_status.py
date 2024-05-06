import os
import requests
from requests.exceptions import RequestException

# the following try/except block will make the custom check compatible with any Agent version
try:
    # first, try to import the base class from old versions of the Agent...
    from checks import AgentCheck
except ImportError:
    # ...if the above failed, the check is running in Agent version 6 or later
    from datadog_checks.base import AgentCheck

__version__ = "1.0.0"


class CheckJcustomerstatus(AgentCheck):
    __NAMESPACE__ = "jcustomer"
    BUNDLE_CHECK_NAME = "bundle_status"

    def check(self, instance):
        self.check_bundles(instance)

    def __set_error(self, error):
        self.service_check(
            self.SERVICE_CHECK_NAME,
            AgentCheck.CRITICAL,
            message='JCustomer is not running or not ready: ' + error
        )

    def check_bundles(self, instance):
        error_lines = []
        filelist = []
        path = '/opt/jcustomer/jcustomer/data/cache/'

        for root, dirs, files in os.walk(path):
            for file in files:
                if file == 'bundle.info':
                    file_path = os.path.join(root, file)
                    filelist.append(file_path)

        for file in filelist:
            with open(file, 'r') as f:
                lines = f.readlines()
            for i in range(len(lines)):
                line = lines[i]
                if 'org.apache.unomi' not in line and 'org.jahia.jcustomer' not in line:
                    continue
                if lines[i + 1].strip() != '32':
                    error_lines.append(line.strip())

        if not error_lines:
            self.service_check(
                self.BUNDLE_CHECK_NAME,
                AgentCheck.OK,
                message='JCustomer bundles are OK.'
            )
        else:
            self.service_check(
                self.BUNDLE_CHECK_NAME,
                AgentCheck.CRITICAL,
                message='Following bundle states are problematic: ' + ' '.join(error_lines)
            )
