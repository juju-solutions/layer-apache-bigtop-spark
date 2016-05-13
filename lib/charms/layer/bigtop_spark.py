from path import Path
from charms.reactive import is_state
from charmhelpers.core import hookenv
from charmhelpers.core import host
from charmhelpers.core import unitdata
from jujubigdata import utils
from charms.layer.apache_bigtop_base import Bigtop


class Spark(object):

    def __init__(self, dist_config):
        self.dist_config = dist_config

    # translate our execution_mode into the appropriate --master value
    def get_master_url(self, spark_master_host):
        mode = hookenv.config()['spark_execution_mode']
        master = None
        if mode.startswith('local') or mode == 'yarn-cluster':
            master = mode
        elif mode == 'standalone':
            master = 'spark://{}:7077'.format(spark_master_host)
        elif mode.startswith('yarn'):
            master = 'yarn-client'
        return master

    def get_roles(self):
        roles = ['spark-worker', 'spark-client']
        if is_state('leadership.is_leader'):
            roles.append('spark-master')
            roles.append('spark-history-server')
        return roles

    def set_log_permissions(self):
        events_dir = 'hdfs:///var/log/spark/'
        utils.run_as('hdfs', 'hdfs', 'dfs', '-mkdir', '-p', events_dir)
        utils.run_as('hdfs', 'hdfs', 'dfs', '-chown', '-R', 'ubuntu:spark', events_dir)

    def setup(self):
        self.set_log_permissions()
        self.install_demo()
        self.open_ports()

    def configure(self, available_hosts):
        if not unitdata.kv().get('spark.bootstrapped', False):
            self.setup()
            unitdata.kv().set('spark.bootstrapped', True)

        bigtop = Bigtop()
        hosts = {
            'namenode': available_hosts['namenode'],
            'spark': available_hosts['spark-master'],
        }

        if 'resourcemanager' in available_hosts:
            hosts['resourcemanager'] = available_hosts['resourcemanager']

        roles = self.get_roles()

        override = {
            'spark::common::master_url': self.get_master_url(available_hosts['spark-master']),
        }

        bigtop.render_site_yaml(hosts, roles, override)
        bigtop.trigger_puppet()
        # There is a race condition here.
        # The work role will not start the first time we trigger puppet apply.
        # The exception in /var/logs/spark:
        # Exception in thread "main" org.apache.spark.SparkException: Invalid master URL: spark://:7077
        # The master url is not set at the time the worker start the first time.
        # TODO(kjackal): ...do the needed... (investiate,debug,submit patch) 
        bigtop.trigger_puppet()

    def install_demo(self):
        '''
        Install sparkpi.sh to /home/ubuntu (executes SparkPI example app)
        '''
        demo_source = 'scripts/sparkpi.sh'
        demo_target = '/home/ubuntu/sparkpi.sh'
        Path(demo_source).copy(demo_target)
        Path(demo_target).chmod(0o755)
        Path(demo_target).chown('ubuntu', 'hadoop')

    def start(self):
        if unitdata.kv().get('spark.uprading', False):
            return

        # stop services (if they're running) to pick up any config change
        self.stop()
        # always start the history server, start master/worker if we're standalone
        host.service_start('spark-history-server')
        if hookenv.config()['spark_execution_mode'] == 'standalone':
            host.service_start('spark-master')
            host.service_start('spark-worker')

    def stop(self):
        if not unitdata.kv().get('spark.installed', False):
            return
        # Only stop services if they're running
        if utils.jps("HistoryServer"):
            host.service_stop('spark-history-server')
        if utils.jps("Master"):
            host.service_stop('spark-master')
        if utils.jps("Worker"):
            host.service_stop('spark-worker')

    def open_ports(self):
        for port in self.dist_config.exposed_ports('spark'):
            hookenv.open_port(port)

    def close_ports(self):
        for port in self.dist_config.exposed_ports('spark'):
            hookenv.close_port(port)
