#!/usr/bin/python
#coding=utf-8
import sys
import os
import tarfile
import time
import commands
import urllib2
import utils
from sys import stderr
from datetime import datetime
from common import GlobalVar

def setup_aliyun_sdk():
    lib_dir = os.path.join(GlobalVar.SPARK_ECS_DIR, "lib")
    if not os.path.exists(lib_dir):
        os.mkdir(lib_dir)
    ecs_sdk_lib_dir = os.path.join(lib_dir, "aliyun-sdk")
    if not os.path.isdir(ecs_sdk_lib_dir):
        tgz_file_path = os.path.join(lib_dir, "aliyun-sdk.tgz")
        print "Downloading Aliyun sdk..."
        download_stream = urllib2.urlopen(GlobalVar.ALIYUN_SDK_URL)
        with open(tgz_file_path, "wb") as tgz_file:
            tgz_file.write(download_stream.read())
        tar = tarfile.open(tgz_file_path)
        tar.extractall(path=lib_dir)
        tar.close()
        os.remove(tgz_file_path)
        os.system("mv %s/* %s/aliyun-sdk" % (lib_dir, lib_dir))
        print "Finished downloading Aliyun sdk"
    sys.path.insert(0, ecs_sdk_lib_dir)

setup_aliyun_sdk()
import aliyun.api

def set_secret_key():
    access_id = os.getenv('ALIYUN_ACCESS_ID')
    if access_id is None:
        print >> stderr, ("ERROR: The environment variable ALIYUN_ACCESS_ID must be set")
        sys.exit(1)
    access_key = os.getenv('ALIYUN_ACCESS_KEY')
    if access_key is None:
        print >> stderr, ("ERROR: The environment variable ALIYUN_ACCESS_KEY must be set")
    aliyun.setDefaultAppInfo(access_id, access_key)

set_secret_key()

def check_aliyun_api_ret_code(response):
    if "Code" in response:
        print "Fail."
        print response['Code']
        print response['Message']
        raise RuntimeError(response['Code'], response['Message'])

def authorize_security_group_in(group_id, ip_protocol, src_group_id, src_cidr_ip, port_range, opts):
    req = aliyun.api.Ecs20140526AuthorizeSecurityGroupRequest()
    req.RegionId = opts.region
    req.SecurityGroupId = group_id
    req.IpProtocol = ip_protocol
    req.PortRange = port_range
    if src_cidr_ip == "":
        req.SourceGroupId = src_group_id
        req.NicType = "intranet"
    else:
        req.SourceCidrIp = src_cidr_ip
        req.NicType = "internet"
    f = req.getResponse()
    check_aliyun_api_ret_code(f)

def authorize_security_group_out(group_id, ip_protocol, dst_group_id, dst_cidr_ip, port_range, opts):
    req = aliyun.api.Ecs20140526AuthorizeSecurityGroupEgressRequest()
    req.RegionId = opts.region
    req.SecurityGroupId = group_id
    req.IpProtocol = ip_protocol
    req.PortRange = port_range
    if dst_cidr_ip == "":
        req.DestGroupId = dst_group_id
        req.NicType = "intranet"
    else:
        req.DestCidrIp = dst_cidr_ip
        req.NicType = "internet"
    f = req.getResponse()
    check_aliyun_api_ret_code(f)

def get_security_group_rules(security_group_id, opts):
    req = aliyun.api.Ecs20140526DescribeSecurityGroupAttributeRequest()
    req.SecurityGroupId = security_group_id
    req.RegionId = opts.region
    f = req.getResponse()
    check_aliyun_api_ret_code(f)
    permissions = f['Permissions']['Permission']
    return permissions

def get_all_instances(opts):
    page_number = 1
    instances = []
    req = aliyun.api.Ecs20140526DescribeInstancesRequest()
    req.RegionId = opts.region
    req.PageSize = GlobalVar.ECS_API_PAGESIZE
    req.PageNumber = page_number
    f = req.getResponse()
    check_aliyun_api_ret_code(f)
    instances += f['Instances']['Instance']
    total_pages = f['TotalCount'] / (GlobalVar.ECS_API_PAGESIZE + 1) + 1
    while page_number < total_pages:
        page_number += 1
        req = aliyun.api.Ecs20140526DescribeInstancesRequest()
        req.RegionId = opts.region
        req.PageSize = GlobalVar.ECS_API_PAGESIZE
        req.PageNumber = page_number
        f = req.getResponse()
        check_aliyun_api_ret_code(f)
        instances += f['Instances']['Instance']

    return instances

def get_gateway_instance_info(opts):
    ip = commands.getoutput("""ifconfig eth0 | awk 'NR==2 {print $2}' | awk -F'[:]' '{print $2}'""")
    all_instances = get_all_instances(opts)
    for ins in all_instances:
        inner_ips = ins['InnerIpAddress']['IpAddress']
        public_ips = ins['PublicIpAddress']['IpAddress']
        if ip in inner_ips + public_ips:
            return ins
    raise RuntimeError('Could find instance information of the current gateway.')

def clear_security_group_rules(group_id, opts):
    security_group_rules = get_security_group_rules(group_id, opts)
    for rule in security_group_rules:
        if rule['SourceGroupId'] != "" or rule['SourceCidrIp'] != "":
            req = aliyun.api.Ecs20140526RevokeSecurityGroupRequest()
            req.SourceGroupId = rule['SourceGroupId']
            req.SourceCidrIp = rule['SourceCidrIp']
        else:
            req = aliyun.api.Ecs20140526RevokeSecurityGroupEgressRequest()
            req.DestGroupId = rule['DestGroupId']
            req.DestCidrIp = rule['DestCidrIp']
        req.SecurityGroupId = group_id
        req.RegionId = opts.region
        req.IpProtocol = rule['IpProtocol']
        req.PortRange = rule['PortRange']
        f = req.getResponse()
        check_aliyun_api_ret_code(f)

def launch_instance(opts, cluster_name, role, ami, instance_type, security_group_id, instance_name,
                    internet_band_out, host_name, pass_word, open_public_ip=False):
    req = aliyun.api.Ecs20140526CreateInstanceRequest()
    req.RegionId = opts.region
    req.ImageId = ami
    req.InstanceType = instance_type
    req.SecurityGroupId = security_group_id
    req.InstanceName = instance_name
    req.HostName = host_name.replace('_', '-')
    req.Password = pass_word
    if role == "masters" or open_public_ip:
        req.InternetChargeType = "PayByTraffic"
        req.InternetMaxBandwidthOut = internet_band_out
    else:
        req.InternetChargeType = "PayByBandwidth"
        req.InternetMaxBandwidthOut = "0"
    if opts.disk_size is not None:
        req.DataDisk_1_Category = "cloud"
        req.DataDisk_1_Device = "/dev/xvdb"
        req.DataDisk_1_Size = opts.disk_size

    req2 = aliyun.api.Ecs20140526StartInstanceRequest()
    req3 = aliyun.api.Ecs20140526AllocatePublicIpAddressRequest()

    f = req.getResponse()
    check_aliyun_api_ret_code(f)
    instance_id = f['InstanceId']
    utils.save_masters_or_slaves(cluster_name, role, instance_id)
    if open_public_ip:
        req3.InstanceId = instance_id
        f = req3.getResponse()
        check_aliyun_api_ret_code(f)
    req2.InstanceId = instance_id
    f = req2.getResponse()
    check_aliyun_api_ret_code(f)
    return instance_id

def release_ecs_instance(instance_ids):
    print("Terminating masters and slaves...")
    start_time = datetime.now()

    print "==> Checking cluster status. We can do noting before the cluster enter `Running` status..."
    utils.wait_for_cluster_state(['Running', 'Stopping', 'Stopped'], instance_ids)
    print "==> Checked OK..."

    need_to_stop = []
    need_to_release = []
    for ins in instance_ids:
        instance_info = get_instance_info(ins)
        status = instance_info['Status']
        if status in ['Running']:
            need_to_stop.append(ins)
            need_to_release.append(ins)
        elif status in ['Stopped', 'Stopping']:
            need_to_release.append(ins)

    for ins in need_to_stop:
        try:
            req = aliyun.api.Ecs20140526StopInstanceRequest()
            req.InstanceId = ins
            f = req.getResponse()
            check_aliyun_api_ret_code(f)
        except Exception, e:
            print e
            raise e

    retries = 0
    while True:
        time.sleep(5)
        all_released = True

        for ins in need_to_release:
            try:
                instance_info = get_instance_info(ins)
                if instance_info['Status'] == "Stopped":
                    req2 = aliyun.api.Ecs20140526DeleteInstanceRequest()
                    req2.InstanceId = ins
                    f = req2.getResponse()
                    check_aliyun_api_ret_code(f)
                elif instance_info['Status'] in ["Running", "Stopping"]:
                    all_released = False
            except Exception, e:
                print >> stderr, "Error releasing ECS instance, retrying later."
                time.sleep(5)
                if retries >= 10:
                    raise e

        if all_released:
            break

        retries += 1

    end_time = datetime.now()
    print "Cluster instances have been released successfully. Waited {t} seconds.".format(
        t=(end_time - start_time).seconds
    )

def get_all_instances_status(instances):
    all_instances_status = []
    for ins in instances:
        instance_status = get_instance_info(ins)['Status']
        all_instances_status.append(instance_status)
    return all_instances_status

def get_instance_info(instance_id):
    req = aliyun.api.Ecs20140526DescribeInstanceAttributeRequest()
    req.InstanceId = instance_id
    f = req.getResponse()
    check_aliyun_api_ret_code(f)
    return f

