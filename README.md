## Overview

### Spark Cluster
Apache Spark™ is a fast and general purpose engine for large-scale data
processing. Key features:

 * **Speed**

 Run programs up to 100x faster than Hadoop MapReduce in memory, or 10x faster
 on disk. Spark has an advanced DAG execution engine that supports cyclic data
 flow and in-memory computing.

 * **Ease of Use**

 Write applications quickly in Java, Scala or Python. Spark offers over 80
 high-level operators that make it easy to build parallel apps, and you can use
 it interactively from the Scala and Python shells.

 * **General Purpose Engine**

 Combine SQL, streaming, and complex analytics. Spark powers a stack of
 high-level tools including Shark for SQL, MLlib for machine learning, GraphX,
 and Spark Streaming. You can combine these frameworks seamlessly in the same
 application.


## Deployment

This charm allows the deployment of Apache Spark backaged y Bigtop
in the modes described below:

 * **Standalone**

 In this mode Spark units form a cluster that you can scale to match your needs.
 Starting with a single node:
    
    juju deploy apache-bigtop-namenode namenode
    juju deploy apache-bigtop-slave slave
    juju deploy apache-bigtop-plugin plugin
    juju deploy apache-bigtop-spark spark
    juju add-relation slave namenode
    juju add-relation namenode plugin
    juju add-relation spark plugin

 You can scale the cluster by adding more spark units:

    juju add-unit spark

 When in standalone mode Juju ensures a single Spark master is appointed.
 The status of the unit acting as master reads "Ready (standalone - master)",
 while the rest of the units display a status of  "Ready (standalone)".
 In case you remove the master unit Juju will appoint a new master to the cluster.
 However, should a master fail in this standalone mode the cluster will stop functioning
 properly. Master node failures is handled properly when Apache spark is setup in
 High Availability mode (Standalone HA).

 * **Yarn-client and Yarn-cluster**

 This charm leverages our pluggable Hadoop model with the `hadoop-plugin`
 interface. This means that you can relate this charm to a base Apache Hadoop cluster
 to run Spark jobs there. The suggested deployment method is to use the
 [apache-hadoop-spark](https://jujucharms.com/apache-hadoop-spark/)
 bundle. This will deploy the Apache Hadoop platform with a single Apache Spark
 unit that communicates with the cluster by relating to the
 `apache-hadoop-plugin` subordinate charm:

    juju-quickstart apache-hadoop-spark


Note: To transition among execution modes you need to set the
`spark_execution_mode` config variable:

    juju set spark spark_execution_mode=<new_mode>

## Usage

Once deployment is complete, you can manually load and run Spark batch or
streaming jobs in a variety of ways:

  * **Spark shell**

Spark’s shell provides a simple way to learn the API, as well as a powerful
tool to analyse data interactively. It is available in either Scala or Python
and can be run from the Spark unit as follows:

       juju ssh spark/0
       spark-shell # for interaction using scala
       pyspark     # for interaction using python

  * **Command line**

SSH to the Spark unit and manually run a spark-submit job, for example:

       juju ssh spark/0
       spark-submit --class org.apache.spark.examples.SparkPi \
        --master yarn-client /usr/lib/spark/lib/spark-examples*.jar 10

  * **Apache Zeppelin visual service**

Deploy Apache Zeppelin and relate it to the Spark unit:

    juju deploy apache-zeppelin zeppelin
    juju add-relation spark zeppelin

Once the relation has been made, access the web interface at
`http://{spark_unit_ip_address}:9090`

  * **IPyNotebook for Spark**

The IPython Notebook is an interactive computational environment, in which you
can combine code execution, rich text, mathematics, plots and rich media.
Deploy IPython Notebook for Spark and relate it to the Spark unit:

    juju deploy apache-spark-notebook notebook
    juju add-relation spark notebook

Once the relation has been made, access the web interface at
`http://{spark_unit_ip_address}:8880`


## Upgrading Spark Charm

To upgrade the charm is a multi step process.
First you will need to upgrade the charm by issuing:

    juju upgrade-charm spark

This will fetch any available upgrades. You can query for the available versions via:

    juju action do spark/0 list-spark-versions

Next you need to enter the maintenance modes
where spark is sitting idle for the upgrade to start:

    juju set spark maintenance_mode=true

Set the target spark version (any new units added will be using that spark version):

    juju set spark spark_version=<new_version>

The upgrade process will start immediately. If you would like to trigger the upgrade process
manually per spark unit you should make sure you have set the `upgrade_immediately`
flag to false.

    juju set spark upgrade_immediately=false

And then you can call the action:

    juju action do spark/0 upgrade-spark

Finally at the end of the upgrade you should exit the maintenance mode:

    juju set spark maintenance_mode=false


## Configuration

### `driver_memory`

Amount of memory Spark will request for the Master. Specify gigabytes (e.g.
1g) or megabytes (e.g. 1024m). If running in `local` or `standalone` mode, you
may also specify a percentage of total system memory (e.g. 50%).

### `executor_memory`

Amount of memory Spark will request for each executor. Specify gigabytes (e.g.
1g) or megabytes (e.g. 1024m). If running in `local` or `standalone` mode, you
may also specify a percentage of total system memory (e.g. 50%). Take care
when specifying percentages in local modes, as this value is for *each*
executor. Your Spark job will fail if, for example, you set this value > 50%
and attempt to run 2 or more executors.

### `spark_bench_enabled`

Install the SparkBench benchmarking suite. If `true` (the default), this charm
will download spark bench from the URL specified by `spark_bench_ppc64le`
or `spark_bench_x86_64`, depending on the unit's architecture.

### `spark_execution_mode`

Spark has four modes of execution: local, standalone, yarn-client, and
yarn-cluster. The default mode is `yarn-client` and can be changed by setting
the `spark_execution_mode` config variable.

  * **Local**

    In Local mode, Spark processes jobs locally without any cluster resources.
    There are 3 ways to specify 'local' mode:

    * `local`

      Run Spark locally with one worker thread (i.e. no parallelism at all).

    * `local[K]`

      Run Spark locally with K worker threads (ideally, set this to the number
      of cores on your machine).

    * `local[*]`

      Run Spark locally with as many worker threads as logical cores on your
      machine.

  * **Standalone**

    In `standalone` mode, Spark launches a Master and Worker daemon on the Spark
    unit. This mode is useful for simulating a distributed cluster environment
    without actually setting up a cluster.

  * **YARN-client**

    In `yarn-client` mode, the driver runs in the client process, and the
    application master is only used for requesting resources from YARN.

  * **YARN-cluster**

    In `yarn-cluster` mode, the Spark driver runs inside an application master
    process which is managed by YARN on the cluster, and the client can go away
    after initiating the application.


## Verify the deployment

### Status and Smoke Test

The services provide extended status reporting to indicate when they are ready:

    juju status --format=tabular

This is particularly useful when combined with `watch` to track the on-going
progress of the deployment:

    watch -n 0.5 juju status --format=tabular

The message for each unit will provide information about that unit's state.
Once they all indicate that they are ready, you can perform a "smoke test"
to verify that Spark is working as expected using the built-in `smoke-test`
action:

    juju action do spark/0 smoke-test

After a few seconds or so, you can check the results of the smoke test:

    juju action status

You will see `status: completed` if the smoke test was successful, or
`status: failed` if it was not.  You can get more information on why it failed
via:

    juju action fetch <action-id>


### Verify Job History

The Job History server shows all active and finished spark jobs submitted.
To view the Job History server you need to expose spark (`juju expose spark`)
and navigate to `http://{spark_master_unit_ip_address}:18080` of the
unit acting as master.


## Benchmarking

This charm provides several benchmarks, including the
[Spark Bench](https://github.com/SparkTC/spark-bench) benchmarking
suite (if enabled), to gauge the performance of your environment.

The easiest way to run the benchmarks on this service is to relate it to the
[Benchmark GUI][].  You will likely also want to relate it to the
[Benchmark Collector][] to have machine-level information collected during the
benchmark, for a more complete picture of how the machine performed.

[Benchmark GUI]: https://jujucharms.com/benchmark-gui/
[Benchmark Collector]: https://jujucharms.com/benchmark-collector/

However, each benchmark is also an action that can be called manually:

    $ juju action do spark/0 pagerank
    Action queued with id: 88de9367-45a8-4a4b-835b-7660f467a45e
    $ juju action fetch --wait 0 88de9367-45a8-4a4b-835b-7660f467a45e
    results:
      meta:
        composite:
          direction: asc
          units: secs
          value: "77.939000"
        raw: |
          PageRank,2015-12-10-23:41:57,77.939000,71.888079,.922363,0,PageRank-MLlibConfig,,,,,10,12,,200000,4.0,1.3,0.15
        start: 2015-12-10T23:41:34Z
        stop: 2015-12-10T23:43:16Z
      results:
        duration:
          direction: asc
          units: secs
          value: "77.939000"
        throughput:
          direction: desc
          units: x/sec
          value: ".922363"
    status: completed
    timing:
      completed: 2015-12-10 23:43:59 +0000 UTC
      enqueued: 2015-12-10 23:42:10 +0000 UTC
      started: 2015-12-10 23:42:15 +0000 UTC

Valid action names at this time are:

  * logisticregression
  * matrixfactorization
  * pagerank
  * sql
  * streaming
  * svdplusplus
  * svm
  * trianglecount
  * sparkpi


## Contact Information

- <bigdata@lists.ubuntu.com>


## Help

- [Juju mailing list](https://lists.ubuntu.com/mailman/listinfo/juju)
- [Juju community](https://jujucharms.com/community)
