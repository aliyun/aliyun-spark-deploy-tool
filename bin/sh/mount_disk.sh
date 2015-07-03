#!/bin/bash

mkdir -p /amrdata

if which mkfs.ext4 > /dev/null ;then
	if ls /dev/xvdb1 > /dev/null;then
	   if cat /etc/fstab|grep /amrdata > /dev/null ;then
			if cat /etc/fstab|grep /amrdata|grep ext3 > /dev/null ;then
				sed -i "/\/amrdata/d" /etc/fstab
				echo '/dev/xvdb1             /amrdata                 ext4    defaults        0 0' >> /etc/fstab
			fi
	   else
			echo '/dev/xvdb1             /amrdata                 ext4    defaults        0 0' >> /etc/fstab
	   fi
	   mount -a
	   echo ""
	   exit;
	else
		if ls /dev/xvdb ;then
fdisk /dev/xvdb << EOF
n
p
1


wq
EOF
			mkfs.ext4 /dev/xvdb1
			echo '/dev/xvdb1             /amrdata                 ext4    defaults        0 0' >> /etc/fstab
		fi
	fi
else
	if ls /dev/xvdb1 > /dev/null;then
	   if cat /etc/fstab|grep /amrdata > /dev/null ;then
			echo ""
	   else
			echo '/dev/xvdb1             /amrdata                 ext3    defaults        0 0' >> /etc/fstab
	   fi
	   mount -a
	   echo ""
	   exit;
	else
		if ls /dev/xvdb ;then
fdisk /dev/xvdb << EOF
n
p
1


wq
EOF
			mkfs.ext3 /dev/xvdb1
			echo '/dev/xvdb1             /amrdata                 ext3    defaults        0 0' >> /etc/fstab
		fi
	fi
fi

mount -a