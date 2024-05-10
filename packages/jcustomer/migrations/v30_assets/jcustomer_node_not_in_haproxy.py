import os
import subprocess
import socket

# the following try/except block will make the custom check compatible with any Agent version
try:
    # first, try to import the base class from old versions of the Agent...
    from checks import AgentCheck
except ImportError:
    # ...if the above failed, the check is running in Agent version 6 or later
    from datadog_checks.base import AgentCheck

__version__ = "1.0.0"


class CheckNodeInHaproxyPool(AgentCheck):
    __NAMESPACE__ = "jcustomer"
    SERVICE_CHECK_NAME = "jcustomer_node_not_in_haproxy_pool"
    IP = socket.gethostbyname(socket.getfqdn())  # get the local ip
    HAPROXY_NODES_COUNT = int(os.environ["HAPROXY_NODES_COUNT"])
    # the following command:
    #   * runs a tcpdump for 10s
    #     * this tcpdump list for http GET request on port 80 with the local ip as destination
    #   * the tcpdump output is then filtred by awk
    #     * it detect the client IP
    #     * if the request user "user-agent: HAProxy", it add an index (based on the client IP) on the "a" array and print its length
    #   * and we just keep the last awk output line
    CMD = f"timeout --preserve-status 10 tcpdump -s0 -ntAql 'dst host {IP} and dst port 80 and tcp[((tcp[12:1] & 0xf0) >> 2):4] = 0x47455420'" \
          + """| awk '$1=="IP" {ip=gensub(/\.[0-9]+$/, "", 1, $2)}; $1=="user-agent:" && $2=="HAProxy" {a[ip]; print length(a)}' | tail -n1"""

    def check(self, instance):
        runcmd = subprocess.Popen(self.CMD,shell=True,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
        try:
            count = int(runcmd.communicate()[0])
        except Exception:
            count = 0

        if count == self.HAPROXY_NODES_COUNT:
            self.service_check(
                self.SERVICE_CHECK_NAME,
                AgentCheck.OK,
                message='jCustomer node present in pool of all HAProxy nodes')
        elif count == 0:
            self.service_check(
                self.SERVICE_CHECK_NAME,
                AgentCheck.CRITICAL,
                message='jCustomer node missing from pool of all HAProxy node')
        elif count < self.HAPROXY_NODES_COUNT:
            self.service_check(
                self.SERVICE_CHECK_NAME,
                AgentCheck.CRITICAL,
                message='jCustomer node missing from pool of at least one HAProxy node')
        else:
            self.service_check(
                self.SERVICE_CHECK_NAME,
                AgentCheck.CRITICAL,
                message='jCustomer node is present in more HAProxy nodes pool than it should be')
