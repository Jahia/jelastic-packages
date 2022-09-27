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


class CheckProxySQLConnectionDiscrepancies(AgentCheck):

    SERVICE_CHECK_NAME = "connections_discrepancies"
    __NAMESPACE__ = "proxysql"

    query = 'SELECT hostgroup, srv_host, status from stats_mysql_connection_pool where hostgroup=2 and status="SHUNNED" and (ConnUsed>0 or ConnFree>0)'

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
            if not resp:
                message = "All connections are on the ONLINE backend."
                self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK, message=message)
            else:
                self.log.debug("the query return: {}".format(resp))
                mess_tpl = "{} have open connection(s) while not ONLINE"
                srv_hosts = [row[1] for row in resp]
                srv_hosts.sort()
                message = mess_tpl.format(", ".join(srv_hosts))
                self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                                   message=message)
        finally:
            if db:
                db.close()
