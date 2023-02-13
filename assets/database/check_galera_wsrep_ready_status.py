import pymysql
import pymysql.cursors

# the following try/except block will make the custom check compatible with any Agent version
try:
    # first, try to import the base class from old versions of the Agent...
    from checks import AgentCheck
except ImportError:
    # ...if the above failed, the check is running in Agent version 6 or later
    from datadog_checks.checks import AgentCheck, ConfigurationError

__version__ = "1.0.0"


class CheckGaleraWsrepReadyStatus(AgentCheck):
    SERVICE_CHECK_NAME = "check_galera_wsrep_ready_status"
    __NAMESPACE__ = "mysql"
    DESIRED_STATUS = "ON"
    query = "SELECT variable_value FROM information_schema.global_status WHERE variable_name LIKE 'wsrep_ready'"

    def check(self, instance):
        try:
            db = pymysql.connect(
                       host='localhost',
                       user=instance["username"],
                       password=instance["password"],
                       unix_socket=instance["sock"]
                )
            
            q = db.cursor()
            q.execute(self.query)
            resp = q.fetchall()
            actual_status = ','.join(resp[0])
            if actual_status == self.DESIRED_STATUS:
                self.service_check(
                    self.SERVICE_CHECK_NAME,
                    AgentCheck.OK,
                    message='Galera Node wsrep_ready status is ON'
                )
            else:
                self.service_check(
                    self.SERVICE_CHECK_NAME,
                    AgentCheck.CRITICAL,
                    message='Galera Node wsrep_ready status is not ON'
                )
            
        except Exception:
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL)
            self.log.exception("Can't connect to database.")
        finally:
            if db:
                db.close()
