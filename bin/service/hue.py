#!/usr/bin/python
#coding=utf-8
import os
import sys
from core import ecs, utils
from core.common import GlobalVar

def start_hue(masters, opts):
    print "==> Starting HUE service..."
    master = masters[0]
    ins = ecs.get_instance_info(master)
    ip = ins['InnerIpAddress']['IpAddress'][0]
    copy_command = ' \"/bin/cp -r %s/hue/desktop/conf/hue.ini %s/desktop/conf/ \"' \
                   % (GlobalVar.DEFAULT_CONF_DIR, GlobalVar.HUE_INSTALL_DIR)
    launch_hue_step1 = ' \"source /root/.bash_profile; cd %s/build/env/bin/; nohup ./hue livy_server > /dev/null 2>&1 & \" ' \
                       % GlobalVar.HUE_INSTALL_DIR
    launch_hue_step2 = ' \"source /root/.bash_profile; cd %s/build/env/bin/; nohup ./supervisor > /dev/null 2>&1 & \" ' \
                       % GlobalVar.HUE_INSTALL_DIR
    os.system("sshpass -p %s ssh %s %s@%s %s" % (opts.pwd, " ".join(utils.ssh_args()), opts.user, ip, copy_command))
    os.system("sshpass -p %s ssh %s %s@%s %s" % (opts.pwd, " ".join(utils.ssh_args()), opts.user, ip, launch_hue_step1))
    os.system("sshpass -p %s ssh %s %s@%s %s" % (opts.pwd, " ".join(utils.ssh_args()), opts.user, ip, launch_hue_step2))
    print "==> Started HUE service successfully"

def stop_hue(masters, opts):
    print "==> Stopping HUE service..."
    master = masters[0]
    ins = ecs.get_instance_info(master)
    ip = ins['InnerIpAddress']['IpAddress'][0]
    stop_hue_step1 = ' \" pgrep supervisor | xargs -r kill -9 \" '
    stop_hue_step2 = ' \" ps -ef | grep livy.server.Main | grep -v grep | awk \'{print \$2}\' | xargs -r kill -9 \" '
    stop_hue_step3 = ' \" pgrep hue | xargs -r kill -9 \" '
    os.system("sshpass -p %s ssh %s %s@%s %s" % (opts.pwd, " ".join(utils.ssh_args()), opts.user, ip, stop_hue_step1))
    os.system("sshpass -p %s ssh %s %s@%s %s" % (opts.pwd, " ".join(utils.ssh_args()), opts.user, ip, stop_hue_step2))
    os.system("sshpass -p %s ssh %s %s@%s %s" % (opts.pwd, " ".join(utils.ssh_args()), opts.user, ip, stop_hue_step3))
    print "==> Stopped HUE service successfully"
