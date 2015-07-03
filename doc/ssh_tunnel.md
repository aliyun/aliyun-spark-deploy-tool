# 打通SSH隧道

打通`本机	<-->	Spark Master`, 以便在本机访问Spark UI, Hue, Spark Notebook.		

要连接主节点的 SparkUI、HUE、Spark-notebook的UI界面，需要创建本机到Spark主节点的SSH隧道，以本地端口转发到远程端口的安全的方式访问。具体的创建步骤如下：

## SSH客户端配置

支持PuTTY（windows）或OpenSSH（linux、Max OSX）

###	windows相关配置

1. 首先[下载PuTTY](http://www.chiark.greenend.org.uk/~sgtatham/putty/download.html)
2. 配置PuTTY    
	*	首先创建一个session并配置好Master的IP地址和22端口号并保存session。这一步的目的是能连接到SSH Server建立一个SSH通道    
		![](http://i.imgur.com/AgmjuGL.jpg)
	*	切换到Tunnel面板，分别配置Source Port和 Destination的IP端口，然后点击Add保存端口转发映射    
		![](http://i.imgur.com/MWOj90s.jpg)

3. 点击open按钮，输入用户名密码登陆
	这样就建立好了一个带有端口转发的SSH隧道。访问`http://127.0.0.1:8888`端口的请求就会被转发到远程机器的`9000`端口。通过此方式，就可以安全的访问Spark UI、spark-notebook、和HUE的页面了。

###	Linux相关配置

1.	安装openssh （ECS默认都有安装）
2. 执行命令 `ssh -N -f -L port1:127.0.0.1:port2 username@ip`

*参数说明*

参数 | 描述
------------ | -------------
-N | 参数告诉SSH客户端，改命令仅仅做端口转发
-f|告诉SSH客户端在后台运行
-L|做本地映射端口
port1|要使用的本地端口
port2|要映射的远程端口
username|登陆远程机器的用户名
ip|要建立通道的远程机器的IP


>	连接成功后，在浏览器访问 127.0.0.1：port1 就可以被转发到服务器的 ip：port2端口了     
>	因为直接访问服务的器的目标端口是被防火墙屏蔽的，所以SSH隧道技术，可以绕过防火墙的设置，并提供了一个安全访问的机制。

## 使用SparkUI、spark-notebook、Hue

请确保上文中SSH隧道能够打通

###	Web服务的端口映射绑定
	
SparkUI的配置：

####	Linux命令行执行如下命令
1. 将本地`8081`绑定到远程`80`端口      
	`ssh -N -f -L 8081:127.0.0.1:80 username@ip`    
   >	username和ip分别为登陆master机器的username和IP     
2. 将本地`80`绑定到远程`80`端口    
	`ssh -N -f -L 80:127.0.0.1:80 username@ip`       
   >	username和ip分别为登陆master机器的username和IP
3. 将本地`8080`绑定到远程`80`端口    
	`ssh -N -f -L 8080:127.0.0.1:80 username@ip`        
	>	username和ip分别为登陆master机器的username和IP
4. 将本地`4040`绑定到远程`4040`端口    
		`ssh -N -f -L 4040:127.0.0.1:4040 username@ip`    
	>	username和ip分别为登陆master机器的username和IP
 
####	windows下 Putty的配置
1. 将本地 8081 绑定到远程 80 端口    
	结合上图切换到 Tunnel对应的选项卡：    
	*	source port填写 8081
	*	Destination 填写 127.0.0.1:80
2. 将本地 80 绑定到远程 80 端口
   结合上图切换到 Tunnel对应的选项卡：    
	*	source port填写 80
	*	Destination 填写 127.0.0.1:80
3. 将本地 8080 绑定到远程 80 端口
	结合上图切换到 Tunnel对应的选项卡:     
	*	source port填写 8080
	*	Destination 填写 127.0.0.1:80
4. 将本地 4040 绑定到远程 4040 端口
	结合上图切换到 Tunnel对应的选项卡：    
	*	source port填写 4040
	*	Destination 填写 127.0.0.1:4040
    
####	将Spark master和所有slave的机器名绑定127.0.0.1

如： `127.0.0.1 23		hxs787e`

*	windows hosts文件路径: `C:\Windows\System32\drivers\etc\hosts`
*	linux hosts文件路径: `/etc/hosts`

####	Spark-notebook的配置：
	
1.	Linux命令行执行如下命令：
`ssh -N -f -L port1:127.0.0.1:9090 username@ip`
*username和ip分别为登陆master机器的username和IP，port1的值为与本机其他端口不冲突的任意有效值*
2. windows Putty的配置：
结合上图切换到 Tunnel对应的选项卡：    
	*	source port填写与本机其他端口不冲突的任意有效值
	*	Destination 填写 127.0.0.1:9090

####	配置Hue

1.	Linux命令行执行如下命令：
`ssh -N -f -L port1:127.0.0.1:8888 username@ip`
*username和ip分别为登陆master机器的username和IP，port1的值为与本机其他端口不冲突的任意有效值*

2.	windows Putty的配置
结合上图切换到 Tunnel对应的选项卡：     
	*	source port填写与本机其他端口不冲突的任意有效值
	*	Destination 填写 127.0.0.1:8888