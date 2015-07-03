#!/usr/bin/python
#coding=utf-8
import os
import sys
from core import ecs, utils
from core.common import GlobalVar

def start_spark_notebook(masters, opts):
    print "==> Starting Spark Notebook service..."
    master = masters[0]
    ins = ecs.get_instance_info(master)
    ip = ins['InnerIpAddress']['IpAddress'][0]
    launch_notebook = ' \" cd %s; nohup ./bin/spark-notebook -Dhttp.port=9090 > /dev/null 2>&1 & \" ' \
                      % GlobalVar.SPARK_NOTEBOOK_INSTALL_DIR
    os.system("sshpass -p %s ssh %s %s@%s %s" % (opts.pwd, " ".join(utils.ssh_args()), opts.user, ip, launch_notebook))
    print "==> Started Spark Notebook service successfully..."

def stop_spark_notebook(masters, opts):
    print "==> Stopping Spark Notebook..."
    master = masters[0]
    ins = ecs.get_instance_info(master)
    ip = ins['InnerIpAddress']['IpAddress'][0]
    stop_notebook = ' \" cd %s; cat RUNNING_PID | xargs -r kill -9; rm -f RUNNING_PID \" ' \
                    % GlobalVar.SPARK_NOTEBOOK_INSTALL_DIR
    os.system("sshpass -p %s ssh %s %s@%s %s" % (opts.pwd, " ".join(utils.ssh_args()), opts.user, ip, stop_notebook))
    print "==> Stopped Spark Notebook service successfully..."
