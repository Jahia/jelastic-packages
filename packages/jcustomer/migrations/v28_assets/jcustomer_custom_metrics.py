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

class CheckCustomMetrics(AgentCheck):

    __NAMESPACE__ = "jcustomer"
    es_username = os.getenv('UNOMI_ELASTICSEARCH_USERNAME')
    es_password = os.getenv('UNOMI_ELASTICSEARCH_PASSWORD')
    # Fix for LOIM to handle http instead of https
    protocol = "https://" if os.getenv('UNOMI_ELASTICSEARCH_SSL_ENABLE') != "false" else "http://"
    es_endpoint = protocol + str(os.getenv('UNOMI_ELASTICSEARCH_ADDRESSES'))

    def check(self, instance):
        self.count_event(instance)

    def count_event(self, instance):
        index_pattern = '*-event-*'
        count_url = f'{self.es_endpoint}/{index_pattern}/_count'
        try:
            response = requests.get(count_url, auth=(self.es_username, self.es_password))
            self.gauge("event_count", response.json()['count'])

        except ValueError as exception:
            self.__set_error("jcustomer.event_count: Returned invalid json")
        except RequestException as exception:
            self.__set_error("jcustomer.event_count: Request failed")
        except Exception as exception:
            self.__set_error("jcustomer.event_count: An unexpected error occured")

        return

    def __set_error(self, error):
        self.log.error(error)
