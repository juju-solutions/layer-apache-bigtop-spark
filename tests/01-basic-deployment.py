#!/usr/bin/env python3

import unittest
import amulet


class TestDeploy(unittest.TestCase):
    """
    Trivial deployment test for Apache Spark.
    """
    def setUp(self):
        self.d = amulet.Deployment(series='trusty')
        self.d.add('spark', 'apache-bigtop-spark')
        self.d.setup(timeout=900)
        self.d.sentry.wait(timeout=1800)

    def test_deploy(self):
        self.d.sentry.wait_for_messages({"spark": "Waiting for a relation to HDFS"})


if __name__ == '__main__':
    unittest.main()
