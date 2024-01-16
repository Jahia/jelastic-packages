import requests

# the following try/except block will make the custom check compatible with any Agent version
try:
    # first, try to import the base class from old versions of the Agent...
    from checks import AgentCheck
except ImportError:
    # ...if the above failed, the check is running in Agent version 6 or later
    from datadog_checks.checks import AgentCheck

__version__ = "1.0.0"


class CheckHealthcheckMetric(AgentCheck):

    __NAMESPACE__ = "jahia.healthcheck"
    HEALTHCHECK_METRIC_SERVICE_CHECK_NAME = "HealthcheckStatus"

    CONF_FOLDER = "/etc/datadog-agent/conf.d/healthcheck_metric.d"
    JAHIA_ROOT_TOKEN_FILE = f"{CONF_FOLDER}/jahia_root_token"

    def check(self, instance):
        try:
            with open(self.JAHIA_ROOT_TOKEN_FILE, 'r') as jahia_root_token_file:
                self.jahia_root_token = jahia_root_token_file.read()
        except FileNotFoundError:
            message = f"Failed to get the jahia root token because the {self.JAHIA_ROOT_TOKEN_FILE} file does not exist."
            self.service_check(
                self.HEALTHCHECK_METRIC_SERVICE_CHECK_NAME,
                AgentCheck.CRITICAL,
                message=message
            )

        healthcheck_url = "http://127.0.0.1/modules/healthcheck"
        headers = headers = {'Authorization': 'APIToken ' + self.jahia_root_token}

        try:
            response = requests.get(healthcheck_url, headers=headers)
            probes = response.json()["probes"]
        except requests.exceptions.RequestException as error:
            message = "Error while performing http request on " + healthcheck_url + ". Error: " + str(error)
            self.service_check(
                self.HEALTHCHECK_METRIC_SERVICE_CHECK_NAME,
                AgentCheck.CRITICAL,
                message=message
            )
            return
        except requests.exceptions.JSONDecodeError as error:
            message = "Error while decoding json from healthcheck response. Error: " + str(error)
            self.service_check(
                self.HEALTHCHECK_METRIC_SERVICE_CHECK_NAME,
                AgentCheck.CRITICAL,
                message=message
            )
            return

        for probe in probes:
            if probe["status"]["health"] == "GREEN":
                probe_value = 0
            elif probe["status"]["health"] == "YELLOW":
                probe_value = 1
            else:
                probe_value = 2
            self.gauge(
                probe["name"],
                probe_value,
                tags=["severity:" + probe["severity"]]
            )
