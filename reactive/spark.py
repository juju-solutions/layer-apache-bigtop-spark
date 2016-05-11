import subprocess
from charms.reactive import when, when_not, is_state, set_state, remove_state
from charms.layer.apache_bigtop_base import Bigtop, get_layer_opts
from charmhelpers.core import host, hookenv
from charms import layer


def set_deployment_mode_state(state):
    if is_state('spark.yarn.installed'):
        remove_state('spark.yarn.installed')
    if is_state('spark.standalone.installed'):
        remove_state('spark.standalone.installed')
    set_state(state)
    

@when('hadoop.hdfs.ready', 'puppet.available')
@when_not('hadoop.yarn.ready', 'spark.standalone.installed')
def install_spark_standalone(hadoop):
    nns = hadoop.namenodes()
    hookenv.status_set('maintenance', 'installing spark standalone')
    spark_master_host = subprocess.check_output(['facter', 'fqdn']).strip().decode()
    bigtop = Bigtop()
    hiera_params={
        'bigtop::hadoop_head_node': nns[0],
        'bigtop::roles': ['spark-master', 'spark-worker', 'spark-history-server','spark-client'],
        'bigtop::roles_enabled': True,
        'hadoop::common_hdfs::hadoop_namenode_host': nns[0],
        'spark::common::master_host': spark_master_host,
    }
    # There is a race condition here  
    # bigtop.install(hosts={'spark': spark_master_host}, roles="['spark-worker','spark-master']")
    # fails to bring up the worker
    # TODO(kjackal): Investigate why
    bigtop.install(hosts={}, hiera_params=hiera_params)
    # Of course we need to run this twice....
    bigtop.install(hosts={}, hiera_params=hiera_params)
    set_deployment_mode_state('spark.standalone.installed')
    hookenv.status_set('active', 'ready (standalone)')


@when('hadoop.hdfs.ready', 'hadoop.yarn.ready', 'puppet.available')
@when_not('spark.yarn.installed')
def install_spark_yarn(hdfs, yarn):
    nns = hdfs.namenodes()
    rms = yarn.resourcemanagers()
    hookenv.status_set('maintenance', 'installing spark yarn')
    spark_master_host = subprocess.check_output(['facter', 'fqdn']).strip().decode()
    bigtop = Bigtop()
    hiera_params={
        'bigtop::hadoop_head_node': nns[0],
        'bigtop::roles': ['spark-master', 'spark-worker', 'spark-history-server','spark-client'],
        'bigtop::roles_enabled': True,
        'hadoop::common_hdfs::hadoop_namenode_host': nns[0],
        'spark::common::master_host': spark_master_host,
        'hadoop::common_yarn::hadoop_ps_host': rms[0],
        'hadoop::common_yarn::hadoop_rm_host': rms[0],
        'hadoop::common_mapred_app::jobtracker_host': rms[0],
        'hadoop::common_mapred_app::mapreduce_jobhistory_host': rms[0],
    }
    # There is a race condition here  
    # bigtop.install(hosts={'spark': spark_master_host}, roles="['spark-worker','spark-master']")
    # fails to bring up the worker
    # TODO(kjackal): Investigate why
    bigtop.install(hosts={}, hiera_params=hiera_params)
    # Of course we need to run this twice....
    bigtop.install(hosts={}, hiera_params=hiera_params)
    set_deployment_mode_state('spark.yarn.installed')
    hookenv.status_set('active', 'ready (yarn & standalone)')

@when('hadoop.yarn.ready', 'puppet.available')
@when_not('hadoop.hdfs.ready')
def blocked_on_hdfs(yarn):
    hookenv.status_set('blocked', 'please add hdfs')


@when('spark.installed', 'sparkpeers.joined')
def peers_update(sprkpeer):
    nodes = sprkpeer.get_nodes()
    nodes.append((hookenv.local_unit(), hookenv.unit_private_ip()))
    update_peers_config(nodes)


@when('spark.installed')
@when_not('sparkpeers.joined')
def no_peers_update():
    nodes = [(hookenv.local_unit(), hookenv.unit_private_ip())]
    update_peers_config(nodes)


def update_peers_config(nodes):
    nodes.sort()
    if data_changed('available.peers', nodes):
        spark = Spark(get_dist_config())
        # We need to reconfigure spark only if the master changes or if we
        # are in HA mode and a new potential master is added
        if spark.update_peers(nodes):
            hookenv.status_set('maintenance', 'Updating Apache Spark config')
            spark.stop()
            spark.configure()
            spark.start()
            report_status(spark)


