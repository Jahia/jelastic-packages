import pymysql
import pymysql.cursors
import ssl

# the following try/except block will make the custom check compatible with any Agent version
try:
    # first, try to import the base class from old versions of the Agent...
    from checks import AgentCheck
except ImportError:
    # ...if the above failed, the check is running in Agent version 6 or later
    from datadog_checks.checks import AgentCheck, ConfigurationError

__version__ = "1.0.0"


def make_insecure_ssl_client_context():
    """Creates an insecure ssl context for integration that requires to use TLS without checking
    the host authenticity.
    :rtype ssl.Context
    """
    context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS)
    context.verify_mode = ssl.CERT_NONE
    return context


class CheckProxySQLBackendMissing(AgentCheck):

    SERVICE_CHECK_NAME = "backend_missing"
    __NAMESPACE__ = "proxysql"

    query = 'SELECT hostgroup, srv_host, status from stats_mysql_connection_pool where hostgroup=2'

    def check(self, instance):
        ssl_context = make_insecure_ssl_client_context()
        db = None

        try:
            db = pymysql.connect(
                host=instance["host"],
                user=instance["username"],
                port=instance["port"],
                password=instance["password"],
                connect_timeout=instance["connect_timeout"],
                read_timeout=instance["read_timeout"],
                ssl=ssl_context,
            )

            q = db.cursor()
            q.execute(self.query)
            resp = q.fetchall()

        except Exception:
            message = "Can't connect to ProxySQL"
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, message=message)
            return
        else:
            if len(resp) == 3:
                self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK)
            else:
                self.log.debug("the query return: {}".format(resp))
                theorical = ('galera_1', 'galera_2', 'galera_3')
                known_backend = [row[1] for row in resp]
                missing_tuple = set(theorical).difference(known_backend)
                missing = list(missing_tuple)
                missing.sort()
                mess_tpl = "Backend(s) {} is/are missing from to writer hostgroup."
                message = mess_tpl.format(", ".join(missing))
                self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                                   message=message)
        finally:
            if db:
                db.close()
