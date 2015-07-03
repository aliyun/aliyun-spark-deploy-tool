#!/usr/bin/python
#coding=utf-8
import os
import sys

def do_generate_upstream_server_config(spark_host_info_path):

    format_tab = "\t"
    format_tab2 = format_tab*2
    up_stream_place_template = format_tab+"upstream server_${hostname} {"+os.linesep + \
                          format_tab2 + "server ${host}:${port};" + os.linesep + \
                          format_tab + "}"
    server_place_holder_template = format_tab+"server {" + os.linesep + \
                              format_tab2 + "listen 80;" + os.linesep + \
                              format_tab2 + "server_name ${hostname};"+os.linesep + \
                              format_tab2 + "location / {" + os.linesep + \
                              format_tab2 + "        proxy_pass http://server_${hostname};" + os.linesep + \
                              format_tab2 + "}"+os.linesep + \
                              format_tab + "}"
    spark_host_info_file = open(spark_host_info_path)
    host_info_lines = spark_host_info_file.readlines()[1:]

    up_stream_str = ""
    server_stream_str = ""

    spark_master_host_name = "spark_master"
    up_stream_master_item = up_stream_place_template.replace("${hostname}", spark_master_host_name)\
                                            .replace("${host}", "127.0.0.1")\
                                            .replace("${port}", "8080").replace("\t", "", 1)
    server_stream_master_item = \
        server_place_holder_template.replace("${hostname}", spark_master_host_name).replace("\t", "", 1)

    up_stream_str += up_stream_master_item + os.linesep
    server_stream_str += server_stream_master_item+os.linesep

    for host_info in host_info_lines:
        host_info_list = host_info.split()
        up_stream_item = up_stream_place_template.replace("${hostname}", host_info_list[1].strip()) \
                                            .replace("${host}", host_info_list[0].strip()) \
                                            .replace("${port}", "8081")
        server_stream_item = server_place_holder_template.replace("${hostname}", host_info_list[1].strip())

        up_stream_str += up_stream_item.rstrip() + os.linesep
        server_stream_str += server_stream_item.rstrip()+os.linesep
    return up_stream_str, server_stream_str

def do_update_nginx_config_file(result_content, nginx_config_target_path):
    nginx_config_file = file(nginx_config_target_path, "w")
    nginx_config_file.write(result_content)

def generate_config_file(spark_host_info_path,nginx_config_template_path, nginx_config_taget_path):

     up_stream_place_holder="${upstream_place_holder}"
     server_place_holder="${server_place_holder}"

     nginx_upstream_server_tuple = do_generate_upstream_server_config(spark_host_info_path)

     nginx_config_template_file = open(nginx_config_template_path)
     nginx_config_template_lines = nginx_config_template_file.readlines()
     result_content = ""
     for line in nginx_config_template_lines:
        result_content += line
    
     result_content = result_content.replace(up_stream_place_holder, nginx_upstream_server_tuple[0]) \
                  .replace(server_place_holder, nginx_upstream_server_tuple[1])
    
     do_update_nginx_config_file(result_content, nginx_config_taget_path)

