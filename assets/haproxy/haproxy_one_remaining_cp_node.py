from os import system
import requests
import re

# the following try/except block will make the custom check compatible with any Agent version
try:
    # first, try to import the base class from old versions of the Agent...
    from checks import AgentCheck
except ImportError:
    # ...if the above failed, the check is running in Agent version 6 or later
    from datadog_checks.base import AgentCheck

__version__ = "1.0.0"


class CheckNumberBrowsingRemaining(AgentCheck):
    __NAMESPACE__ = "haproxy"
    SERVICE_CHECK_NAME = "number_NODE_TYPE_PLACEHOLDER_remaining"
    BROWSING_BACKEND_NAME = 'BK_NAME_PLACEHOLDER'

    def check(self, instance):
        try:
            res = requests.get('http://localhost:80/haproxy_adm_panel?stats;csv;norefresh',
                               auth=(instance["username"], instance["password"]))
            haproxy_stats = res.text.splitlines()
            # With this regexp, we only keep individual backend lines, not the global BACKEND one
            r_backend = re.compile('^' + self.BROWSING_BACKEND_NAME + ',(?!BACKEND).*')
            r_backend_up = re.compile('.*,UP,.*')
            backend_stats = list(filter(r_backend.match, haproxy_stats))
            backend_up_stats = list(filter(r_backend_up.match, backend_stats))
            if len(backend_up_stats) <= 1:
                if len(backend_stats) != len(backend_up_stats):
                    self.service_check(
                        self.SERVICE_CHECK_NAME,
                        AgentCheck.CRITICAL,
                        message='Not enough NODE_TYPE_PLACEHOLDER nodes are running.'
                    )
                    return
            self.service_check(
                self.SERVICE_CHECK_NAME,
                AgentCheck.OK,
                message='Enough NODE_TYPE_PLACEHOLDER nodes are running.'
            )
            return
        except Exception:
            message = "Can't get Haproxy stats."
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, message=message)
            return
