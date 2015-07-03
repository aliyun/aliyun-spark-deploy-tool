#!/usr/bin/python
#coding=utf-8
import sys
import os
import getpass
from service import hdfs, hue, spark, spark_notebook
from core import utils, ecs
from core.common import GlobalVar
from sys import stderr
from optparse import OptionParser

utils.welcome()

class UsageError(Exception):
    pass

def parse_args():
    parser = OptionParser(
        prog="spark-ecs",
        usage="%prog [options] <action> <cluster_name>[:<module_name>]\n\n"
              + "<action> can be: launch, destroy, stop, start, enable, disable \n"
              + "<cluster_name> can be anything you want \n"
              + "<module_name> can be: hdfs, hue, spark-notebook")
    parser.add_option(
        "-m", '--mode', type="string",
        help="There are two modes, i.e. `client` and `cluster`. " +
             "In `client` mode, you need to buy ECS instances firstly, and then provide `masters` file listing " +
             "Spark master `InstanceId` and `slaves` listing Spark slave `InstanceId`. In `cluster` mode, you " +
             "can create ECS instances and start Spark cluster through this script.")
    parser.add_option(
        "-p", '--pwd', type="string", help="User password for each ECS instance.")
    parser.add_option(
        "-s", "--slaves", type="int", default=1, help="Number of slaves to launch (default: %default)")
    parser.add_option(
        "-d", "--disk-size", type="int", help="Size (in GB) of each ECS data disk")
    parser.add_option(
        "--ibo", type="string", default="2", help="Internet bandwidth out")
    parser.add_option(
        "-t", "--instance-type", type="string", help="Type of instance to launch.")
    parser.add_option(
        "-r", "--region", type="string", help="ECS region to launch instances in")
    parser.add_option(
        "-z", "--zone", type="string",
        help="Availability zone to launch instances in, or 'all' to spread " +
             "slaves across multiple (an additional RMB 0.8/Gb for bandwidth" +
             "between zones applies) (default: a single zone chosen at random)")
    parser.add_option("-i", "--ami", help="Aliyun Machine Image ID to use")
    parser.add_option(
        "-u", "--user", default="root",
        help="The SSH user you want to connect as (default: %default)")
    parser.add_option(
        "--authorized-address", type="string", default="0.0.0.0/0",
        help="Address to authorize on created security groups (default: %default)")
    parser.add_option(
        "--include-gateway", action="store_true", default=False,
        help="Whether to put current login machine into Spark Cluster."
    )
    parser.add_option(
        "--enable-slave-public-ip", action="store_true", default=False,
        help="Whether to allocate a public network IP for Spark master."
    )
    parser.add_option(
        "--enable-hdfs", action="store_true", default=False,
        help="Whether to launch a HDFS service"
    )
    parser.add_option(
        "--enable-spark-notebook", action="store_true", default=False,
        help="Launch a spark-notebook. More information: https://github.com/andypetrella/spark-notebook"
    )
    parser.add_option(
        "--enable-hue", action="store_true", default=False,
        help="Launch a Hue web Service"
    )

    (opts, command) = parser.parse_args()
    if len(command) != 2:
        parser.print_help()
        print "\nYou need to provide a <cluster_name>[:<module_name>]\n"
        sys.exit(1)
    (action, name) = command
    if action in ["launch", "stop", "start", "destroy"]:
        GlobalVar.CLUSTER_HOSTS = name + "-hosts"

    return opts, action, name

def launch_in_cluster_mode(cluster_name, opts):
    # check cluster status trickly
    if utils.check_cluster_status(cluster_name, ['Running', 'Stopped']):
        print "Cluster %s has been launched, please `Destroy` it first." % cluster_name
        sys.exit(1)
    do_validity_check(opts)

    if opts.slaves <= 0:
        print >> stderr, "ERROR: You have to start as least 1 slave"
        sys.exit(1)
    (masters, slaves, master_ip) = utils.launch_cluster(opts, cluster_name)
    utils.wait_for_cluster_state(
        cluster_state=['Running'],
        instances=masters + slaves)
    utils.mount_disk(masters, slaves, opts)
    spark.setup_cluster(masters, slaves, opts, True)
    if opts.enable_spark_notebook:
        spark_notebook.start_spark_notebook(masters, opts)
    if opts.enable_hue:
        hue.start_hue(masters, opts)
    if opts.enable_hdfs:
        hdfs.setup_hdfs(masters, slaves, opts)
    if opts.enable_slave_public_ip:
        utils.save_public_ips(masters, slaves)
    utils.open_nginx(opts, masters)

    utils.end_of_startup(opts, master_ip, masters)
    # update cluster status
    os.system("echo Running > %s%s" % (GlobalVar.CLUSTER_STATUS, cluster_name))

def destroy_in_cluster_mode(cluster_name, opts):
    do_validity_check(opts)
    print "Are you sure you want to destroy the cluster %s?" % cluster_name
    print "The following instances will be terminated:"
    (masters, slaves) = utils.get_masters_and_slaves(opts.mode, cluster_name)
    if len(masters + slaves) <= 0:
        print "There is no master or slave, check it first please."
        sys.exit(1)
    instances = masters + slaves
    gateway = ecs.get_gateway_instance_info(opts)['InstanceId']
    if gateway in instances:
        instances.remove(gateway)

    to_release = []
    for ins in instances:
        try:
            instance_info = ecs.get_instance_info(ins)
            to_release.append(ins)
            print "> %s" % (instance_info['HostName'])
        except Exception, e:
            if 'InvalidInstanceId.NotFound' in e.args:
                print "> %s, invalid `InstanceId` not found, skip it." % ins
            else:
                raise e

    utils.warning()
    msg = "All data on all nodes will be lost!!\nYou'd better stop it first. " \
          "Destroy cluster %s (Y/n): " % cluster_name
    to_destroy = raw_input(msg)
    if to_destroy == "Y":
        try:
            ecs.release_ecs_instance(to_release)
        except Exception, e:
            print e, "\nReleasing ECS instances failed for some unknown reasons, " \
                  "you can do it through: https://console.aliyun.com/ecs/index.htm"
            raise e
        finally:
            utils.delete_file_safely(GlobalVar.CLUSTER_STATUS + cluster_name)
            utils.delete_file_safely(GlobalVar.CLUSTER_INSTANCES + cluster_name)
            utils.delete_file_safely(GlobalVar.SPARK_ECS_DIR + "/" + GlobalVar.CLUSTER_HOSTS)
            utils.delete_file_safely(GlobalVar.SPARK_ECS_DIR + "/" + GlobalVar.CLUSTER_HOSTS + "-public")
    else:
        print "Not `Y`, give up destroying cluster %s" % cluster_name

def stop_in_cluster_mode(cluster_name, opts):
    # check cluster status trickly
    if utils.check_cluster_status(cluster_name, ['Stopped']):
        print "Cluster %s has been `Stopped`, you can not stop it again." % cluster_name
        sys.exit(1)
    do_validity_check(opts)

    (masters, slaves) = utils.get_masters_and_slaves(opts.mode, cluster_name)
    if len(masters + slaves) <= 0:
        print "There is no master or slave running, check it first please."
        sys.exit(1)

    print "==> Stopping Spark cluster..."
    utils.warning()
    msg = "Stopping Spark cluster will stop HDFS, spark-notebook and Hue at the same time. " \
          "Stop it? (Y/n): "
    to_stop = raw_input(msg)
    if to_stop == "Y":
        if opts.pwd == "":
            opts.pwd = getpass.getpass("You need to provide the password for ECS instance:")
        spark.stop_spark_cluster(masters, slaves, opts)
        hdfs.stop_hdfs(masters, slaves, opts)
        hue.stop_hue(masters, opts)
        spark_notebook.stop_spark_notebook(masters, opts)
        utils.stop_nginx(opts,masters)
        # update cluster status
        os.system("echo Stopped > %s%s" % (GlobalVar.CLUSTER_STATUS, cluster_name))
    else:
        print "Not `Y`, give up stopping cluster %s" % cluster_name

def start_in_cluster_mode(cluster_name, opts):
    # check cluster status trickly
    if utils.check_cluster_status(cluster_name, ['Running']):
        print "Cluster %s is `Running`, please `Stop` it first." % cluster_name
        sys.exit(1)
    do_validity_check(opts)

    (masters, slaves) = utils.get_masters_and_slaves(opts.mode, cluster_name)
    if len(masters + slaves) <= 0:
        print "There is no master or slave, check it first please."
        sys.exit(1)

    print "==> Restarting spark cluster..."
    if opts.pwd == "":
        opts.pwd = getpass.getpass("You need to provide the password for ECS instance:")
    master_ip = ecs.get_instance_info(masters[0])['PublicIpAddress']['IpAddress'][0]
    spark.start_spark_cluster(masters[0], slaves, opts)
    if opts.enable_spark_notebook:
        spark_notebook.start_spark_notebook(masters, opts)
    if opts.enable_hue:
        hue.start_hue(masters, opts)
    if opts.enable_hdfs:
        hdfs.setup_hdfs(masters, slaves, opts)
    if opts.enable_slave_public_ip:
        utils.save_public_ips(masters, slaves)
    utils.open_nginx(opts, masters)

    utils.end_of_startup(opts, master_ip, masters)
    # update cluster status
    os.system("echo Running > %s%s" % (GlobalVar.CLUSTER_STATUS, cluster_name))

def launch_in_client_mode(cluster_name, opts):
    # check cluster status trickly
    if utils.check_cluster_status(cluster_name, ['Running', 'Stopped']):
        print "Cluster %s has been launched, please `Destroy` it first." % cluster_name
        sys.exit(1)
    do_validity_check(opts)

    (masters, slaves) = utils.get_masters_and_slaves(opts.mode)
    if len(masters) <= 0:
        print >> stderr, "ERROR: You have to start as least 1 master"
        sys.exit(1)
    if len(slaves) <= 0:
        print >> stderr, "ERROR: You have to start as least 1 slave"
        sys.exit(1)

    # Now we only support single-node master.
    spark.setup_cluster(masters, slaves, opts, True)
    if opts.enable_spark_notebook:
        spark_notebook.start_spark_notebook(masters, opts)
    if opts.enable_hue:
        hue.start_hue(masters, opts)
    if opts.enable_hdfs:
        hdfs.setup_hdfs(masters, slaves, opts)
    if opts.enable_slave_public_ip:
        utils.save_public_ips(masters, slaves)
    master_ip = ecs.get_instance_info(masters[0])['PublicIpAddress']['IpAddress'][0]

    utils.open_nginx(opts, masters)
    utils.end_of_startup(opts, master_ip, masters)
    # update cluster status
    os.system("echo Running > %s%s" % (GlobalVar.CLUSTER_STATUS, cluster_name))

def destroy_in_client_mode(cluster_name, opts):
    do_validity_check(opts)
    (masters, slaves) = utils.get_masters_and_slaves(opts.mode)
    if len(masters + slaves) <= 0:
        print "There is no master or slave, check it first please."
        sys.exit(1)

    print "Are you sure you want to destroy the cluster %s?" % cluster_name
    print "The following instances will be terminated:"
    instances = masters + slaves
    gateway = ecs.get_gateway_instance_info(opts)['InstanceId']
    if gateway in instances:
        instances.remove(gateway)
    to_release = []
    for ins in instances:
        try:
            instance_info = ecs.get_instance_info(ins)
            to_release.append(ins)
            print "> %s" % (instance_info['HostName'])
        except Exception, e:
            if 'InvalidInstanceId.NotFound' in e.args:
                print "> %s, invalid `InstanceId` not found, skip it." % ins
            else:
                raise e

    utils.warning()
    msg = "All data on all nodes will be lost!!\nYou'd better stop it first. " \
          "Destroy cluster %s (Y/n): " % cluster_name
    to_destroy = raw_input(msg)
    if to_destroy == "Y":
        try:
            ecs.release_ecs_instance(to_release)
        except Exception, e:
            print e, "Releasing ECS instances failed for some unknown reasons, " \
                  "you can do it through: https://console.aliyun.com/ecs/index.htm"
            raise e
        finally:
            utils.delete_file_safely(GlobalVar.CLUSTER_STATUS + cluster_name)
            utils.delete_file_safely(GlobalVar.CLUSTER_INSTANCES + cluster_name)
            utils.delete_file_safely(GlobalVar.SPARK_ECS_DIR + "/" + GlobalVar.CLUSTER_HOSTS)
            utils.delete_file_safely(GlobalVar.SPARK_ECS_DIR + "/" + GlobalVar.CLUSTER_HOSTS + "-public")
    else:
        print "Not `Y`, give up destroying cluster %s" % cluster_name
        sys.exit(1)

def stop_in_client_mode(cluster_name, opts):
    # check cluster status trickly
    if utils.check_cluster_status(cluster_name, ['Stopped']):
        print "Cluster %s has been `Stopped`, you can not stop it again." % cluster_name
        sys.exit(1)
    do_validity_check(opts)

    (masters, slaves) = utils.get_masters_and_slaves(opts.mode)
    if len(masters + slaves) <= 0:
        print "There is no master or slave running, check it first please."
        sys.exit(1)

    print "==> Stopping spark cluster..."
    utils.warning()
    msg = "Stopping Spark cluster will stop HDFS, spark-notebook and Hue at the same time. " \
          "Stop %s? (Y/n): " % cluster_name
    to_stop = raw_input(msg)
    if to_stop == "Y":
        if opts.pwd == "":
            opts.pwd = getpass.getpass("You need to provide the password for ECS instance:")
        spark.stop_spark_cluster(masters, slaves, opts)
        hdfs.stop_hdfs(masters, slaves, opts)
        hue.stop_hue(masters, opts)
        spark_notebook.stop_spark_notebook(masters, opts)
        utils.stop_nginx(opts,masters)
        # update cluster status
        os.system("echo Stopped > %s%s" % (GlobalVar.CLUSTER_STATUS, cluster_name))
    else:
        print "Not `Y`, give up stopping cluster %s" % cluster_name

def start_in_client_mode(cluster_name, opts):
    # check cluster status trickly
    if utils.check_cluster_status(cluster_name, ['Running']):
        print "Cluster %s is `Running`, please `Stop` it first." % cluster_name
        sys.exit(1)
    do_validity_check(opts)

    (masters, slaves) = utils.get_masters_and_slaves(opts.mode)
    if len(masters + slaves) <= 0:
        print "There is no master or slave, check it first please."
        sys.exit(1)

    print "==> Restarting spark cluster..."
    if opts.pwd == "":
        opts.pwd = getpass.getpass("You need to provide the password for ECS instance:")
    spark.start_spark_cluster(masters[0], slaves, opts)
    if opts.enable_spark_notebook:
        spark_notebook.start_spark_notebook(masters, opts)
    if opts.enable_hue:
        hue.start_hue(masters, opts)
    if opts.enable_hdfs:
        hdfs.setup_hdfs(masters, slaves, opts)
    if opts.enable_slave_public_ip:
        utils.save_public_ips(masters, slaves)
    master_ip = ecs.get_instance_info(masters[0])['PublicIpAddress']['IpAddress'][0]
    utils.open_nginx(opts, masters)
    utils.end_of_startup(opts, master_ip, masters)
    # update cluster status
    os.system("echo Running > %s%s" % (GlobalVar.CLUSTER_STATUS, cluster_name))

def enable_module(name, opts):
    if len(name.split(":")) != 2:
        print "\nYou need to provide a <cluster_name>:<module_name>\n"
        sys.exit(1)
    cluster_name = name.split(":")[0]
    module_name = name.split(":")[1]
    do_validity_check(opts)
    (masters, slaves) = utils.get_masters_and_slaves(opts.mode, cluster_name)
    if module_name == "hdfs":
        hdfs.setup_hdfs(masters, slaves, opts)
    elif module_name == "hue":
        hue.start_hue(masters, opts)
    elif module_name == "spark-notebook":
        spark_notebook.start_spark_notebook(masters, opts)
    else:
        print "Now we only support 3 module: hdfs, hue, spark-notebook"
        sys.exit(1)

def disable_module(name, opts):
    if len(name.split(":")) != 2:
        print "\nYou need to provide a <cluster_name>:<module_name>\n"
        sys.exit(1)
    cluster_name = name.split(":")[0]
    module_name = name.split(":")[1]
    do_validity_check(opts)
    (masters, slaves) = utils.get_masters_and_slaves(opts.mode, cluster_name)
    if module_name == "hdfs":
        hdfs.stop_hdfs(masters, slaves, opts)
    elif module_name == "hue":
        hue.stop_hue(masters, opts)
    elif module_name == "spark-notebook":
        spark_notebook.stop_spark_notebook(masters, opts)
    else:
        print "Now we only support 3 module: hdfs, hue, spark-notebook"
        sys.exit(1)

def do_validity_check(opts):
    if opts.region is None:
        length = len(GlobalVar.ECS_REGION)
        print "There are %s regions available, listed as following:\n" % length
        for id in range(1, length + 1):
            print id, ":", GlobalVar.ECS_REGION["%s" % id]
        print
        msg = "Please specify the ECS region No. (like 1): "
        opts.region = GlobalVar.ECS_REGION[raw_input(msg).strip()]

    if opts.pwd is None:
        opts.pwd = getpass.getpass("""You need to provide a password for ECS instance.
If `CLIENT` mode, you just need to provide login machine's password.
If `CLUSTER` mode and `--include-gateway`, you just need to provide login machine's password.
If `CLUSTER` mode only, you need to set a new default password for each ECS instance.
Please set a password:""")

def real_main():
    (opts, action, name) = parse_args()
    utils.setup_sshpass()
    utils.read_properties()

    if opts.mode is None:
        msg = "Please specify the running mode, client/cluster: "
        opts.mode = raw_input(msg).strip()

    try:
        if action == "launch" and opts.mode == "cluster":
            launch_in_cluster_mode(name, opts)
        elif action == "destroy" and opts.mode == "cluster":
            destroy_in_cluster_mode(name, opts)
        elif action == "stop" and opts.mode == "cluster":
            stop_in_cluster_mode(name, opts)
        elif action == "start" and opts.mode == "cluster":
            start_in_cluster_mode(name, opts)
        elif action == "launch" and opts.mode == "client":
            launch_in_client_mode(name, opts)
        elif action == "destroy" and opts.mode == "client":
            destroy_in_client_mode(name, opts)
        elif action == "stop" and opts.mode == "client":
            stop_in_client_mode(name, opts)
        elif action == "start" and opts.mode == "client":
            start_in_client_mode(name, opts)
        elif action == "enable":
            enable_module(name, opts)
        elif action == "disable":
            disable_module(name, opts)
        else:
            print "Wrong action or mode or module. We support: \n " \
                  "6 actions: launch, stop, start, destroy, enable, disable \n " \
                  "2 modes: client and cluster \n " \
                  "3 modules: hdfs, hue, spark-notebook"
    except RuntimeError as e:
        utils.do_rollback()

def main():
    try:
        GlobalVar.SPARK_ECS_DIR = os.path.dirname(os.path.realpath(__file__))
        real_main()
    except UsageError, e:
        print >> stderr, "\nERROR:\n",
        sys.exit(1)

if __name__ == "__main__":
    main()

