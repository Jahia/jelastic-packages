import os
import requests

# the following try/except block will make the custom check compatible with any Agent version
try:
    # first, try to import the base class from old versions of the Agent...
    from checks import AgentCheck
except ImportError:
    # ...if the above failed, the check is running in Agent version 6 or later
    from datadog_checks.checks import AgentCheck

__version__ = "1.0.0"


class CheckAugmentedSearchStatus(AgentCheck):

    AS_SERVICE_CHECK_NAME = "AugmentedSearchStatus"
    AS_CONNECTION_SERVICE_CHECK_NAME = "AugmentedSearchConnection"
    AS_CONNECTION_HEALTH_SERVICE_CHECK_NAME = "AugmentedSearchConnectionHealth"
    __NAMESPACE__ = "augmented_search"

    CONF_FOLDER = "/etc/datadog-agent/conf.d/augmented_search.d"
    JAHIA_ROOT_TOKEN_FILE = f"{CONF_FOLDER}/jahia_root_token"

    es_username = os.environ["JAHIA_ELASTICSEARCH_USERNAME"]
    es_password = os.environ["JAHIA_ELASTICSEARCH_PASSWORD"]
    # Fix for LOIM to handle http instead of https
    protocol = "https://" if os.getenv('JAHIA_ELASTICSEARCH_SSL_ENABLE') != "false" else "http://"
    es_endpoint = protocol + os.environ["JAHIA_ELASTICSEARCH_ADDRESSES"]

    INDICES_SIZE_METRIC_NAME = "customer_disk_usage.augmented_search"

    def check(self, instance):
        try:
            with open(self.JAHIA_ROOT_TOKEN_FILE, 'r') as jahia_root_token_file:
                self.jahia_root_token = jahia_root_token_file.read()
        except FileNotFoundError:
            message = f"Failed to get the jahia root token because the {self.JAHIA_ROOT_TOKEN_FILE} file does not exist."
            self.service_check(
                self.AS_SERVICE_CHECK_NAME,
                AgentCheck.CRITICAL,
                message=message
            )

        self.check_as_status(instance)
        self.check_as_connection(instance)
        if os.environ['_ROLE'] == "Processing":
            self.count_languages()

        # We update the namespace so it is the same as the other custom metrics, that is "jahia"
        # instead of "augmented_search" so we have all of them in the same place
        namespace = self.__NAMESPACE__
        self.__NAMESPACE__ = "jahia"

        self.get_as_indices_size()

        # And now we set the namespace back to "augmented_search" for next checks
        self.__NAMESPACE__ = namespace

    def check_as_status(self, instance):
        AS_PROBE_NAME = "Augmented Search"
        healthcheck_url = "http://127.0.0.1/modules/healthcheck"
        headers = headers = {'Authorization': 'APIToken ' + self.jahia_root_token}

        try:
            response = requests.get(healthcheck_url, headers=headers)
            probes = response.json()["probes"]
        except requests.exceptions.RequestException as error:
            message = "Error while performing http request on " + healthcheck_url + ". Error: " + str(error)
            self.service_check(
                self.AS_SERVICE_CHECK_NAME,
                AgentCheck.CRITICAL,
                message=message
            )
            return
        except requests.exceptions.JSONDecodeError as error:
            message = "Error while decoding json from healthcheck response. Error: " + str(error)
            self.service_check(
                self.AS_SERVICE_CHECK_NAME,
                AgentCheck.CRITICAL,
                message=message
            )
            return

        as_probe = None
        # Look for Augmented search probe in healthcheck response
        for probe in probes:
            if probe["name"] == AS_PROBE_NAME:
                as_probe = probe

        if as_probe:
            if as_probe["status"]["health"] == "GREEN":
                self.service_check(
                    self.AS_SERVICE_CHECK_NAME,
                    AgentCheck.OK,
                    message=as_probe["status"]["message"]
                )
            elif as_probe["status"]["health"] == "YELLOW":
                self.service_check(
                    self.AS_SERVICE_CHECK_NAME,
                    AgentCheck.WARNING,
                    message=as_probe["status"]["message"]
                )
            else:
                self.service_check(
                    self.AS_SERVICE_CHECK_NAME,
                    AgentCheck.CRITICAL,
                    message=as_probe["status"]["message"]
                )
        else:
            self.service_check(
                self.AS_SERVICE_CHECK_NAME,
                AgentCheck.CRITICAL,
                message="No Augmented Search probe found in healthcheck response"
            )

    def check_as_connection(self, instance):
        jahia_cloud_connection_name = "jahia-cloud_augmented-search"
        url = "http://localhost:8080/modules/graphql"
        headers = headers = {
            'Authorization': 'APIToken ' + self.jahia_root_token,
            'Origin': 'http://localhost:8080',
            'Content-Type': 'application/json'
        }

        # Check if the connection used for AS is jahia-cloud_augmented-search
        data = {
            "query": "query { admin { search { currentConnection } } }"
        }

        response = self.__send_post_request(url, headers, data, self.AS_CONNECTION_SERVICE_CHECK_NAME)
        if not response:
            return
        currentConnection = None
        try:
            currentConnection = response["data"]["admin"]["search"]["currentConnection"]
        except Exception:
            message = "Cannot get AS currentConnection in response body: " + str(response)
            self.service_check(
                self.AS_CONNECTION_SERVICE_CHECK_NAME,
                AgentCheck.CRITICAL,
                message=message
            )
            return

        if currentConnection == "jahia-cloud_augmented-search":
            message = "AS is using " + jahia_cloud_connection_name + " connection id."
            self.service_check(
                self.AS_CONNECTION_SERVICE_CHECK_NAME,
                AgentCheck.OK,
                message=message
            )
        elif not currentConnection:
            message = "There is no connection configured for AS."
            self.service_check(
                self.AS_CONNECTION_SERVICE_CHECK_NAME,
                AgentCheck.CRITICAL,
                message=message
            )
        else:
            message = "AS is using " + str(currentConnection) + " connection id instead of " + jahia_cloud_connection_name + "."
            self.service_check(
                self.AS_CONNECTION_SERVICE_CHECK_NAME,
                AgentCheck.CRITICAL,
                message=message
            )

        # Check if the jahia-cloud_augmented-search connection is valid
        data = {
            "query": "query { admin { search { dbConnections {connectionId} } } }"
        }
        response = self.__send_post_request(url, headers, data, self.AS_CONNECTION_HEALTH_SERVICE_CHECK_NAME)
        if not response:
            return
        try:
            valid_connections = response["data"]["admin"]["search"]["dbConnections"]
        except KeyError:
            message = "Cannot get ES valid connection list in response body"
            self.service_check(
                self.AS_CONNECTION_HEALTH_SERVICE_CHECK_NAME,
                AgentCheck.CRITICAL,
                message=message
            )
            return
        as_connection_found = False
        for connection in valid_connections:
            if connection["connectionId"] == jahia_cloud_connection_name:
                as_connection_found = True
                break

        if as_connection_found:
            message = "AS connection is valid"
            self.service_check(
                self.AS_CONNECTION_HEALTH_SERVICE_CHECK_NAME,
                AgentCheck.OK,
                message=message
            )
        else:
            message = "AS connection is not valid"
            self.service_check(
                self.AS_CONNECTION_HEALTH_SERVICE_CHECK_NAME,
                AgentCheck.CRITICAL,
                message=message
            )

    def count_languages(self):
        url = self.es_endpoint + "/_cat/indices"
        params = {"format": "json"}

        try:
            response = requests.get(url, auth=(self.es_username, self.es_password), params=params)
            indices = response.json()
        except ValueError as exception:
            self.__set_error(f"{__NAMESPACE__}.count_languages: Returned invalid json")
        except RequestException as exception:
            self.__set_error(f"{__NAMESPACE__}.count_languages: Request failed")
        except Exception as exception:
            self.__set_error(f"{__NAMESPACE__}.count_languages: An unexpected error occured")

        languages = [index["index"].split("__")[-2] for index in indices]
        try:
            languages.remove("file")
        except ValueError:
            pass

        self.gauge("languages_count", len(set(languages)))

    def get_as_indices_size(self):
        metric_name = f"{self.__NAMESPACE__}.{self.INDICES_SIZE_METRIC_NAME}"

        url = self.es_endpoint + "/_cat/indices"
        params = {'bytes': 'b', 'format': 'json'}
        try:
            response = requests.get(url, auth=(self.es_username, self.es_password), params=params)
            indices = response.json()
        except ValueError as exception:
            self.log.error(metric_name + ": Returned invalid json")
            return
        except RequestException as exception:
            self.log.error(metric_name + ": Request failed")
            return
        except Exception as exception:
            self.log.error(metric_name + ": An unexpected error occured")
            return

        total_size = sum([int(index['pri.store.size']) for index in indices])

        self.gauge(self.INDICES_SIZE_METRIC_NAME, total_size)

    def __send_post_request(self, url, headers, data, check_name):
        try:
            response = requests.post(url, headers=headers, json=data)
            return response.json()
        except requests.exceptions.RequestException as error:
            message = "Error while performing http request on " + url + ". Error: " + str(error)
            self.service_check(
                check_name,
                AgentCheck.CRITICAL,
                message=message
            )
            return
        except requests.exceptions.JSONDecodeError as error:
            message = "Error while decoding json from healthcheck response. Error: " + str(error)
            self.service_check(
                check_name,
                AgentCheck.CRITICAL,
                message=message
            )
            return
