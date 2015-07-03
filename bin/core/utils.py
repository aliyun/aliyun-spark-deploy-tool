#!/usr/bin/python
#coding=utf-8
import sys
import os
import shutil
import pipes
import getpass
import subprocess
import textwrap
import time
import ConfigParser
import ecs
from datetime import datetime
from sys import stderr
from xml.etree import ElementTree as ET
from nginx import start_nginx, do_stop_nginx
from common import GlobalVar

class UsageError(Exception):
    pass

def setup_sshpass():
    try:
        print "==> Checking sshpass installed or not..."
        subprocess.check_call(['sshpass', '-V'])
    except Exception:
        print "Begin to setup sshpass..."
        try:
            subprocess.check_call(['yum', '-y', 'install', 'sshpass'])
        except Exception:
            subprocess.check_call(['apt-get', '-y', 'install', 'sshpass'])

def read_properties():
    if os.path.exists(GlobalVar.PROPERTY_FILE):
        cf = ConfigParser.ConfigParser()
        cf.read(GlobalVar.PROPERTY_FILE)
        GlobalVar.SPARK_INSTALL_DIR = cf.get('path', 'spark')
        GlobalVar.SPARK_NOTEBOOK_INSTALL_DIR = cf.get('path', 'spark-notebook')
        GlobalVar.HUE_INSTALL_DIR = cf.get('path', 'hue')
        GlobalVar.HADOOP_INSTALL_DIR = cf.get('path', 'hadoop')
        GlobalVar.HADOOP_CONF_DIR = "%s/etc/hadoop" % GlobalVar.HADOOP_INSTALL_DIR

def save_masters_or_slaves(cluster_name, machine_type, instance_id):
    if instance_id is None:
        return
    dir = "%s/%s" % (GlobalVar.CLUSTER_INSTANCES, cluster_name)
    if not os.path.exists(dir):
        os.makedirs(dir)
    file = "%s/%s" % (dir, machine_type)
    if not os.path.exists(file):
        f = open(file, 'w')
        f.close()
    os.system("echo %s >> %s" % (str(instance_id), file))

def get_masters_and_slaves(mode, cluster_name=""):
    masters = []
    slaves = []
    if mode == "client":
        masters_file = "%s/%s" % (GlobalVar.SPARK_ECS_DIR, "masters")
        slaves_file = "%s/%s" % (GlobalVar.SPARK_ECS_DIR, "slaves")
    else:
        masters_file = "%s/%s/%s" % (GlobalVar.CLUSTER_INSTANCES, cluster_name, "masters")
        slaves_file = "%s/%s/%s" % (GlobalVar.CLUSTER_INSTANCES, cluster_name, "slaves")

    if os.path.exists(masters_file):
        f = open(masters_file, 'r')
        for line in f.readlines():
            masters.append(line.strip())
    if os.path.exists(slaves_file):
        f = open(slaves_file, 'r')
        for line in f.readlines():
            slaves.append(line.strip())

    return masters, slaves

def match_and_change(property, tag, content):
    children = property.getchildren()
    if children[0].text == tag:
        children[1].text = content
        return

def update_hadoop_configuration(namenode_url):
    file = ET.parse(GlobalVar.HADOOP_CONF_DIR + '/core-site.xml')
    properties = file.findall('./property')
    for property in properties:
        match_and_change(property, 'fs.defaultFS', namenode_url)
    file.write(GlobalVar.HADOOP_CONF_DIR + '/core-site.xml', encoding="utf-8")

def ssh_args():
    parts = ['-o', 'StrictHostKeyChecking=no']
    parts += ['-o', 'UserKnownHostsFile=/dev/null']
    parts += ['-o', 'LogLevel=quiet']
    return parts

def ssh_command():
    return ['ssh'] + ssh_args()

def scp_command():
    return ['scp', '-r'] + ssh_args()

def stringify_command(parts):
    if isinstance(parts, str):
        return parts
    else:
        return ' '.join(map(pipes.quote, parts))

def is_ssh_available(ip, opts, print_ssh_output=True):

    s = subprocess.Popen(
        ssh_command() + ['-t', '-t', '-o', 'ConnectTimeout=3',
                         '%s@%s' % (opts.user, ip), stringify_command('true')],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT  # we pipe stderr through stdout to preserve output order
    )
    cmd_output = s.communicate()[0]  # [1] is stderr, which we redirected to stdout

    if s.returncode != 0 and print_ssh_output:
        # extra leading newline is for spacing in wait_for_cluster_state()
        print textwrap.dedent("""\n
            Warning: SSH connection error. (This could be temporary.)
            Host: {h}
            SSH return code: {r}
            SSH output: {o}
        """).format(
            h=ip,
            r=s.returncode,
            o=cmd_output.strip()
        )

    return s.returncode == 0

def is_cluster_ssh_available(cluster_instances, opts):
    for i in cluster_instances:
        instance_info = ecs.get_instance_info(i)
        ip = instance_info['InnerIpAddress']['IpAddress'][0]
        if not is_ssh_available(ip, opts, True):
            return False
    else:
        return True

def save_public_ips(masters, slaves):
    cluster_hosts = open(GlobalVar.SPARK_ECS_DIR + "/" + GlobalVar.CLUSTER_HOSTS + "-public", 'w')

    for node in masters + slaves:
        instance_info = ecs.get_instance_info(node)
        host = instance_info['HostName']
        ip = instance_info['PublicIpAddress']['IpAddress'][0]
        cluster_hosts.write(ip + "  " + host + "\n")

    cluster_hosts.close()

def check_cluster_status(cluster_name, status):
    if not os.path.exists(GlobalVar.DEFAULT_CONF_DIR + "/status"):
        os.mkdir(GlobalVar.DEFAULT_CONF_DIR + "/status")
    if not os.path.exists(GlobalVar.CLUSTER_STATUS + cluster_name):
        f = open(GlobalVar.CLUSTER_STATUS + cluster_name, "w")
        f.close()
        return False
    f = open(GlobalVar.CLUSTER_STATUS + cluster_name, "r")
    stat = f.readline().strip()
    return stat in status

def delete_file_safely(path):
    print "deleting %s" % path
    if os.path.exists(path):
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)

def launch_cluster(opts, cluster_name):
    if opts.pwd == "":
        opts.pwd = getpass.getpass("""You need to provide a password for ECS instance.
If `CLIENT` mode, you just need to provide login machine's password.
If `CLUSTER` mode and `--include-gateway`, you just need to provide login machine's password.
If `CLUSTER` mode only, you need to set a new default password for each ECS instance.
Please set a password:""")

    if opts.ami is None:
        print "You need to specify an available ECS image, listed as following: \n"
        length = len(GlobalVar.AVAILABLE_SAPRK_VERSION)
        for idx in range(1, length+1):
            id = "%s" % idx
            print idx, ': ', GlobalVar.AVAILABLE_SAPRK_VERSION[id]
        print
        msg = "Please choose an image No. (like: 1): "
        id = raw_input(msg)
        spark_version = GlobalVar.AVAILABLE_SAPRK_VERSION[id]
        opts.ami = GlobalVar.SPARK_IMAGES[(spark_version, opts.region)]

    if opts.instance_type is None:
        print "You need to specify the type of ECS instance, listed as following: \n\n" \
              "%-14s: %s" % ("type name",  "(cores, memory)")
        for instance_type in GlobalVar.ECS_INSTANCE_TYPE:
            print "%-14s: %s" % (instance_type, GlobalVar.ECS_INSTANCE_TYPE[instance_type])
        print
        msg = "Please choose an ECS instance type (like: ecs.t1.small): "
        opts.instance_type = str(raw_input(msg)).strip()

    print "==> Begin to launch Spark cluster..."
    print_shopping_list(opts)
    print "==> Setting internet security rules..."
    current_group_id = ecs.get_gateway_instance_info(opts)['SecurityGroupIds']['SecurityGroupId'][0]
    ecs.clear_security_group_rules(current_group_id, opts)
    authorized_address = opts.authorized_address
    ecs.authorize_security_group_in(current_group_id, 'tcp', "", authorized_address, '22/22', opts)
    ecs.authorize_security_group_out(current_group_id, 'tcp', "", authorized_address, '1/65535', opts)
    if opts.enable_slave_public_ip:
        ecs.authorize_security_group_in(current_group_id, 'tcp', "", authorized_address, '8080/8080', opts)
        ecs.authorize_security_group_in(current_group_id, 'tcp', "", authorized_address, '8081/8081', opts)
        ecs.authorize_security_group_in(current_group_id, 'tcp', "", authorized_address, '9000/9000', opts)

    print "==> Launching master and slaves..."
    # Launch slaves
    master_instances = []
    slave_instacens = []
    count = 0
    while (count < opts.slaves):
        slave_instance_name = cluster_name + "-slave-%s" % (count)
        slave_instance_id = ecs.launch_instance(opts, cluster_name, "slaves", opts.ami, opts.instance_type, current_group_id,
                                            slave_instance_name, opts.ibo, slave_instance_name,
                                            opts.pwd, open_public_ip=opts.enable_slave_public_ip)
        slave_instacens.append(slave_instance_id)
        count += 1

    if not opts.include_gateway:
        # Launch master
        master_instance_name = cluster_name + "-master"
        master_instance_id = ecs.launch_instance(opts, cluster_name, "masters", opts.ami, opts.instance_type, current_group_id,
                                             master_instance_name, opts.ibo, master_instance_name,
                                             opts.pwd, open_public_ip=True)
        master_instances.append(master_instance_id)
    else:
        gateway = ecs.get_gateway_instance_info(opts)['InstanceId']
        master_instances.append(gateway)
        save_masters_or_slaves(cluster_name, "masters", gateway)

    master_ip = ecs.get_instance_info(master_instances[0])['PublicIpAddress']['IpAddress'][0]

    return master_instances, slave_instacens, master_ip

def wait_for_cluster_state(cluster_state, instances):
    sys.stdout.write("==> Waiting for cluster to enter one of `{s}` status .".format(s=cluster_state))
    sys.stdout.flush()

    start_time = datetime.now()
    while True:
        time.sleep(5)

        all_instances_status = ecs.get_all_instances_status(instances)
        if all(status in cluster_state for status in all_instances_status):
            break

        sys.stdout.write(".")
        sys.stdout.flush()
    sys.stdout.write("\n")

    end_time = datetime.now()
    print "Cluster is now in one of '{s}' status. Waited {t} seconds.".format(
        s=cluster_state,
        t=(end_time - start_time).seconds
    )

def update_hosts(instance_id, opts, src, dst):
    src_file = src + "/" + GlobalVar.CLUSTER_HOSTS
    dst_file = dst + "/" + GlobalVar.CLUSTER_HOSTS
    append_hosts = "cat %s >> /etc/hosts" % dst_file
    remove_tmp_hosts = "rm -f %s" % dst_file
    do_scp(instance_id, opts, src_file, dst_file)
    do_ssh(instance_id, opts, append_hosts)
    do_ssh(instance_id, opts, remove_tmp_hosts)

def do_scp(instance_id, opts, src, dst):
    instance_info = ecs.get_instance_info(instance_id)
    ip = instance_info['InnerIpAddress']['IpAddress'][0]
    tries = 0
    while True:
        try:
            res = subprocess.check_call(
                ["sshpass", "-p", opts.pwd] +
                scp_command() + [src, '%s@%s:%s' % (opts.user, ip, dst)])
            if res != 0:
                raise RuntimeError("Error executing remote command.")
            return res
        except subprocess.CalledProcessError as e:
            if tries > 5:
                # If this was an ssh failure, provide the user with hints.
                if e.returncode == 255:
                    raise UsageError(
                        "Failed to SSH to remote host {0}.\n".format(ip))
                else:
                    raise e
            print >> stderr, \
                "Error executing remote command, retrying after 10 seconds."
            time.sleep(10)
            tries += 1

def do_ssh(instance_id, opts, command):
    instance_info = ecs.get_instance_info(instance_id)
    ip = instance_info['InnerIpAddress']['IpAddress'][0]
    tries = 0
    while True:
        try:
            res = subprocess.check_call(
                ["sshpass", "-p", opts.pwd] +
                ssh_command() + ['-t', '-t', '%s@%s' % (opts.user, ip),
                                 stringify_command(command)])
            if res != 0:
                raise RuntimeError("Error executing remote command.")
            return res
        except subprocess.CalledProcessError as e:
            if tries > 5:
                # If this was an ssh failure, provide the user with hints.
                if e.returncode == 255:
                    raise UsageError(
                        "Failed to SSH to remote host {0}.\n".format(ip))
                else:
                    raise e
            print >> stderr, \
                "Error executing remote command, retrying after 10 seconds."
            time.sleep(10)
            tries += 1

def _check_output(*popenargs, **kwargs):
    if 'stdout' in kwargs:
        raise ValueError('stdout argument not allowed, it will be overridden.')
    process = subprocess.Popen(stdout=subprocess.PIPE, *popenargs, **kwargs)
    output, unused_err = process.communicate()
    retcode = process.poll()
    if retcode:
        cmd = kwargs.get("args")
        if cmd is None:
            cmd = popenargs[0]
        raise subprocess.CalledProcessError(retcode, cmd, output=output)
    return output

def ssh_read(instance_id, opts, command):
    instance_info = ecs.get_instance_info(instance_id)
    ip = instance_info['InnerIpAddress']['IpAddress'][0]
    return _check_output(
        ["sshpass", "-p", opts.pwd] + ssh_command() + ['%s@%s' % (opts.user, ip), stringify_command(command)])

def ssh_write(instance_id, opts, command, arguments):
    instance_info = ecs.get_instance_info(instance_id)
    ip = instance_info['InnerIpAddress']['IpAddress'][0]
    tries = 0
    while True:
        proc = subprocess.Popen(
            ["sshpass", "-p", opts.pwd] +
            ssh_command() + ['%s@%s' % (opts.user, ip), stringify_command(command)],
            stdin=subprocess.PIPE)
        proc.stdin.write(arguments)
        proc.stdin.close()
        status = proc.wait()
        if status == 0:
            break
        elif tries > 5:
            raise RuntimeError("ssh_write failed with error %s" % proc.returncode)
        else:
            print >> stderr, \
                "Error {0} while executing remote command, retrying after 10 seconds".format(status)
            time.sleep(10)
            tries = tries + 1

def prepare_hosts(master, slaves, opts):
    cluster_hosts = open(GlobalVar.SPARK_ECS_DIR + "/" + GlobalVar.CLUSTER_HOSTS, 'w')
    instance_info = ecs.get_instance_info(master)
    host = instance_info['HostName']
    ip = instance_info['InnerIpAddress']['IpAddress'][0]
    cluster_hosts.write(ip + "  " + host + "\n")

    for slave in slaves:
        instance_info = ecs.get_instance_info(slave)
        host = instance_info['HostName']
        ip = instance_info['InnerIpAddress']['IpAddress'][0]
        cluster_hosts.write(ip + "  " + host + "\n")

    cluster_hosts.close()
    update_hosts(master, opts, GlobalVar.SPARK_ECS_DIR, "/root/")
    for slave in slaves:
        update_hosts(slave, opts, GlobalVar.SPARK_ECS_DIR, "/root/")

def mount_disk(masters, slaves, opts):
    print "==> mounting data disk: /dev/xvdb ..."
    src = "%s/sh/mount_disk.sh" % GlobalVar.SPARK_ECS_DIR
    dst = "/root/"
    command = "/bin/bash /root/mount_disk.sh > /dev/null 2>&1"
    for ins in masters + slaves:
        do_scp(ins, opts, src, dst)
        do_ssh(ins, opts, command)
    print "==> mounted OK..."

# def update_default_output(opts):


def open_nginx(opts,masters):
    print "==> Starting nginx service..."
    host_info_path = GlobalVar.CLUSTER_HOSTS
    master_ip = ecs.get_instance_info(masters[0])['PublicIpAddress']['IpAddress'][0]
    result_code = start_nginx(opts, host_info_path, master_ip)
    if result_code == 1:
        print("[success] start nginx succcess ...")
    else:
        print("[error] start nginx failed ...")

def stop_nginx(opts, masters):
    print "==> Stopping nginx service..."
    master_ip = ecs.get_instance_info(masters[0])['PublicIpAddress']['IpAddress'][0]
    result_code = do_stop_nginx(opts, master_ip)
    if result_code == 1:
        print("[success] stop nginx succcess ...")
    else:
        print("[error] stop nginx failed ...")

def do_rollback():
    print "==> Doing rollback..."
    # TODO:

def welcome():
    print """
Welcome to:
      ____              __                    _____________
     / __/__  ___ _____/ /__    ___  ____    /___/___//___/
    _\ \/ _ \/ _ `/ __/  '_/   / _ \/__ /   /___//___.\ \.
   /___/ .__/\_,_/_/ /_/\_\    \__./_/_/   /___/____/___/
      /_/                                                  version 0.1

Type --help for more information.
    """

def print_shopping_list(opts):
    (cores, memory) = GlobalVar.ECS_INSTANCE_TYPE[opts.instance_type]
    if opts.disk_size is None:
        disk_size = "None"
    else:
        disk_size = "%sG" % opts.disk_size
    current_group_id = ecs.get_gateway_instance_info(opts)['SecurityGroupIds']['SecurityGroupId'][0]
    if opts.enable_slave_public_ip:
        slave_internet_charge_type = "PayByTraffic"
        slave_internet_bandwidth_out = opts.ibo
    else:
        slave_internet_charge_type = "PayByBandwidth"
        slave_internet_bandwidth_out = "0"

    print """The ECS instance configuration listed as following:

+--------------------------------------------------------+
+                   Check  List                          +
+--------------------------------------------------------+"""
    if not opts.include_gateway:
        print """
 Running Mode:                      %s

 Master Instance:
       Number:                      %s
       Region:                      %s
       Zone:                        %s
       Image:                       %s
       Cores:                       %s
       Memory:                      %sG
       Disk:                        %s
       InstanceType:                %s
       SecurityGroup:               %s
       InternetChargeType:          %s
       InternetMaxBandwidthOut:     %s
       """ % (opts.mode, "1", opts.region, opts.zone, opts.ami, cores, memory,
              disk_size, opts.instance_type, current_group_id, "PayByTraffic", opts.ibo)
    print """
 Slave Instance:
       Number:                      %s
       Region:                      %s
       Zone:                        %s
       Image:                       %s
       Cores:                       %s
       Memory:                      %sG
       Disk:                        %s
       InstanceType:                %s
       SecurityGroup:               %s
       InternetChargeType:          %s
       InternetMaxBandwidthOut:     %s
+--------------------------------------------------------+
        """ % (opts.slaves, opts.region, opts.zone, opts.ami, cores, memory, opts.instance_type,
               disk_size, current_group_id, slave_internet_charge_type, slave_internet_bandwidth_out)
    msg = "Continue buying? (Y/n): "
    to_buy = raw_input(msg)
    if to_buy != "Y":
        print "Not `Y`, give up buying ECS instances, Goodbye!"
        sys.exit(1)

def end_of_startup(opts, master_ip, masters):
    master_name = ecs.get_instance_info(masters[0])['HostName']
    print """
+--------------------------------------------------------+
+        Spark Cluster Started Successfully!             +
+--------------------------------------------------------+
The Spark Cluster Configuration listed as following:

    Spark Cluster:

        Master Node IP:  %s
        Spark UI:        http://%s:8080
        Master URL:      spark://%s:7077

    """ % (master_ip, master_ip, master_name)

    if opts.enable_hdfs:
        print """
    HDFS NameNode URL:   hdfs://%s:9000
        """ % master_ip

    if opts.enable_spark_notebook:
        print """
    Spark Notebook:      http://%s:9090
        """ % master_ip
    if opts.enable_hue:
        print """
    Hue:                 http://%s:8888
        """ % master_ip
    print"""
+--------------------------------------------------------+
        """

def warning():
    print """
**********************************************************
**                     WARNING!!!                       **
**********************************************************
    """
