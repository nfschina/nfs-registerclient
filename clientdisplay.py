#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
# if os.environ.has_key('LD_LIBRARY_PATH'):
#   os.environ['LD_LIBRARY_PATH'] = '/usr/lib:' + os.environ['LD_LIBRARY_PATH']
# else:
#    os.environ['LD_LIBRARY_PATH'] = '/usr/lib'
import gi
import datetime
import base64
import json
import signal
import dbus
import pycurl
import requests
import socket
import subprocess
import re
import uuid
from ctypes import Structure
from ctypes import c_char
from ctypes import c_char_p
from ctypes import c_long
from ctypes import cdll
from ctypes import create_string_buffer
from ctypes import POINTER
from pysqlcipher3 import dbapi2 as sqlite
from threading import Thread
gi.require_version('Gtk', '3.0')
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, GObject
from gi.repository import Gdk

lib = cdll.LoadLibrary('/usr/lib/libSDK_VerifyRegister.so')
CSS_FILE = "/usr/share/registerclient/style.css"
status_file = "/usr/share/registerclient/status.ini"
reg_server_url = "172.30.43.23"
port = "8111"

def get_safe_id():
    safeid = lib._SKD_GetSafeID
    safeid.argtypes = [c_char_p]
    safeid.restype = c_char_p
    safe_id = create_string_buffer("", 1960)
    # s3 = hostinfo(code, host_data)
    safeid(safe_id)
    return safe_id.value

def save_regcode(code):
    fp = open(status_file, "w")
    fp.write(base64.encodestring(code));
    fp.close()

def getBroadAddList():
    ######获取IP以及子网掩码
    #######windows 下的命令是ipconfig,LINUX下是ifconfig,倘若再不行，我们直接用python获取ip
    try:
        sys_cmd = subprocess.Popen('ifconfig',stdout=subprocess.PIPE)
    except Exception as e:#####如果用ipconfig命令无法获取到机器的ip,使用python的socket模块获取
        print e
        ip_add =  socket.gethostbyname(socket.getfqdn(socket.gethostname()))
        print ip_add
        index_ = ip_add.rfind(".")
        return [ip_add[:index_]+".255"]
    cmd_res = sys_cmd.stdout.read()
    pattern =  re.compile(r'((\d+\.){3}\d+\s)') #########正则匹配
    ip_list = pattern.findall(cmd_res)
    ip_add = []
    subMask = []
    for i in ip_list:
        if  int(i[0].rstrip().split(".")[-1]) == 0:
            subMask.append(str(i[0]))
            #print subMask
        else:
            ip_info =  i[0][:i[0].rfind(".")]
            if ip_info not in ip_add:ip_add.append(ip_info)
    #########计算广播地址
    broad_list = []
    for j in ip_add:
        if len(subMask) < 1:
            continue
        subMask_split = subMask.pop(0).split(".")
        #print subMask_split
        myIp = (j+".1").split(".")
        #print myIp
        str_cast = ""
        for i in xrange(4):
            xx = (int(myIp[i])&int(subMask_split[i]))|((int(subMask_split[i]))^255)
            str_cast = str_cast + str(xx)+"."
        if not str_cast == "127.255.255.255.":
            broad_list.append(str_cast.rstrip("."))
    print broad_list
    return broad_list

def get_mac_address():
    node = uuid.getnode()
    mac = uuid.UUID(int = node).hex[-12:]
    return ":".join([mac[e:e+2] for e in range(0,11,2)])

def get_regcode(safe_id):
    print("safe_id: %s" % safe_id)
    lib._SDK_GetServerIP.argtypes = [c_char_p, c_char_p]
    lib._SDK_GetServerIP.restype = c_char_p
    broadaddrs = getBroadAddList()
    if not broadaddrs:
        return False
    for broadaddr in broadaddrs:
        addr = lib._SDK_GetServerIP(broadaddr, port)
        if addr:
            break
    if not addr:
        addr = reg_server_url
    url = "http://" + addr + ":8000/get_regcode"
    print url
    curl = pycurl.Curl()
    curl.setopt(pycurl.CONNECTTIMEOUT,1)
    curl.setopt(pycurl.TIMEOUT,1)
    curl.setopt(pycurl.MAXREDIRS,1)
    curl.setopt(pycurl.FORBID_REUSE,1)
    curl.setopt(pycurl.URL,url)
    try:
        curl.perform()
    except Exception,err:
        print err
        return False

    headers = {
        'Content-type': 'application/json',
    }
    data = {}
    data["safe_id"] = safe_id
    data["mac"] = get_mac_address()
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        print response.text
        if response.status_code == 202:
            textjson = json.loads(response.text)
            save_regcode("1 " + textjson["valid_date"] + " " + textjson["regcode"] + " NoRegister")
            hostinfo = lib._SDK_GetHostInfo
            hostinfo.argtypes = [c_char_p, c_char_p]
            hostinfo.restype = c_char_p
            host_data = create_string_buffer("", 1960)
            # s3 = hostinfo(code, host_data)
            hostinfo(textjson["regcode"], host_data)
            final_info = host_data.value + "&valid_period=" + str(textjson["validperiod"])
            # 保存用户注册信息
            fp = open("/usr/share/registerclient/reginfo", "w")
            reginfo_tmp = base64.encodestring(final_info)  # 保存所有注册信息
            fp.write(reginfo_tmp)
            fp.close()
            return True
        return False
    except Exception as e:
        print e
        return False

def update_window(window):
    window.should_quit = False
    window.window.close()
    RegistedWindow()

def get_regcode_thread(window):
    safe_id = get_safe_id()
    if get_regcode(safe_id):
        GObject.idle_add(update_window, window)

class StructPointer(Structure):
    _fields_ = [("SC_RespInfo", c_char * 64), ("SC_ValidTime", c_char * 20),
                ("SC_RespCode", c_long)]

class RegistedWindow(object):
    def on_window_destroy(self, __widget):
        if self.should_quit:
            Gtk.main_quit()

    def __init__(self):
        self.system_bus = dbus.SystemBus()
        nfsmount = self.system_bus.get_object('com.nfs.register', '/')
        iface = dbus.Interface(nfsmount, dbus_interface='com.nfs.register')
        self.check_register = iface.get_dbus_method("check_register", dbus_interface=None)
        if not self.check_register() and not self.check_state():
            window = CreateWindow()
            getRegcodeThread = Thread(target=get_regcode_thread, args=[window])
            getRegcodeThread.start()
            return

        self.should_quit=True
        print("RegistedWindow __init__")
        self.set_theme()
        builder = Gtk.Builder()
        builder.add_from_file(
            "/usr/share/registerclient/ui/clientwindow.glade")
        builder.connect_signals(self)

        self.window = builder.get_object("window1")
        self.window.connect("destroy", self.on_window_destroy)
        self.window.set_icon_from_file(
            "/usr/share/registerclient/pic/registerclient.png")


        self.window.set_title("注册客户端")
        self.window.set_resizable(False)
        self.window.set_position(1)

        self.layout = builder.get_object("layout1")

        label_text1 = Gtk.Label()
        label_text2 = Gtk.Label()
        label_text3 = Gtk.Label()
        label_text4 = Gtk.Label()
        label_text5 = Gtk.Label()

        valid_time=""
        regcode=""
        fp = open("/usr/share/registerclient/status.ini", "r")
        regstatus_temp = fp.read()  # read file all content
        regstatus = base64.decodestring(regstatus_temp)
        statuslist = regstatus.split()  # status list
        statuslistlen = len(statuslist)  # status list length
        if statuslist[0] == "1":
            if statuslistlen >= 2:
                valid_time = statuslist[1]
            if statuslistlen >= 3:
                regcode = statuslist[2]

        if valid_time == "NoRegister":
            label_text1.set_markup(
                "<span foreground='#333333' font_desc='18'>%s</span>" % ("未验证"))
            label_text2.set_markup(
                "<span foreground='#333333' font_desc='12'>%s</span>" %
                ("您的注册信息未验证，请您及时联网进行注册信息验证！"))
            label_text4.set_markup(
                "<span foreground='#666666' font_desc='12'>%s</span>" %
                ("过期时间:"))
            image = Gtk.Image.new_from_file('/usr/share/registerclient/pic/unregistered.png')
            self.layout.put(image, 36, 21)
        else:
            label_text1.set_markup(
                "<span foreground='#333333' font_desc='18'>%s</span>" % ("已注册"))
            label_text2.set_markup(
                "<span foreground='#333333' font_desc='12'>%s</span>" %
                ("您的系统已完成注册。"))
            label_text4.set_markup(
                "<span foreground='#666666' font_desc='12'>%s</span>" %
                ("过期时间：%s" % valid_time))
            image = Gtk.Image.new_from_file('/usr/share/registerclient/pic/ok.png')
            self.layout.put(image, 36, 21)
        label_text3.set_markup(
            "<span foreground='#333333' font_desc='12'>%s</span>" %
            ("您的密钥：%s" % regcode.upper()))
        label_text5.set_markup(
            "<span foreground='#007FD1' underline='single' underline_color='blue' font_desc='12'>%s</span>" %
            ("更改密钥\n"))
        event_box = Gtk.EventBox()
        event_box.add(label_text5)
        event_box.connect("button_press_event",self.modify_button_press)

        self.exit_button = Gtk.Button.new_with_label("关闭")
        self.exit_button.connect("clicked", self.exit_button_press)
        self.exit_button.set_size_request(100,30)
        self.exit_button.show()
        self.layout.put(self.exit_button, 570, 385)

        self.layout.put(label_text1, 76, 21)
        self.layout.put(label_text2, 36, 71)
        self.layout.put(label_text3, 36, 113)
        self.layout.put(label_text4, 36, 140)
        self.layout.put(event_box, 36, 395)
        self.window.show_all()
    def set_theme(self):
        screen = Gdk.Screen.get_default()
        provider = Gtk.CssProvider.get_default()
        provider.load_from_path(CSS_FILE)
        Gtk.StyleContext.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)
    def modify_button_press(self, widget, event):
        self.should_quit=False
        self.window.close()
        CreateWindow()
        return
    def exit_button_press(self, widget):
        self.window.close()
        return
    def check_state(self):
        fp = open("/usr/share/registerclient/status.ini", "r")
        regstatus = fp.read()
        regstatus = base64.decodestring(regstatus)
        statuslist = regstatus.split()
        statuslistlen = len(statuslist)
        if statuslist[0] == "1":
            if statuslistlen >= 2:
                time = statuslist[1]
                if cmp(time,"NoRegister")!=0:
                    timeObjet = datetime.datetime.strptime(time, '%Y-%m-%d')
                    if not datetime.datetime.today() > timeObjet:
                        return True
                elif statuslistlen >= 3:
                    return True
        return False


class CreateWindow(object):
    def on_window_destroy(self, __widget):
        if self.should_quit:
            Gtk.main_quit()

    def __init__(self):
        print "CreateWindow"
        self.system_bus = dbus.SystemBus()
        nfsmount = self.system_bus.get_object('com.nfs.register', '/')
        iface = dbus.Interface(nfsmount, dbus_interface='com.nfs.register')
        self.register = iface.get_dbus_method("register", dbus_interface=None)
        self.check_register = iface.get_dbus_method("check_register", dbus_interface=None)
        self.updateRegcode = iface.get_dbus_method("updateRegcode",
                                                   dbus_interface=None)
        self.should_quit = True
        self.set_theme()
        builder = Gtk.Builder()
        builder.add_from_file(
            "/usr/share/registerclient/ui/clientwindow.glade")
        builder.connect_signals(self)

        self.window = builder.get_object("window1")
        self.window.connect("destroy", self.on_window_destroy)
        self.window.set_icon_from_file(
            "/usr/share/registerclient/pic/registerclient.png")

        fp = open("/usr/share/registerclient/status.ini", "rb")
        regstatus_temp = fp.read()  # read file all content

        regstatus = base64.decodestring(regstatus_temp)
        statuslist = regstatus.split()  # status list
        statuslistlen = len(statuslist)  # status list length
        # fp.readline()#'\n'
        if statuslist[0] == "1":
            # fp.seek(1,1)
            # time = fp.readline(10)
            if statuslistlen >= 2:
                time = statuslist[1]
                if cmp(time, "NoRegister") == 0:
                    self.window.set_title("填写密钥(注册码规则检查通过)")
                else:
                    time = statuslist[1]
                    timeObjet = datetime.datetime.strptime(time, '%Y-%m-%d')
                    if datetime.datetime.today() > timeObjet:
                        self.window.set_title("填写密钥(已过期 到期时间" + time + ")")
                    else:
                        self.window.set_title("填写密钥(已注册 到期时间" + time + ")")
        else:
            self.window.set_title("填写密钥(未注册)")
        fp.close()
        self.window.set_resizable(False)
        self.window.set_position(1)

        self.layout = builder.get_object("layout1")

        # image = Gtk.Image.new_from_file('background.jpg')
        #image = Gtk.Image.new_from_file('/usr/share/registerclient/pic/01.jpg')
        #self.layout.put(image, 0, 0)

        # self.vbox_register = builder.get_object("box7")
        label_text1 = Gtk.Label()
        label_text2 = Gtk.Label()
        label_text3 = Gtk.Label()
        label_text4 = Gtk.Label()
        self.tip_label = Gtk.Label()

        label_text1.set_markup(
            "<span foreground='#333333' font_desc='18'>%s</span>" % ("输入产品密钥"))
        label_text2.set_markup(
            "<span foreground='#333333' font_desc='12'>%s</span>" %
            ("产品密钥应该在方德桌面操作系统销售方或经销方给你的电子邮件中，或者在包装盒上。"))
        label_text3.set_markup(
            "<span foreground='#333333' font_desc='12'>%s</span>" %
            ("产品密钥类似于这样：(数字与英文组合)"))
        label_text4.set_markup(
            "<span foreground='#333333' font_desc='12'>%s</span>" %
            ("产品密钥：gkdiw4ux839201jbnxfjg8273yruwi2z"))

        self.entry_register = Gtk.Entry()
        #label_text_register = Gtk.Label()
        #label_text_register.set_markup(
        #    "<span foreground='#FFFFFF' font_desc='12'>%s</span>" % ("产品密钥"))
        self.entry_register.set_placeholder_text("产品密钥")
        self.entry_register.set_size_request(480, -1)
        self.entry_register.connect('changed', self.entry_changed)

        self.entry_register.set_max_length(25)
        self.layout.put(label_text1, 36, 30)
        self.layout.put(label_text2, 36, 82)
        self.layout.put(label_text3, 36, 134)
        self.layout.put(label_text4, 36, 153)
        #self.layout.put(label_text_register, 36, 188)
        self.layout.put(self.entry_register, 36, 200)
        self.layout.put(self.tip_label, 36, 240)

        self.entry_org = Gtk.Entry()
        self.entry_org.set_max_length(64)
        self.entry_org.set_size_request(480, -1)
        self.entry_org.set_placeholder_text("单位名称")
        self.layout.put(self.entry_org, 36, 273)
        
        self.entry_contact = Gtk.Entry()
        self.entry_contact.set_max_length(32)
        self.entry_contact.set_size_request(480, -1)
        self.entry_contact.set_placeholder_text("联系方式")
        self.layout.put(self.entry_contact, 36, 323)

        self.exit_button = Gtk.Button.new_with_label("退出")
        self.exit_button.connect("clicked", self.exit_button_press)
        self.exit_button.set_size_request(100,30)
        
        self.register_button = Gtk.Button.new_with_label("注册")
        style_context = self.register_button.get_style_context()
        style_context.add_class("button-register")
        self.register_button.connect("clicked", self.register_button_press)
        self.register_button.set_size_request(100,30)

        self.usb_register_button = Gtk.Button.new_with_label("通过U盘注册")
        self.usb_register_button.connect("clicked",
                                         self.usb_register_button_press)
        self.usb_register_button.set_size_request(100, 30)

        #self.register_image = Gtk.Image()
        #self.register_image.set_from_file(
        #    "/usr/share/registerclient/pic/register-1.png")
        #self.usb_register_image = Gtk.Image()
        # self.usb_register_image.set_from_file(
        #    "/usr/share/registerclient/pic/u.png")
        # self.sys_image.show()
        #self.register_button.add(self.register_image)
        self.register_button.show()
        # self.usb_register_button.add(self.usb_register_image)

        #self.exit_image = Gtk.Image()
        #self.exit_image.set_from_file(
        #    "/usr/share/registerclient/pic/cancle.png")
        # self.sys_image.show()
        # self.exit_button.add(self.exit_image)
        self.exit_button.show()

        self.layout.put(self.register_button, 460, 380)
        self.layout.put(self.exit_button, 570, 380)
        # self.layout.put(self.usb_register_button, 36, 290)

        self.register_button.grab_focus()
        self.window.show_all()

    def set_theme(self):
        screen = Gdk.Screen.get_default()
        provider = Gtk.CssProvider.get_default()
        provider.load_from_path(CSS_FILE)
        Gtk.StyleContext.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)

    def exit_button_press(self, widget):
        Gtk.main_quit()
        return

    def find_usb_storage(self):
        tip = ""
        self.tip_label.set_markup(
            "<span foreground='#DC143C' font_desc='12'>%s</span>" % (tip))
        comm = 'find /media -maxdepth 3 -type f -name register-nfs-5520-cbb.db 2>/dev/null'
        db_file = os.popen(comm).readlines()
        return db_file[0].strip()

    def get_unused_register_code(self):
        db_file = self.find_usb_storage()
        if not db_file:
            tip = "未发现可用注册u盘。"
            self.tip_label.set_markup(
                "<span foreground='#DC143C' font_desc='12'>%s</span>" % (tip))
            return None
        conn = sqlite.connect(db_file)
        c = conn.cursor()
        c.execute("PRAGMA key='qwe123'")
        c.execute(
            'select * from register_code where hdserial is null limit 0,1')
        values = c.fetchall()
        conn.commit()
        c.close()
        if len(values) > 0:
            return values[0][0]
        else:
            return None

    def get_hdserial(self):
        hdserial = os.popen(
            "smartctl -i /dev/sda 2>/dev/null | grep \"Serial Number:\" | awk '{print $3}'"
        ).readlines()
        if not hdserial:
            hdserial = os.popen(
                "smartctl -i /dev/nvme0n1 | grep \"Serial Number:\" | awk '{print $3}'"
            ).readlines()
        return hdserial[0].strip()

    def get_osuuid(self):
        osuuid = os.popen("dmidecode -s system-uuid").readlines()
        return osuuid[0].strip()

    def get_osrelease(self):
        version = os.popen(
            "cat /etc/os-release | grep ^VERSION_ID").readlines()
        version = version[0].split('=')
        return version[1].strip().strip('"')

    def register_code_in_usb(self, code):
        db_file = self.find_usb_storage()
        conn = sqlite.connect(db_file)
        c = conn.cursor()
        c.execute("PRAGMA key='qwe123'")
        createdate = datetime.datetime.now().strftime("%Y-%m-%d")

        sql = "UPDATE register_code SET createdate = '%s', hdserial = '%s', osuuid = '%s', osrelease = '%s' WHERE  regcode = '%s'" % (
            createdate, self.get_hdserial(), self.get_osuuid(),
            self.get_osrelease(), code)
        c.execute(sql)
        print sql

        conn.commit()
        c.close()

    def usb_register_button_press(self):
        fp = open("/usr/share/registerclient/status.ini", "r")
        regstatus_temp = fp.read()  # read file all content
        regstatus = base64.decodestring(regstatus_temp)
        statuslist = regstatus.split()  # status list
        statuslistlen = len(statuslist)  # status list length
        print statuslist[0]
        if statuslist[0] == "1":
            if statuslistlen >= 2:
                time = statuslist[1]
                tip = "此产品已经完成注册，无需再次注册！"
                self.tip_label.set_markup(
                    "<span foreground='#8A2BE2' font_desc='12'>%s</span>" %
                    (tip))
                return True

        code = None
        try:
            code = self.get_unused_register_code()
        except RuntimeError:
            tip = "注册码失败，未输入注册码且未在u盘中发现可用注册码！"
            self.tip_label.set_markup(
                "<span foreground='#DC143C' font_desc='12'>%s</span>" % (tip))
        if code is not None:
            if self.check_pw_compliance(code):
                tip = "注册码错误,请联系注册码发售商！"
                self.tip_label.set_markup(
                    "<span foreground='#DC143C' font_desc='12'>%s</span>" %
                    (tip))
                return False
            else:
                self.register_code_in_usb(code)
                fp = open("/usr/share/registerclient/status.ini", "w")
                writestatus_temp = "1 " + (
                    datetime.datetime.now() +
                    datetime.timedelta(days=360)).strftime("%Y-%m-%d")
                writestatus = base64.encodestring(writestatus_temp)
                # fp.write("1 "+get_data.contents.SC_ValidTime)
                fp.write(writestatus)
                fp.close()
                os.system("echo > /usr/share/registerclient/reginfo"
                          )  # clear reginfo

                fp = open("/usr/share/registerclient/status.ini", "r")
                # status = fp.read(1)
                regstatus_temp = fp.read()  # read file all content
                regstatus = base64.decodestring(regstatus_temp)
                statuslist = regstatus.split()  # status list
                statuslistlen = len(statuslist)  # status list length
                #  fp.readline()#'\n'
                print statuslist[0]
                if statuslist[0] == "1":
                    # fp.seek(1,1)
                    # time = fp.read(10)
                    if statuslistlen >= 2:
                        time = statuslist[1]
                        print time
                        self.window.set_title("填写密钥(已注册 到期时间" + time + ")")
                        tip = "注册成功！"
                        self.tip_label.set_markup(
                            "<span foreground='#8A2BE2' font_desc='12'>%s</span>"
                            % (tip))
                else:
                    self.window.set_title("填写密钥(未注册)")
                fp.close()
                os.system("/usr/share/registerclient/registerafter.sh")
        else:
            tip = "注册码失败，未输入注册码且未在u盘中发现可用注册码！"
            self.tip_label.set_markup(
                "<span foreground='#DC143C' font_desc='12'>%s</span>" % (tip))
        pass

    def stat(self, seq, aset):
        sum_num = 0
        for i in seq:
            if i in aset:
                sum_num += 1
        return sum_num

    def check_pw(self, number):
        letters = list('abcdefghijklmnopqrstuvwxyz')
        digit = list('0123456789')
        letters = self.stat(number.lower(), letters)
        digit = self.stat(number.lower(), digit)
        # print "letters = ",letters
        # print "digit = ",digit
        number_length = letters + digit
        # print "number_length = ",number_length
        if number_length < 25:
            return True
        return False

    def check_pw_compliance(self, registercodes):
        basecodes = list('abcdefghjklmnpqrstuvwxyz23456789')
        print "basecodes = ", basecodes
        print "registercodes = ", registercodes.lower()
        number_length = self.stat(registercodes.lower(), basecodes)
        print "number_length = ", number_length
        if number_length < 25:
            return True
        return False

    def entry_changed(self, widget):
        # print "lenth =",len(self.entry_register.get_text())
        self.tip_label.set_text("   ")
        return

    def update_thread(self, code):
        org_name = self.entry_org.get_text()
        if (org_name == None):
            org_name = ''
        org_contact = self.entry_contact.get_text()
        if (org_contact == None):
            org_contact = ''
        #print ("org = %s, contact = %s;" % (org_name, org_contact))
        r = self.updateRegcode('YES', code, org_name, org_contact)
        r = json.loads(r)
        GObject.idle_add(self.update_main_ui, r)

    def update_main_ui(self, r):
        if 'tip' in r:
            self.tip_label.set_markup(r['tip'])

        if 'title' in r:
            self.window.set_title(r['title'])

        if 'reginfo' in r:
            return

        if 'dialogMsg' in r:
            d = Gtk.MessageDialog(None, Gtk.DialogFlags.DESTROY_WITH_PARENT,
                                  Gtk.MessageType.QUESTION,
                                  Gtk.ButtonsType.YES_NO, None)
            d.set_markup("本机已注册，是否确认更新？")
            resp = d.run()
            d.destroy()
            if resp == Gtk.ResponseType.YES:
                registerThread = Thread(target=self.update_thread, args=[self.entry_register.get_text()])
                registerThread.start()
            else:
                self.register_button.handler_unblock_by_func(self.register_button_press)
        else:
            self.register_button.handler_unblock_by_func(self.register_button_press)

    def register_thread(self, code):
        org_name = self.entry_org.get_text()
        if (org_name == None):
            org_name = ''
        org_contact = self.entry_contact.get_text()
        if (org_contact == None):
            org_contact = ''
        r = self.register(code, '', org_name, org_contact)
        r = json.loads(r)
        GObject.idle_add(self.update_main_ui, r)

    def register_button_press(self, widget):
        self.register_button.handler_block_by_func(self.register_button_press)
        registerThread = Thread(target=self.register_thread, args=[self.entry_register.get_text()])
        registerThread.start()

    def register_button_press_b(self, widget):
        print "register"
        tip = ""
        # print self.entry_register.get_text()
        if len(self.entry_register.get_text()) < 1:
            self.usb_register_button_press()
            return

        if len(self.entry_register.get_text()) < 25:
            tip = "注册码错误！"
            self.tip_label.set_markup(
                "<span foreground='#DC143C' font_desc='12'>%s</span>" % (tip))
            return

        if self.check_pw(self.entry_register.get_text()):
            self.entry_register.set_text("")
            tip = "注册码含非法字符！"
            self.tip_label.set_markup(
                "<span foreground='#DC143C' font_desc='12'>%s</span>" % (tip))
            print "TRUE"
            return
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
            print self.entry_register.get_text()
            # 注册码规则检查
            if self.check_pw_compliance(self.entry_register.get_text()):
                self.entry_register.set_text("")
                tip = "请检查网络配置!(注册码规则检查不通过)"
                self.tip_label.set_markup(
                    "<span foreground='#DC143C' font_desc='12'>%s</span>" %
                    (tip))
                self.window.set_title("填写密钥(未注册)")
                return
            else:
                # self.entry_register.set_text("")
                tip = "请检查网络配置!(注册码规则检查通过)"
                self.tip_label.set_markup(
                    "<span foreground='#DC143C' font_desc='12'>%s</span>" %
                    (tip))

                # 读取用户注册信息，此部分代码可注释
                print "Read user reginfo"
                hostinfo = lib._SDK_GetHostInfo
                hostinfo.argtypes = [c_char_p, c_char_p]
                hostinfo.restype = c_char_p
                host_data = create_string_buffer("", 196)
                s3 = hostinfo(self.entry_register.get_text(), host_data)
                print "reginfo:", host_data.value

                # 保存用户注册信息
                fp = open("/usr/share/registerclient/reginfo", "w")
                reginfo_tmp = base64.encodestring(host_data.value)  # 保存所有注册信息
                # reginfo_tmp = base64.encodestring(self.entry_register.get_text()) #仅保存regcode信息
                fp.write(reginfo_tmp)
                fp.close()
                print reginfo_tmp

                self.entry_register.set_text("")

                # 更新status.ini文件
                fp = open("/usr/share/registerclient/status.ini", "r")
                regstatus_tmp = fp.read()  # read file all content
                statuslist = base64.decodestring(regstatus_tmp).split()
                statuslistlen = len(statuslist)  # status list length
                if statuslistlen >= 2 and statuslist[0] == "1" and cmp(
                        statuslist[1], "NoRegister") != 0:
                    os.system(
                        "cp /usr/share/registerclient/status.ini /usr/share/registerclient/status-bak.ini"
                    )
                fp.close()
                fp = open("/usr/share/registerclient/status.ini", "w")
                writestatus = base64.encodestring("1 NoRegister")
                fp.write(writestatus)
                fp.close()
                fp = open("/usr/share/registerclient/status.ini", "r")
                regstatus_temp = fp.read()  # read file all content
                regstatus = base64.decodestring(regstatus_temp)
                statuslist = regstatus.split()  # status list
                statuslistlen = len(statuslist)  # status list length
                print statuslist[0]
                if statuslist[0] == "1":
                    if statuslistlen >= 2:
                        mesg = statuslist[1]
                    print mesg
                    self.window.set_title("注册码已通过规则检查")
                else:
                    self.window.set_title("注册码已通过规则检查")
                fp.close()
                # 断网情况下，无需执行registerafter.sh
                # os.system("/usr/share/registerclient/registerafter.sh")

        else:
            # if self.entry_register.get_text() == "":
            #   print "NULL register"
            #   tip = "注册码为空！"
            # self.tip_label.set_markup("<span foreground='#8A2BE2' font_desc='12'>%s</span>"%("注册码为空！"))
            # else:
            self.entry_register.get_text()
            lib._SDK_DoRegister.restype = POINTER(StructPointer)
            print "in"
            get_data = lib._SDK_DoRegister(self.entry_register.get_text(), self.entry_org.get_text(), self.entry_contact.get_text())
            print "out"
            # status = lib._SDK_GetRegisterInfo(self.entry_register.get_text())
            print get_data.contents.SC_RespCode
            #      get_data.contents.SC_RespCode = 201
            if get_data.contents.SC_RespCode == 201:
                tip = "注册成功！"
                # self.tip_label.set_markup("<span foreground='#8A2BE2' font_desc='12'>%s</span>"%("注册成功！"))
                fp = open("/usr/share/registerclient/status.ini", "w")
                writestatus_temp = "1 " + get_data.contents.SC_ValidTime
                writestatus = base64.encodestring(writestatus_temp)
                # fp.write("1 "+get_data.contents.SC_ValidTime)
                fp.write(writestatus)
                fp.close()
                os.system(
                    "echo > /usr/share/registerclient/reginfo")  #clear reginfo
                print get_data.contents.SC_RespInfo
                fp = open("/usr/share/registerclient/status.ini", "r")
                # status = fp.read(1)
                regstatus_temp = fp.read()  # read file all content
                regstatus = base64.decodestring(regstatus_temp)
                statuslist = regstatus.split()  # status list
                statuslistlen = len(statuslist)  # status list length
                #  fp.readline()#'\n'
                print statuslist[0]
                if statuslist[0] == "1":
                    # fp.seek(1,1)
                    # time = fp.read(10)
                    if statuslistlen >= 2:
                        time = statuslist[1]
                    print time
                    self.window.set_title("填写密钥(已注册 到期时间" + time + ")")
                else:
                    self.window.set_title("填写密钥(未注册)")
                fp.close()
                os.system("/usr/share/registerclient/registerafter.sh")
            else:
                if get_data.contents.SC_RespCode == 302:
                    d = Gtk.MessageDialog(None,
                                          Gtk.DialogFlags.DESTROY_WITH_PARENT,
                                          Gtk.MessageType.QUESTION,
                                          Gtk.ButtonsType.YES_NO, None)
                    d.set_markup("本机已注册，是否确认更新？")
                    resp = d.run()
                    d.destroy()
                    tip = ""
                    if resp == Gtk.ResponseType.YES:
                        print 'yes'
                        lib._SDK_ConfirmRegister.restype = POINTER(
                            StructPointer)
                        get_data = lib._SDK_ConfirmRegister(
                            self.entry_register.get_text())
                        tip = "更新成功"
                        fp = open("/usr/share/registerclient/status.ini", "w")
                        writestatus_temp = "1 " + get_data.contents.SC_ValidTime
                        writestatus = base64.encodestring(writestatus_temp)
                        # fp.write("1 "+get_data.contents.SC_ValidTime)
                        fp.write(writestatus)
                        fp.close()
                        os.system("echo > /usr/share/registerclient/reginfo"
                                  )  # clear reginfo
                        print get_data.contents.SC_RespInfo
                        fp = open("/usr/share/registerclient/status.ini", "r")
                        # status = fp.read(1)
                        regstatus_temp = fp.read()  # read file all content
                        regstatus = base64.decodestring(regstatus_temp)
                        statuslist = regstatus.split()  # status list
                        statuslistlen = len(statuslist)  # status list length
                        # fp.readline()#'\n'
                        print statuslist[0]
                        if statuslist[0] == "1":
                            # fp.seek(1,1)
                            # time = fp.read(10)
                            if statuslistlen >= 2:
                                time = statuslist[1]
                            print time
                            self.window.set_title("填写密钥(已注册 到期时间" + time + ")")
                        else:
                            self.window.set_title("填写密钥(未注册)")
                        fp.close()
                        os.system("/usr/share/registerclient/registerafter.sh")
                        # self.tip_label.set_markup("<span foreground='#8A2BE2' font_desc='12'>%s</span>"%("更新成功！"))
                    else:
                        print 'no'
                elif get_data.contents.SC_RespCode == 202:
                    tip = "本机已使用此码注册！"
                    fp = open("/usr/share/registerclient/status.ini", "w")
                    writestatus_temp = "1 " + get_data.contents.SC_ValidTime
                    writestatus = base64.encodestring(writestatus_temp)
                    # fp.write("1 "+get_data.contents.SC_ValidTime)
                    fp.write(writestatus)
                    # fp.write("1 2015-09-18")
                    fp.close()
                    print get_data.contents.SC_RespInfo
                    fp = open("/usr/share/registerclient/status.ini", "r")
                    # status = fp.readline(1)
                    regstatus_temp = fp.read()  # read file all content
                    regstatus = base64.decodestring(regstatus_temp)
                    statuslist = regstatus.split()  # status list
                    statuslistlen = len(statuslist)  # status list length
                    # fp.readline()#'\n'
                    print statuslist[0]
                    if statuslist[0] == "1":
                        # fp.seek(1,1)
                        # time = fp.read(10)
                        if statuslistlen >= 2:
                            time = statuslist[1]
                        print time
                        self.window.set_title("填写密钥(已注册 到期时间" + time + ")")
                    else:
                        self.window.set_title("填写密钥(未注册)")
                    fp.close()
                    os.system("/usr/share/registerclient/registerafter.sh")

                elif get_data.contents.SC_RespCode == 400:
                    tip = "注册失败！"
                    # self.tip_label.set_markup("<span foreground='#8A2BE2' font_desc='12'>%s</span>"%("注册失败！"))
                    print get_data.contents.SC_RespInfo
                elif get_data.contents.SC_RespCode == 401:
                    print get_data.contents.SC_RespInfo
                    tip = "注册码已注册！"
                elif get_data.contents.SC_RespCode == 402:
                    print get_data.contents.SC_RespInfo
                elif get_data.contents.SC_RespCode == 405:
                    # 下方代码是否需要？
                    if self.check_pw_compliance(
                            self.entry_register.get_text()):
                        self.entry_register.set_text("")
                        tip = "请检查网络配置!(注册码规则检查不通过)"
                        self.tip_label.set_markup(
                            "<span foreground='#DC143C' font_desc='12'>%s</span>"
                            % (tip))
                        print "TRUE"
                        self.window.set_title("填写密钥(未注册)")
                        return
                    else:
                        self.entry_register.set_text("")
                        tip = "请检查网络配置!(注册码规则检查通过)"
                        self.tip_label.set_markup(
                            "<span foreground='#DC143C' font_desc='12'>%s</span>"
                            % (tip))
                        print "FALSE"
                        fp = open("/usr/share/registerclient/status.ini", "w")
                        writestatus = base64.encodestring("1 NoRegister")
                        # fp.write("1 NoRegister")
                        fp.write(writestatus)
                        fp.close()
                        print get_data.contents.SC_RespInfo
                        fp = open("/usr/share/registerclient/status.ini", "r")
                        # status = fp.read(1)
                        regstatus_temp = fp.read()  # read file all content
                        regstatus = base64.decodestring(regstatus_temp)
                        statuslist = regstatus.split()  # status list
                        statuslistlen = len(statuslist)  # status list length
                        print statuslist[0]
                        if statuslist[0] == "1":
                            # fp.seek(1,1)
                            # mesg = fp.read(10)
                            if statuslistlen >= 2:
                                mesg = statuslist[1]
                            print mesg
                            self.window.set_title("注册码已通过规则检查")
                        else:
                            self.window.set_title("注册码已通过规则检查")
                        fp.close()
                        os.system("/usr/share/registerclient/registerafter.sh")
                    # tip = "服务器无响应！"
                    # tip = "请检查网络！信息已保存！"
                    # self.tip_label.set_markup("<span foreground='#8A2BE2' font_desc='12'>%s</span>"%("服务器无响应！"))
                    print get_data.contents.SC_RespInfo
        self.tip_label.set_markup(
            "<span foreground='#DC143C' font_desc='12'>%s</span>" % (tip))
        # self.tip_label.set_markup("<span foreground='#8A2BE2' font_desc='12'>%s</span>"%(tip))
        # self.tip_label.show()
        return

if __name__ == "__main__":
    RegistedWindow()
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    Gtk.main()