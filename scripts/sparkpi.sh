#!/bin/bash
set -eu

echo "Running SparkPi"
spark-submit --class org.apache.spark.examples.SparkPi /usr/lib/spark/lib/spark-examples-*.jar 10
echo ""
