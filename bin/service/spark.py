#!/usr/bin/python
#coding=utf-8
import sys
import os
from core import ecs, utils
from core.common import GlobalVar

def setup_cluster(masters, slaves, opts, deploy_ssh_key):
    master = masters[0]
    if deploy_ssh_key:
        print "==> Generating cluster's SSH key on master..."
        key_setup = """
          [ -f ~/.ssh/id_rsa ] ||
            (ssh-keygen -q -t rsa -N '' -f ~/.ssh/id_rsa &&
             cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys)
        """
        utils.do_ssh(master, opts, key_setup)
        dot_ssh_tar = utils.ssh_read(master, opts, ['tar', 'c', '.ssh'])
        print "==> Transferring cluster's SSH key to slaves..."
        for slave in slaves:
            utils.ssh_write(slave, opts, ['tar', 'x'], dot_ssh_tar)

    print "==> Updating /etc/hosts for each ECS instance..."
    utils.prepare_hosts(master, slaves, opts)

    print "==> Updating Spark default configuration..."
    # copy default hadoop config
    os.system(" /bin/cp -r %s/spark/conf/* %s"
              % (GlobalVar.DEFAULT_CONF_DIR, GlobalVar.SPARK_CONF_DIR))
    utils.do_scp(masters[0], opts, GlobalVar.SPARK_CONF_DIR, GlobalVar.SPARK_INSTALL_DIR)
    for slave in slaves:
        utils.do_scp(slave, opts, GlobalVar.SPARK_CONF_DIR, GlobalVar.SPARK_INSTALL_DIR)

    print "==> Starting spark cluster..."
    start_spark_cluster(master, slaves, opts)

def start_spark_cluster(master, slaves, opts):
    ins = ecs.get_instance_info(master)
    master_name = ins['HostName']
    start_master = "%s/sbin/start-master.sh " % GlobalVar.SPARK_INSTALL_DIR
    utils.do_ssh(master, opts, str(start_master))
    for slave in slaves:
        instance_info = ecs.get_instance_info(slave)
        worker_name = instance_info['HostName']
        start_slave = "%s/sbin/start-slave.sh %s spark://%s:7077" \
                      % (GlobalVar.SPARK_INSTALL_DIR, worker_name, master_name)
        utils.do_ssh(slave, opts, str(start_slave))
    print "==> Started spark cluster successfully!"

def stop_spark_cluster(masters, slaves, opts):
    master = masters[0]
    stop_master = "%s/sbin/stop-master.sh " % GlobalVar.SPARK_INSTALL_DIR
    print "==> Stopping Spark Master..."
    utils.do_ssh(master, opts, str(stop_master))

    print "==> Stopping Spark Slaves..."
    for slave in slaves:
        instance_info = ecs.get_instance_info(slave)
        worker_name = instance_info['HostName']
        stop_slave = "%s/sbin/spark-daemon.sh stop org.apache.spark.deploy.worker.Worker %s" \
                     % (GlobalVar.SPARK_INSTALL_DIR, worker_name)
        utils.do_ssh(slave, opts, str(stop_slave))