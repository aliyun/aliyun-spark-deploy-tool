#!/usr/bin/python
#coding=utf-8
import os
import sys

class GlobalVar:

    DEFAULT_CONF_DIR = "/root/.config"
    PROPERTY_FILE = "%s/packages.property" % DEFAULT_CONF_DIR
    HADOOP_INSTALL_DIR = "/opt/hadoop"
    HADOOP_CONF_DIR = "%s/etc/hadoop" % HADOOP_INSTALL_DIR
    SPARK_INSTALL_DIR = "/opt/spark"
    SPARK_CONF_DIR = "%s/conf" % SPARK_INSTALL_DIR
    SPARK_NOTEBOOK_INSTALL_DIR = "/opt/spark-notebook"
    HUE_INSTALL_DIR = "/opt/hue"
    ALIYUN_SDK_URL = "http://docs-aliyun-com-cn-b.oss-cn-hangzhou.aliyuncs.com/ecs/assets/sdk/python_sdk.tgz"
    SPARK_ECS_DIR = ""
    CLUSTER_STATUS = "%s/status/cluster-" % DEFAULT_CONF_DIR
    CLUSTER_INSTANCES = "%s/instances/" % DEFAULT_CONF_DIR
    CLUSTER_HOSTS = ""

    ECS_API_PAGESIZE = 50

    ECS_INSTANCE_TYPE = {
        "ecs.t1.small": (1, 1),
        "ecs.s1.small": (1, 2),
        "ecs.s1.medium": (1, 4),
        "ecs.s2.small": (2, 2),
        "ecs.s2.large": (2, 4),
        "ecs.s2.xlarge": (2, 8),
        "ecs.s3.medium": (4, 4),
        "ecs.s3.large": (4, 8),
        "ecs.m1.medium": (4, 16)
    }

    ECS_REGION = {
        "1": "cn-hangzhou",
        "2": "cn-shenzhen",
        "3": "cn-beijing",
        "4": "cn-qingdao"
    }

    SPARK_IMAGES = {
        ("Spark-1.3.1", "cn-hangzhou"): "m-23xecoatf",
        ("Spark-1.3.1", "cn-shenzhen"): "m-94ksoicp4",
        ("Spark-1.3.1", "cn-beijing"):  "m-25dt21m47",
        ("Spark-1.3.1", "cn-qingdao"):  "m-28w0wqwa6"
    }

    AVAILABLE_SAPRK_VERSION = {
        "1": "Spark-1.3.1"
    }
