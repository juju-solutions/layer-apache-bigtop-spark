import subprocess
from charms.reactive import when, when_not, is_state, set_state, remove_state
from charms.layer.apache_bigtop_base import Bigtop, get_layer_opts
from charmhelpers.core import host, hookenv
from charms import layer


@when('hadoop.installed', 'puppet.available')
@when_not('spark.installed')
def install_spark(hadoop):

    namenodes = hadoop.namenodes()
    resourcemanagers = hadoop.resourcemanagers()
    print("*** {} {}***".format(namenodes, resourcemanagers))

    set_state('spark.installed')
    hookenv.status_set('maintenance', 'installing spark')
    spark_master_host = subprocess.check_output(['facter', 'fqdn']).strip().decode()
    bigtop = Bigtop()
    # There is a race condition here  
    # bigtop.install(hosts={'spark': spark_master_host}, roles="['spark-worker','spark-master']")
    # fails to bring up the worker
    # TODO(kjackal): Investigate why
    #bigtop.install(hosts={'spark': spark_master_host}, roles='spark-master')
    #bigtop.install(hosts={'spark': spark_master_host}, roles='spark-worker')
    #bigtop.install(hosts={'spark': spark_master_host}, roles='spark-on-yarn')
    #bigtop.install(hosts={'spark': spark_master_host}, roles='spark-history-server')
    #bigtop.install(hosts={'spark': spark_master_host}, roles='spark-client')
    hiera_params={
        'bigtop::roles_enabled': False,
        'hadoop::common_hdfs::hadoop_namenode_host': namenodes[0],
        'hadoop::common_yarn::hadoop_ps_host': resourcemanagers[0],
        'hadoop::common_yarn::hadoop_rm_host': resourcemanagers[0],
        'hadoop::common_mapred_app::jobtracker_host': resourcemanagers[0],
        'hadoop::common_mapred_app::mapreduce_jobhistory_host': resourcemanagers[0],
        'hadoop_cluster_node::cluster_components': ['hadoop', 'yarn', 'spark'],
        'spark::common::master_host': spark_master_host,
        'hadoop::hadoop_storage_dirs': ['/data/1', '/data/2'],
        'bigtop::hadoop_head_node': namenodes[0],
    }
    bigtop.install(hosts={}, hiera_params=hiera_params)
    # Of course we need to run this twice....
    bigtop.install(hosts={}, hiera_params=hiera_params)
    hookenv.status_set('active', 'ready')


@when('puppet.available')
@when_not('spark.installed')
def install_spark_standalone():
    set_state('spark.installed')
    hookenv.status_set('maintenance', 'installing spark')
    spark_master_host = subprocess.check_output(['facter', 'fqdn']).strip().decode()
    bigtop = Bigtop()
    # There is a race condition here  
    # bigtop.install(hosts={'spark': spark_master_host}, roles="['spark-worker','spark-master']")
    # fails to bring up the worker
    # TODO(kjackal): Investigate why
    #bigtop.install(hosts={'spark': spark_master_host}, roles='spark-master')
    #bigtop.install(hosts={'spark': spark_master_host}, roles='spark-worker')
    #bigtop.install(hosts={'spark': spark_master_host}, roles='spark-on-yarn')
    #bigtop.install(hosts={'spark': spark_master_host}, roles='spark-history-server')
    #bigtop.install(hosts={'spark': spark_master_host}, roles='spark-client')
    hiera_params={
        'bigtop::roles_enabled': False,
        'hadoop::common_hdfs::hadoop_namenode_host': spark_master_host,
        'hadoop::common_yarn::hadoop_ps_host': spark_master_host,
        'hadoop::common_yarn::hadoop_rm_host': spark_master_host,
        'hadoop::common_mapred_app::jobtracker_host': spark_master_host,
        'hadoop::common_mapred_app::mapreduce_jobhistory_host': spark_master_host,
        'hadoop_cluster_node::cluster_components': ['hadoop', 'spark'],
        'spark::common::master_host': spark_master_host,
        'hadoop::hadoop_storage_dirs': ['/data/1', '/data/2'],
        'bigtop::hadoop_head_node': spark_master_host,
    }
    bigtop.install(hosts={}, hiera_params=hiera_params)
    # Of course we need to run this twice....
    bigtop.install(hosts={}, hiera_params=hiera_params)
    hookenv.status_set('active', 'ready')


@when_not('hadoop.joined')
def no_hadoop():
    remove_state('spark.installed')
    
