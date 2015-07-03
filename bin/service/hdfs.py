#!/usr/bin/python
#coding=utf-8
import os
import sys
from core import ecs, utils
from core.common import GlobalVar

def setup_hdfs(masters, slaves, opts):
    print "==> Updating Hadoop configuration for each ECS instance..."
    # copy default hadoop config
    os.system(" /bin/cp -r %s/hadoop/etc/hadoop/* %s/etc/hadoop/"
              % (GlobalVar.DEFAULT_CONF_DIR, GlobalVar.HADOOP_INSTALL_DIR))

    master_intranet_ip = ecs.get_instance_info(masters[0])['InnerIpAddress']['IpAddress'][0]
    namenode = "hdfs://%s:9000" % master_intranet_ip
    utils.update_hadoop_configuration(namenode)
    utils.do_scp(masters[0], opts, GlobalVar.HADOOP_CONF_DIR, "%s/etc/" % GlobalVar.HADOOP_INSTALL_DIR)
    for slave in slaves:
        utils.do_scp(slave, opts, GlobalVar.HADOOP_CONF_DIR, "%s/etc/" % GlobalVar.HADOOP_INSTALL_DIR)

    print "==> Starting HDFS service..."
    start_hdfs(masters[0], slaves, opts)
    print "==> Started HDFS service successfully"

def start_hdfs(master, slaves, opts):
    utils.warning()
    msg = "If this is the first time, you need to format HDFS, otherwise you should not format it! \n" \
          "Format HDFS (Y/n): "
    confirm = raw_input(msg)
    if confirm == 'Y':
        msg = "Confirm to format HDFS? (Y/n): "
        confirm_again = raw_input(msg)
        if confirm_again == "Y":
            print "==> Formatting HDFS..."
            format_hdfs = "%s/bin/hdfs namenode -format -force 2> /dev/null" % GlobalVar.HADOOP_INSTALL_DIR
            utils.do_ssh(master, opts, str(format_hdfs))
        else:
            print "==> Not `Y`, skipping formatting HDFS..."
    else:
        print "==> Not `Y`, skipping formatting HDFS..."

    print "==> Starting namenode..."
    start_namenode = "%s/sbin/hadoop-daemon.sh --config %s --script hdfs start namenode" \
                     % (GlobalVar.HADOOP_INSTALL_DIR, GlobalVar.HADOOP_CONF_DIR)
    utils.do_ssh(master, opts, start_namenode)

    print "==> Starting datanode..."
    for slave in slaves:
        start_datanode = "%s/sbin/hadoop-daemon.sh --config %s --script hdfs start datanode" \
                         % (GlobalVar.HADOOP_INSTALL_DIR, GlobalVar.HADOOP_CONF_DIR)
        utils.do_ssh(slave, opts, start_datanode)

def stop_hdfs(masters, slaves, opts):
    print "==> Stopping namenode..."
    master = masters[0]
    stop_namenode = "%s/sbin/hadoop-daemon.sh --config %s --script hdfs stop namenode" \
                    % (GlobalVar.HADOOP_INSTALL_DIR, GlobalVar.HADOOP_CONF_DIR)
    utils.do_ssh(master, opts, stop_namenode)

    print "==> Stopping datanodes..."
    for slave in slaves:
        stop_datanode = "%s/sbin/hadoop-daemon.sh --config %s --script hdfs stop datanode" \
                        % (GlobalVar.HADOOP_INSTALL_DIR, GlobalVar.HADOOP_CONF_DIR)
        utils.do_ssh(slave, opts, stop_datanode)
    print "==> Stopped HDFS service successfully"
