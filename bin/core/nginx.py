#!/usr/bin/python
#coding=utf-8
import sys
import os
import utils
from core.common import GlobalVar
from config_nginx import generate_config_file

def copy_file(opts, src_file, ip, dst):
    try:
        os.system("sshpass -p %s scp -r %s %s %s@%s:%s" % (opts.pwd, " ".join(utils.ssh_args()), src_file, opts.user, ip, dst))
    except Exception as e:
        print(e.message)
        raise e

def execute_remote_command(opts, ip, command):
    os.system("sshpass -p %s ssh %s %s@%s %s" % (opts.pwd, " ".join(utils.ssh_args()), opts.user, ip, command))

def execute_local_command(command):
    os.system(command)

def start_nginx(opts, host_info_file, ip):
    try:
        nginx_config_template_file = "%s/conf/nginx.conf.template" % GlobalVar.SPARK_ECS_DIR
        local_nginx_config = "%s/conf/nginx.conf" % GlobalVar.SPARK_ECS_DIR
        dst = "/opt/nginx-1.9.1/conf/nginx.conf"
        generate_config_file(host_info_file, nginx_config_template_file, local_nginx_config)
        copy_file(opts, local_nginx_config, ip, dst)
        start_nginx_command = "/opt/nginx-1.9.1/sbin/nginx"
        execute_remote_command(opts, ip, start_nginx_command)
        return 1
    except Exception as e:
        print "start nginx failed %s" % str(e.message)
        return -1

def do_stop_nginx(opts,ip):
    try:
        stopNginxCommand = "/opt/nginx-1.9.1/sbin/nginx -s stop"
        execute_remote_command(opts, ip, stopNginxCommand)
        return 1
    except Exception as e:
        print "stop nginx filed "+str(e.message)
        return -1




