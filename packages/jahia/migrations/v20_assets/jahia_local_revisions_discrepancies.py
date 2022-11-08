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


class CheckLocalRevisionsDiscrepancies(AgentCheck):

    SERVICE_CHECK_NAME = "local_revisions_discrepancies"
    __NAMESPACE__ = "jahia"

    query = 'SELECT * from jahia.JR_J_LOCAL_REVISIONS'

    def check(self, instance):
        ssl_context = make_insecure_ssl_client_context()
        db = None
        nodesListFile = instance["nodesListFile"]

        try: 
            with open(nodesListFile, 'r') as file:
                nodeList = file.read().strip().split(" ")
        except Exception:
           message = "Nodes list file (%s) didn't exist" % nodesListFile
           self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, message=message)
           return

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
            message = "Can't connect to the jahia database"
            self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, message=message)
            return

        else:
            ghostNodes = []
            for node, _ in resp:
                if node not in nodeList:
                    ghostNodes.append(node)
            missingNodes = []
            respNodes = [ row[0] for row in resp ]
            for node in nodeList:
                if node not in respNodes:
                    missingNodes.append(node)

            message = ""
            if ghostNodes:
                message += "Node(s) in jahia.JR_J_LOCAL_REVISIONS that shouldn't be there: %s\n" % ", ".join(ghostNodes) 
            if missingNodes:
                message += "Node(s) not present in jahia.JR_J_LOCAL_REVISIONS: %s\n" % ", ".join(missingNodes) 

            if ghostNodes or missingNodes:
                self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL, message=message)
            else:
                message = "No discrepancies found in jahia.JR_J_LOCAL_REVISIONS"
                self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK, message=message)

        finally:
            if db:
                db.close()
