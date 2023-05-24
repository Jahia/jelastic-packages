import requests
import os

# the following try/except block will make the custom check compatible with any Agent version
try:
    # first, try to import the base class from old versions of the Agent...
    from checks import AgentCheck
except ImportError:
    # ...if the above failed, the check is running in Agent version 6 or later
    from datadog_checks.base import AgentCheck

__version__ = "1.0.0"

class CheckESstatus(AgentCheck):
    __NAMESPACE__ = "elasticsearch"
    SERVICE_CHECK_NAME = "es_status"

    def check(self, instance):
        es_username = os.getenv('UNOMI_ELASTICSEARCH_USERNAME')
        es_password = os.getenv('UNOMI_ELASTICSEARCH_PASSWORD')
        es_endpoint = "https://" + str(os.getenv('UNOMI_ELASTICSEARCH_ADDRESSES'))

        # Check if cluster is reachable
        try:
            response = requests.get(
                es_endpoint,
                auth=(es_username, es_password)
            )

            if response.status_code != 200:
                self.__set_error("Received wrong status code " + str(response.status_code))
                return

        except requests.RequestException as exception:
            self.__set_error("Request failed")
        except Exception as exception:
            self.__set_error("An unexpected error occured")

        # Check indices health & status
        indices_url = f"{es_endpoint}/_cat/indices?format=json"
        try:
            response = requests.get(
                indices_url,
                auth=(es_username, es_password)
            )

        except Exception as exception:
            self.__set_error("Unable to check indices")
            return

        indices = response.json()
        for index in indices:
            if index['health'] != 'green':
                self.__set_error("Index %s health is not green" % index['index'])
                return
            elif index['status'] != 'open':
                self.__set_error("Index %s status is not open" % index['index'])
                return

        # If nothing returns, check is OK
        self.service_check(
            self.SERVICE_CHECK_NAME,
            AgentCheck.OK,
            message='ElasticSearch is OK'
        )

    def __set_error(self, error):
        self.service_check(
            self.SERVICE_CHECK_NAME,
            AgentCheck.CRITICAL,
            message='ElasticSearch error: ' + error
        )
