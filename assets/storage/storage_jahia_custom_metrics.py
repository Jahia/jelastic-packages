import shutil
import subprocess

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
    DATASTORE_SIZE_METRIC_NAME = "customer_disk_usage.datastore"

    def check(self, instance):
        self.__get_datastore_size()

    def __get_datastore_size(self):
        df_size = shutil.disk_usage("/").used
        try:
            res = subprocess.run(
                ["sudo", "du", "-bs", "/", "--exclude", "/data", "--exclude", "/glustervolume", "--exclude", "/proc"],
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            self.log.error(f'{self.__NAMESPACE__}.{self.DATASTORE_SIZE_METRIC_NAME}: The "du" command failed, aborting. Error:\n{e.stderr}')
            return

        no_gluster_du_size = int(res.stdout.split("\t")[0])

        self.gauge(self.DATASTORE_SIZE_METRIC_NAME, df_size - no_gluster_du_size)
