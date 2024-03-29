import os
import pwd
from pymysql import cursors as mysql_cursors, connect as mysql_connect
import requests

# the following try/except block will make the custom check compatible with any Agent version
try:
    # first, try to import the base class from old versions of the Agent...
    from checks import AgentCheck
except ImportError:
    # ...if the above failed, the check is running in Agent version 6 or later
    from datadog_checks.checks import AgentCheck

__version__ = "1.0.0"


class CheckCustomMetrics(AgentCheck):

    __NAMESPACE__ = "jahia.custom_metrics"
    WORK_FOLDER = "/tmp/jahia_custom_metrics"
    CONF_FOLDER = "/etc/datadog-agent/conf.d/jahia_custom_metrics.d"
    JAHIA_ROOT_TOKEN_FILE = f"{CONF_FOLDER}/jahia_root_token"

    JAHIA_PRIVILEGED_USERS_COUNT = {
        "metric_name": "privileged_users_count",
        "script_path": f"{CONF_FOLDER}/jahia_privileged_users_count.groovy",
        "file_path": f"{WORK_FOLDER}/jahia_privileged_users_count",
    }

    DB_SIZE_METRIC_NAME = "customer_disk_usage.database"

    def check(self, instance):
        with open(self.JAHIA_ROOT_TOKEN_FILE, 'r') as jahia_root_token_file:
            self.jahia_root_token = jahia_root_token_file.read()

        try:
            os.mkdir(self.WORK_FOLDER)
            dd_agent_uid = pwd.getpwnam("dd-agent").pw_uid
            tomcat_uid = pwd.getpwnam("tomcat").pw_uid
            os.chown(self.WORK_FOLDER, dd_agent_uid, tomcat_uid)
            os.chmod(self.WORK_FOLDER, 0o770)
        except FileExistsError:
            pass

        self.__get_jahia_privileged_users_count()
        self.__get_db_size()

    def __get_jahia_privileged_users_count(self):
        prov_api_url = "http://127.0.0.1/modules/api/provisioning"
        headers = {'Authorization': 'APIToken ' + self.jahia_root_token}
        data = {'script': (None, '[{"executeScript": "file:' + self.JAHIA_PRIVILEGED_USERS_COUNT["script_path"] + '"}]')}

        # First we need to remove the previous file generated by the groovy script
        try:
            os.remove(self.JAHIA_PRIVILEGED_USERS_COUNT["file_path"])
        except FileNotFoundError:
            pass

        # Then we run the groovy script with the provisioning API
        try:
            response = requests.post(prov_api_url, headers=headers, files=data)
        except requests.exceptions.RequestException as error:
            self.log.error(f"Error while performing http request on {prov_api_url}. Error: {str(error)}")
            return

        if (response.status_code >= 400):
            self.log.error(f"The provisioning API returned a HTTP/{response.status_code} code. Error: {response.text}")
            return

        try:
            with open(self.JAHIA_PRIVILEGED_USERS_COUNT["file_path"], 'r') as users_count_file:
                self.gauge(
                    self.JAHIA_PRIVILEGED_USERS_COUNT["metric_name"],
                    users_count_file.read(),
                )
        except FileNotFoundError:
            self.log.error("The groovy script to count Jahia privileged users failed, no file was generated")

    def __get_db_size(self):
        db_config = {
            "host": "localhost",
            "user": os.environ['DB_USER'],
            "password": os.environ['DB_PASSWORD'],
            "port": 6033,
            "database": "jahia",
            "connect_timeout": 5,
        }
        query = 'SELECT SUM(DATA_LENGTH + INDEX_LENGTH) FROM information_schema.TABLES WHERE TABLE_SCHEMA="jahia"'

        try:
            conn = mysql_connect(**db_config)
            with conn.cursor() as c:
                c.execute(query)
                res = c.fetchone()[0]
        except Exception as e:
            self.log.error("An error occured when trying to query the database: " + str(e))
            return

        self.gauge(self.DB_SIZE_METRIC_NAME, res)
