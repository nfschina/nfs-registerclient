#!/usr/bin/python   
#coding:utf-8   

#import pygtk
#pygtk.require('2.0')
import pynotify
#import sys
#import gtk
import os
import base64
import pycurl
import time
from ctypes import *

lib = cdll.LoadLibrary('/usr/lib/libSDK_VerifyRegister.so')
class StructPointer(Structure):
	_fields_=[("SC_RespInfo", c_char * 64),("SC_ValidTime",c_char * 20), ("SC_RespCode", c_long)]	


def clear_reg_status():
	writestatus_temp = "0"
	writestatus = base64.encodestring(writestatus_temp)
	os.system("sudo /usr/share/registerclient/savestatus.sh %s" % (writestatus))


def auth_reginfo():
	#self.entry_registor.get_text()
	fp = open("/usr/share/registerclient/reginfo","r")
	reginfo_temp = fp.read() #read file all content
	fp.close()
	print len(reginfo_temp)
	if len(reginfo_temp) == 0:
		print "reglen=" + len(reginfo_temp)
		return ""
	else:
		reginfo = ""
		fp = open("/usr/share/registerclient/reginfo","r")
		for line in fp:
    			reginfo = reginfo + base64.decodestring(line)
		#reginfos = base64.decodestring(reginfo_temp)
		print "reginfo = " + reginfo
		fp.close()
		#reglist = reginfos.split("&")
		#if len(reglist) > 0:
			#regcodelist = reglist[0].split("=")
			#if len(regcodelist) ==2:
				#regcode = regcodelist[1]
			#else:
				#return
		#else
			#return
		#if reginfos == "":
			#return ""
		lib._SDK_DoRegisterForAuth.restype = POINTER(StructPointer)
		print "in"
		get_data = lib._SDK_DoRegisterForAuth(reginfo)
		print "out"
		print "RespCode:"
		print get_data.contents.SC_RespCode
		print "ValidTime:"
		print get_data.contents.SC_ValidTime
		print "RespInfo:"
		print get_data.contents.SC_RespInfo
		rregcode = ""
		#if not get_data.contents.SC_RespInfo:
		try:
			fpw = open("/usr/share/registerclient/unregist_code", "r")
			regstatus_temp = fpw.read()  # read file all content
			rregcode = base64.decodestring(regstatus_temp)
			fpw.close()
		except:
			print "file /usr/share/registerclient/unregist_code not found"
		print rregcode
		if get_data.contents.SC_RespCode == 201:
			if not rregcode:
				writestatus_temp = "1 "+get_data.contents.SC_ValidTime
			else:
				writestatus_temp = "1 "+get_data.contents.SC_ValidTime+ " " + rregcode
			writestatus = base64.encodestring(writestatus_temp)
			#os.system("sudo /usr/share/registerclient/savestatus.sh %s" % (writestatus_temp))
			fp = open("/usr/share/registerclient/status.ini","w")
			fp.write(writestatus)
			fp.close()
			print get_data.contents.SC_RespInfo
			auth_notify = "系统已注册验证成功! 注册到期时间是"+get_data.contents.SC_ValidTime
			os.system("sudo /usr/share/registerclient/registerafter.sh")
		elif get_data.contents.SC_RespCode == 302:
			lib._SDK_ConfirmRegForAuth.restype = POINTER(StructPointer)
			get_data = lib._SDK_ConfirmRegForAuth(reginfo)
			tip = "更新成功"
			if not rregcode:
				writestatus_temp = "1 "+get_data.contents.SC_ValidTime
			else:
				writestatus_temp = "1 "+get_data.contents.SC_ValidTime+ " " + rregcode
			writestatus = base64.encodestring(writestatus_temp)
			fp = open("/usr/share/registerclient/status.ini","w")
			print writestatus_temp
			fp.write(writestatus)
			fp.close()
			print "savestatus.sh begin"
			#os.system("sudo /usr/share/registerclient/savestatus.sh %s" % (writestatus_temp))
			print "savestatus.sh end"
			print get_data.contents.SC_RespInfo
			auth_notify = "系统已注册验证成功! 注册到期时间是"+get_data.contents.SC_ValidTime
			print "registerafter.sh begin"
			os.system("sudo /usr/share/registerclient/registerafter.sh")
			print "registerafter.sh end"
		elif get_data.contents.SC_RespCode == 202:
			if not rregcode:
				writestatus_temp = "1 "+get_data.contents.SC_ValidTime
			else:
				writestatus_temp = "1 "+get_data.contents.SC_ValidTime+ " " + rregcode
			writestatus = base64.encodestring(writestatus_temp)
			#os.system("sudo /usr/share/registerclient/savestatus.sh %s" % (writestatus_temp))
			fp = open("/usr/share/registerclient/status.ini","w")
			fp.write(writestatus)
			fp.close()
			print get_data.contents.SC_RespInfo
			auth_notify = " "
			os.system("sudo /usr/share/registerclient/updatestatus.sh")
		elif get_data.contents.SC_RespCode == 400:
			#tip = "注册失败！"
			print get_data.contents.SC_RespInfo
			auth_notify = "注册验证失败！"
			clear_reg_status()
			os.system("sudo /usr/share/registerclient/updatestatus.sh")
		elif get_data.contents.SC_RespCode == 401:
			print get_data.contents.SC_RespInfo
			#tip = "注册码已注册！"
			auth_notify = "系统注册码已被使用过，请重新试一个！"	
			clear_reg_status()		
			os.system("sudo /usr/share/registerclient/updatestatus.sh")
		elif get_data.contents.SC_RespCode == 402:
			print get_data.contents.SC_RespInfo
			auth_notify = "注册验证失败！"
			clear_reg_status()
			os.system("sudo /usr/share/registerclient/updatestatus.sh")
		elif get_data.contents.SC_RespCode == 405:
			print get_data.contents.SC_RespInfo
			auth_notify = "注册验证失败！"
			clear_reg_status()
			os.system("sudo /usr/share/registerclient/updatestatus.sh")
		else:
			print get_data.contents.SC_RespInfo
			auth_notify = "注册验证失败！"
			clear_reg_status()
			os.system("sudo /usr/share/registerclient/updatestatus.sh")
		return auth_notify


#def help_cb(n, action):
#    assert action == "help"
#    print "You clicked Help"
#    n.close()
# os._exit(0)
time.sleep(5)
pynotify.init ("registertips")  
#nfs_icon=gdk_pixbuf_new_from_file("/usr/share/nfs/image/logo.png")
#uri = "file://usr/share/nfs/image/logo.png"

fp = open("/usr/share/registerclient/status.ini","r")
regstatus_temp = fp.read() #read file all content
fp.close()

regstatus = base64.decodestring(regstatus_temp)
statuslist = regstatus.split()   #status list
statuslistlen = len(statuslist)  #status list length
print "statuslist[0]=" + statuslist[0]
if statuslist[0] == "1": 
	if statuslistlen >= 2:
		time = statuslist[1]
		if statuslistlen >= 4:
			time = statuslist[3]
		print "time=" + time
		if cmp(time,"NoRegister")==0:
			#self.window.set_title("填写密钥(注册码规则检查通过)")
			#check net connected
			#if os.system('ping -c 2 -w 2 nisc.nfschina.com'):
			curl = pycurl.Curl()
			curl.setopt(pycurl.CONNECTTIMEOUT,1)
			curl.setopt(pycurl.TIMEOUT,1)
			curl.setopt(pycurl.MAXREDIRS,1)
			curl.setopt(pycurl.FORBID_REUSE,1)
			curl.setopt(pycurl.URL,"http://nisc.nfschina.com")
			try:
				curl.perform()
			except Exception,err:
				print err
				print "net not connected."
				register_notify = pynotify.Notification ("提示:您的注册信息未验证！", "请您及时联网进行注册信息验证！")
				# register_notify.set_urgency("critical")
			else:
				print "net connected."
				#send reginfo to server for auth
				notify_info = auth_reginfo()
				print "notify_info=" + notify_info.__str__()
				register_notify = pynotify.Notification ("提示:您的注册信息已验证！", notify_info.__str__())
				fp = open("/usr/share/registerclient/status.ini","r")
				status_temp = fp.read() #read file all content
				fp.close()
				statuslist_temp = base64.decodestring(status_temp).split()
				statuslistlen_temp = len(statuslist_temp)  #status list length
				if statuslistlen_temp >= 2:
					if cmp(statuslist_temp[1],"NoRegister")==0:
						register_notify.set_urgency("critical")

				if statuslistlen_temp == 1:
					if cmp(statuslist_temp[0],"0")==0:
						register_notify.set_urgency("critical")
			register_notify.show() 

		#else:
		#	register_notify = pynotify.Notification ("提示:您使用的系统已注册！", "注册到期时间是"+time) 
			#register_notify.set_urgency("critical")


#else:
#	register_notify = pynotify.Notification ("提示:您使用的系统尚未注册！", "请在系统注册客户端中使用序列号完成系统注册！\n\n注册完成后, 您可以获得更完整的体验和更贴心的服务!") 
#	register_notify.set_urgency("critical")

#register_notify.set_icon_from_pixbuf (nfs_icon) 
#register_notify.add_action () 
#helper = gtk.Button()
#icon = helper.render_icon(gtk.STOCK_DIALOG_QUESTION, gtk.ICON_SIZE_DIALOG)
#register_notify.set_icon_from_pixbuf(icon) 

#register_notify.add_action("help", "Help", help_cb)


