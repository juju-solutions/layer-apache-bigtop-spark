from charms.reactive import when, when_not, is_state, set_state, remove_state, when_any
from charms.layer.apache_bigtop_base import get_fqdn
from charms.layer.bigtop_spark import Spark
from charmhelpers.core import hookenv
from charms import leadership
from charms.reactive.helpers import data_changed
from charms.layer.hadoop_client import get_dist_config


def set_deployment_mode_state(state):
    if is_state('spark.yarn.installed'):
        remove_state('spark.yarn.installed')
    if is_state('spark.standalone.installed'):
        remove_state('spark.standalone.installed')
    remove_state('spark.ready.to.install')
    set_state('spark.started')
    set_state(state)


def report_status():
    mode = hookenv.config()['spark_execution_mode']
    if (not is_state('spark.yarn.installed')) and mode.startswith('yarn'):
        hookenv.status_set('blocked',
                           'Yarn execution mode not available')
        return

    if mode == 'standalone' and is_state('leadership.is_leader'):
        mode = mode + " - master"

    hookenv.status_set('active', 'Ready ({})'.format(mode))


def install_spark(hadoop, yarn=False):
    spark_master_host = leadership.leader_get('master-fqdn')
    nns = hadoop.namenodes()
    hosts = {
        'namenode': nns[0],
        'spark-master': spark_master_host,
    }

    if yarn:
        rms = hadoop.resourcemanagers()
        hosts['resourcemanager'] = rms[0]

    dist = get_dist_config()
    spark = Spark(dist)
    spark.configure(hosts)

@when_any('spark.standalone.installed', 'spark.yarn.installed' )
@when('config.changed', 'hadoop.hdfs.ready')
def reconfigure_spark(hadoop):
    config = hookenv.config()
    mode = hookenv.config()['spark_execution_mode']
    hookenv.status_set('maintenance', 
                       'Changing default execution mode to {}'.format(mode))

    yarn = False
    if is_state('hadoop.yarn.ready'):
        yarn = True

    install_spark(hadoop, yarn)
    report_status()


@when('hadoop.hdfs.ready', 'bigtop.available')
@when_not('spark.ready.to.install')
def ready_to_install(hadoop):
    set_state('spark.ready.to.install')


@when_any('leadership.changed.master-fqdn', 'spark.ready.to.install')
@when('hadoop.hdfs.ready', 'bigtop.available')
@when_not('hadoop.yarn.ready')
def install_spark_standalone(hdfs):
    spark_master_host = leadership.leader_get('master-fqdn')
    if (not data_changed('master-host', spark_master_host)) and \
       is_state('spark.standalone.installed'):
        return

    hookenv.status_set('maintenance', 'Installing spark standalone')
    install_spark(hdfs)
    set_deployment_mode_state('spark.standalone.installed')
    report_status()


@when_any('leadership.changed.master-fqdn', 'spark.ready.to.install')
@when('hadoop.hdfs.ready', 'hadoop.yarn.ready', 'bigtop.available')
def install_spark_yarn(hdfs, yarn):
    spark_master_host = leadership.leader_get('master-fqdn')
    if (not data_changed('master-host', spark_master_host)) and \
       is_state('spark.yarn.installed'):
        return

    hookenv.status_set('maintenance', 'Installing spark yarn')
    install_spark(hdfs, yarn=True)
    set_deployment_mode_state('spark.yarn.installed')
    report_status()


@when('bigtop.available')
@when_not('hadoop.hdfs.ready')
def blocked_on_hdfs():
    dist = get_dist_config()
    spark = Spark(dist)
    spark.stop()
    remove_state('spark.started')
    hookenv.status_set('blocked', 'Waiting for a relation to HDFS')


@when('leadership.is_leader', 'bigtop.available')
def send_fqdn():
    spark_master_host = get_fqdn()
    leadership.leader_set({'master-fqdn': spark_master_host})
    hookenv.log("Setting leader to {}".format(spark_master_host))


@when('spark.started', 'client.joined')
def client_present(client):
    client.set_spark_started()


@when('client.joined')
@when_not('spark.started')
def client_should_stop(client):
    client.clear_spark_started()


