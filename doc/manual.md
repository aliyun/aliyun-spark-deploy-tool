# Spark On ECS 
v0.2      
2015.6.30


## Prepare
-------------
### 三种工作模式
脚本工作在三种不同的模式下，下面会介绍三种不同的模式：
* cluster + gateway exclude模式    
    需要先申请一台具有公网访问能力的ECS机器作为gateway，然后脚本会自动创建一个新的master和多台slaves，最终这个gateway机器不会成为集群的一部分。
* cluster + gateway include模式    
    需要先申请一台具有公网访问能力的ECS机器作为gateway。这台机器会作为集群的master存在，脚本会创建其余的slaves。
* client 模式    
    用户可以自行在ECS的购买页面上先行购买好所有的机器，（但是需要使用我们的Spark环境的镜像，此外机器的密码目前需要都一样）。然后在其中一台具有公网访问能力的机器上配置机器信息的配置文件，脚本会读取配置并负责环境的启动。


## Quick Start

####    cluster + gateway exclude模式
-------------

### 1. 选购Gateway    
在[阿里云ECS](http://www.aliyun.com/product/ecs/)购买一台ECS实例作为Gateway，用来执行自动化部署脚本。

*   Gateway需要配置公网IP，默认不作为Spark集群的一部分，Gateway可以用低配
*	Gateway所在地域默认为spark cluster的地域(Region)

### 2. 配置环境变量    

从[AccessKey管理](https://ak-console.aliyun.com/#/accesskey)获得阿里云API公钥密钥。在gateway上配置环境变量:    
 *ALIYUN_ACCESS_ID*和*ALIYUN_ACCESS_KEY*

```               
  export ALIYUN_ACCESS_ID=HAxxxxxxxxxx2     
  export ALIYUN_ACCESS_KEY=JAxxxxxxxxxxxxxxxxxxxxxxxxxs       
```    
*考虑到安全性, 推荐每次登陆时在当前会话中设置环境变量; 出于方便也可以在.bash_profile中配置(不推荐)*  

###	3.	执行脚本, 启动spark集群    

- 在geteway上执行： **`python spark_ecs.py --mode=cluster -t ecs.s2.large launch spark-test`**

- 购买前会有一个Check List，列出您购买的ECS实例配置和个数，如下：

```
+--------------------------------------------------------+
+                   Check   List                         +
+--------------------------------------------------------+

 Running Mode:                      cluster

 Master Instance:
       Number:                      1
       Region:                      cn-hangzhou
       Zone:                        cn-hangzhou-d
       Cores:                       2
       Memory:                      4G
       InstanceType:                ecs.s2.large
       InternetChargeType:          PayByTraffic
       InternetMaxBandwidthOut:     2
       

 Slave Instance:
       Number:                      1
       Region:                      cn-hangzhou
       Zone:                        cn-hangzhou-d
       Cores:                       2
       Memory:                      4G
       InstanceType:                ecs.s2.large
       InternetChargeType:          PayByBandwidth
       InternetMaxBandwidthOut:     0
+--------------------------------------------------------+
            
```	
这里会看到所有的生成的实例的信息，比如

* Number 对应节点的数量
* Region 表示所在的region
* Zone 所在的zone
* Image 使用的镜像的id
* Cores 机器的核数的配置，目前所有的master和slaves的配置都是一样的
* Memory 使用的内容，目前所有的master和slaves的配置都是一样的
* InstanceType 这个是ECS的官方机型缩略代号
* SecurityGroup 机器所在的安全组，一般同一个集群的会在同一个安全组内
* InternetChargeType 公网流量的付费方式，按量和按带宽
* InternetMaxBandwidthOut 带宽大小


启动完，会打印出Spark集群所有服务的简要信息，如下：

```
+--------------------------------------------------------+
+        Spark Cluster Started Successfully!             +
+--------------------------------------------------------+
The Spark Cluster Configuration listed as following:

    Spark Cluster:

        Spark UI:  http://xxx.xxx.xxx.xxx:8080
        Master URL: spark://spark-test-master:7077      

+--------------------------------------------------------+	
```
- 到这里Spark Cluster就完全起来了, 下面可以愉快的跑spark任务了。

###	4.  Spark Sample Test
- 登陆到spark master: *ssh xxx.xxx.xxx.xxx*， master ip可以根据上面的成功启动的信息里面找到
- 执行:  `/opt/spark/bin/run-example SparkPi`, 测试spark任务能否跑成功。

###	5. 停止Spark Cluster和释放ECS
登陆到gateway上:

*	停止spark cluster: `spark_ecs.py --mode=cluster stop spark-test`
*	启动spark cluster: `spark_ecs.py --mode=cluster start spark-test`
*	释放ECS资源: `spark_ecs.py --mode=cluster destroy spark-test`

##	cluster + gateway include模式
基本上cluster gateway exclude模式一样，以下的几部需要注意
###	3.	执行脚本, 启动spark集群    

- 执行： **`python spark_ecs.py --mode=cluster --include-gateway -t ecs.s2.large launch spark-test`**
- 需要注意的是新申请的slaves的密码需要和已有的master一致

###	4.  Spark Sample Test
- 由于本机就是master，所以可以直接执行:  `/opt/spark/bin/run-example SparkPi`, 测试spark任务能否跑成功。

###	5. 停止Spark Cluster和释放ECS
由于本机就是master，直接在master机器上执行
*	停止spark cluster: `spark_ecs.py --mode=cluster stop spark-test`
*	启动spark cluster: `spark_ecs.py --mode=cluster start spark-test`
*	释放ECS资源: `spark_ecs.py --mode=cluster destroy spark-test`

##	client模式
### 1. 选购集群机器
不再需要选购gateway，取而代之的是，需要在ECS购买页面上购买好所有的机器，包括master和slaves

### 2. 配置环境变量    
从[AccessKey管理](https://ak-console.aliyun.com/#/accesskey)获得阿里云API公钥密钥。在master上配置环境变量: *ALIYUN_ACCESS_ID*和*ALIYUN_ACCESS_KEY*

```               
  export ALIYUN_ACCESS_ID=HAxxxxxxxxxx2     
  export ALIYUN_ACCESS_KEY=JAxxxxxxxxxxxxxxxxxxxxxxxxxs       
```    
*考虑到安全性, 推荐每次登陆时在当前会话中设置环境变量; 出于方便也可以在.bash_profile中配置(不推荐)*

###	3.	脚本下载    

下载地址: [此处](), 将脚本拷贝到master任意目录下,例如`$HOME/spark`    
并在脚本目录下创建master和slaves文件    
master内将要作为master机器的instance id写进去    
一行一个id，类似
```
i-m32135678d
```
slaves内将要作为slaves机器的instance id(instance id 可以在ECS的实例列表上看到。)写进去
一行一个id，类似
```
i-m12563538d
i-m12332678d
i-m46745678d
```

###	4.	执行脚本, 启动spark集群    

- 在master上执行： **`python spark_ecs.py --mode=client launch spark-test`**

###	6. 停止Spark Cluster和释放ECS
在master上:

*	停止spark cluster: `spark_ecs.py --mode=client stop spark-test`
*	启动spark cluster: `spark_ecs.py --mode=client start spark-test`
*	释放ECS资源: `spark_ecs.py --mode=client destroy spark-test`

**脚本的更多参数设置见下面的用户手册。**

##		Manual
-------------

**Usage: `spark-ecs [options] <action> <cluster_name>[:<module_name>]`**    
**`<action>`可以是: launch, destroy, stop, start, enable, disable**     
**`<module_name>`可以是: hdfs, hue, spark-notebook**

启动Spark集群格式: `python spark-ecs.py -t <ecs-instance-type> -i <ecs-image-id> -s <num-slaves> -p <password> launch <cluster-name>`

例如: `python spark-ecs.py -t ecs.s2.large -i m-xxxxxxx5j -s 2 -p xxxxxx launch test`

启动单独服务格式：`python spark-ecs.py enable <cluster-name>:<module_name>`

例如： `python spark-ecs.py enable test:hdfs`

###	命令描述

命令 | 参数 | 描述
----|---- | ----
launch|集群名字|创建并启动一个Spark集群 
destroy|集群名字|销毁Spark集群,并释放集群中所有ECS实例, **集群数据将无法恢复，请及时转移重要数据**。销毁后集群ECS实例将停止收取相关费用
stop|集群名字|停止Saprk集群，集群实例不会被释放，集群中数据不会丢失。**集群ECS实例将继续收取相关费用**
start|集群名字|再次启动Spark集群
enable|子服务名|启用一个子服务，例如hdfs，hue或者spark-notebook
disable|子服务名|关闭一个子服务，例如hdfs，hue或者spark-notebook

脚本执行完会打印出:

*	Spark UI地址: `http://<master-ip>:8080`
*	Spark Master: `spark://<master-hostname>:7077`
*	Spark Notebook(可选): `http://<master-ip>:9090`
*	Hue(可选): `http://<master-ip>:8888`

访问Spark UI检查所有的slave节点是否正常启动。Spark UI的使用方式见下面的说明。

### 脚本参数说明

运行`python spark-ecs.py --help`查看使用帮助。以下列出主要的配置项说明：

| 参数 |缩写| 要求 | 默认值 | 描述 | 可用模式 |
| ------------ | --- | ------------- | ------------ | ------------ | ----- | 
|`--instance-type=<ecs-instance-type>`|-t|可选|无|配置所要创建的ECS实例类型. 更多类型见: [实例资源规格对照表](http://docs.aliyun.com/?spm=5176.730001.3.16.5mmF39#/pub/ecs/open-api/appendix&instancetype)|clueter模式有效|
| `--mode=<cluster-mode>`|-m|可选|cluster|运行模式。可选有client模式和cluster模式。client模式是使用已有ECS实例；cluster模式是创建新的ECS实例 | - |
| `--pwd=<password>` |-p|可选|无|配置Spark集群中每个ECS实例的默认密码|clueter模式有效| 
| `--ami=<ecs-image-id>`|无|可选|无|配置阿里云ECS机器镜像ID|clueter模式有效| 
|`--slaves=<num-slaves>`|-s|可选|1|配置Spark集群中Slave节点数|clueter模式有效| 
|`--ibo=<max-bandwidth-out>`|无|可选|2MB|配置实例的流出的带宽上限，计费以发生的公共网络流量为依据|clueter模式有效| 
|`--region=<region-id>`|-r|必选|无|配置ECS实例所属的Region. 注意:**Spark集群的ECS实例Region需要和login机器Region保持一致**|clueter模式有效| 
|`--zone=<zone-id>`|-z|可选|*cn-hangzhou-d*|配置ECS实例所属可用区|clueter模式有效| 
|`--include-gateway`|无 |可选|不包含|是否将当前登录机器包含进Spark集群|clueter模式有效|
|`--enable-slave-public-ip`|无|可选|不配置|是否配置Spark Slave节点的公网IP|clueter模式有效|
|`--enable-hdfs`|无|可选|不开启|是否打开HDFS服务|两种模式有效| 
|`--enable-hue`|无|可选|不开启|是否打开HUE服务|两种模式有效| 
|`--enable-spark-notebook`|无|可选|不开启|是否打开Spark Notebook服务|两种模式有效| 

**注意点:**

1. client模式时，一些参数无效，请注意每个参数的可用模式
2. cluster模式时，您可以选择是否将当前login机器加入到Spark集群中，详见`--include-gateway`参数。        
3. 不同可用区之间的数据传输需要收取公网流量费用：**￥0.8/GB**

###	模式参数说明

1. cluster模式
	ECS实例的申请，集群和服务的启动完全通过脚本完成。
2. client模式
	基于用户已有ECS实例，完成集群和服务的启动。    
	通过阿里云的售卖页面完成ECS实例的购买可以更加直观地获得费用信息。client模式需要提供两个文件`masters`和`slaves`，分别包含Master节点和Slave节点的实例ID，即`InstanceId`。可以在[ECS控制台](https://console.aliyun.com/ecs/index.htm)查看每个ECS实例的`InstanceId`。

**注意点:**

1. `masters`和`slaves`必须和脚本本放在同一目录中   
2. 使用client模式时，您需要注意购买ECS实例时选择我们提供的镜像并设置相同的默认密码，具体可参考[Spark镜像列表](https://github.com/aliyun/spark-on-ecs/tree/master/ecs-image-list)。


## Spark相关

###	Spark UI
目前提供两种方式支持Spark UI，即SSH隧道和公网开放式两种。

1. SSH隧道：通过在PC和Spark master节点之间的SSH隧道建立连接。这种方式安全性将会高一些，但需要您做一定的配置工作。具体操作过程请详见[SSH隧道使用指引](https://github.com/aliyun/spark-on-ecs/tree/master/doc/ssh_tunnel.md)。
2. 公网开放式：这种方式需要您在购买ECS实例时配置一个公网IP。这种方式会额外打开一些端口，例如8080，8081，9090等，安全性比SSH方式低，但使用上更加方便。
	- 脚本执行完, 会在当前目录创建Spark集群的Hosts列表文件，请把这个文件内容拷贝到本机的hosts文件中。Windows用户请编辑`C:\Windows\System32\drivers\etc\hosts`文件，Linux用户请编辑`\etc\hosts`文件
	- 由于每次创建集群的机器名和公网IP都会发生变化，所以一旦销毁集群请及时清除本机中相关的Hosts修改

**注意：** 建议使用SSH隧道方式。

### Spark Notebook

Spark Notebook提供一种交互式的编程方式，您可以在上面进行Spark程序开发。更多信息请关注[Spark Notebook](https://github.com/andypetrella/spark-notebook)的最新进展。

### Hue

Hue是一种开源的进行大数据分析的Web平台。更多信息请关注[Cloudera-Hue](https://github.com/cloudera/hue)的最新进展。

### 默认配置文件

本脚执行时会动态修改一些软件的配置文件。这些软件的默认配置文件放置在/root/.config目录下：

1. packages.property文件：配置每个软件的安装路径
2. hadoop目录：hadoop配置文件目录，包含core-site.xml，hdfs-site.xml以及hadoop-env.sh
3. hue目录：Hue配置文件目录，包含hue.ini
