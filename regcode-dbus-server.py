#!/usr/bin/python
# -*- coding: utf-8 -*-

# import sys
import os
import signal
import base64
import datetime
import json

import dbus
import dbus.mainloop.glib
import dbus.service
import pycurl
import hashlib
from ctypes import Structure
from ctypes import c_char
from ctypes import c_char_p
from ctypes import c_long
from ctypes import cdll
from ctypes import create_string_buffer
from ctypes import POINTER
# from dbus.mainloop.glib import DBusGMainLoop
# from gi.repository import GObject
from gi.repository import GLib
from pysqlcipher3 import dbapi2 as sqlite
from threading import Thread

lib = cdll.LoadLibrary('/usr/lib/libSDK_VerifyRegister.so')

INTERFACE = 'com.nfs.register'
PATH = '/'
STATUS_FILE = '/usr/share/registerclient/status.ini'

def get_safe_id():
    safeid = lib._SKD_GetSafeID
    safeid.argtypes = [c_char_p]
    safeid.restype = c_char_p
    safe_id = create_string_buffer("", 1960)
    # s3 = hostinfo(code, host_data)
    safeid(safe_id)
    return safe_id.value

def check_regcode(code):
    lib._SDK_Encode.argtypes = [c_char_p, c_char_p]
    lib._SDK_Encode.restype = c_char_p
    safe_id = get_safe_id()
    hexdigest = lib._SDK_Encode(code[0:12], safe_id).upper()
    check_str = code[12:20]
    print "correct code:"
    print code[0:12] + hexdigest[-8:]
    if hexdigest[-8:] == check_str:
        return True
    return False

def get_validperiod(code):
    tmp_str = code[8:12]
    print tmp_str
    validperiod = (ord(code[8]) - 80) * 1000 + (ord(code[9]) - 80) * 100 + (ord(code[10]) - 80) * 10 + ord(code[11]) - 80
    print validperiod
    return validperiod


class StructPointer(Structure):
    """
    """
    _fields_ = [("SC_RespInfo", c_char * 64), ("SC_ValidTime", c_char * 20),
                ("SC_RespCode", c_long)]


class DbusDaemon(dbus.service.Object):
    """
    """

    def __init__(self, mainloop=None):
        print 'run dbus\n'
        self.mainloop = mainloop
        bus_loop = dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        bus = dbus.SystemBus(mainloop=bus_loop)
        bus_name = dbus.service.BusName(INTERFACE, bus)
        dbus.service.Object.__init__(self, bus_name, PATH)
        signal.signal(signal.SIGINT, lambda: mainloop.quit())
        print INTERFACE

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

        number_length = letters + digit
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

    @dbus.service.signal(dbus_interface=INTERFACE, signature='s')
    def register_single(self, msg):
        pass

    def register_after(self, msg='register'):
        # os.system("/usr/share/registerclient/registerafter.sh")
        self.register_single(msg)
        pass

    @dbus.service.method(INTERFACE, in_signature='', out_signature='')
    def exit(self):
        self.mainloop.quit()
        pass

    @dbus.service.method(INTERFACE, in_signature='ss', out_signature='iis')
    def getRegisterStatus(self, product, version):
        if product == 'os':
            print os
            fp = open(STATUS_FILE, "r")
            regstatus_temp = fp.read()
            regstatus = base64.decodestring(regstatus_temp)
            statuslist = regstatus.split()
            statuslistlen = len(statuslist)
            if statuslistlen >= 2:
                if statuslist[0] == "1":
                    d1 = datetime.datetime.strptime(statuslist[1], '%Y-%m-%d')
                    d2 = datetime.datetime.now()
                    day = (d1 - d2).days
                    return (1, day, statuslist[1])
            else:
                return (0, 0, '')
        pass

    @dbus.service.method(INTERFACE, in_signature='ssss', out_signature='s')
    def updateRegcode(self, resp, code, org_name, org_contact):
        r = {}
        if resp == 'YES':
            if (org_name == ''):
                org_name = None
            if (org_contact == ''):
                org_contact = None
            code = str(code)
            lib._SDK_ConfirmRegister.restype = POINTER(StructPointer)
            get_data = lib._SDK_ConfirmRegister(code, org_name, org_contact)
            r['tip'] = "<span foreground='#8A2BE2' font_desc='12'>%s</span>" % (
                "更新成功！")
            fp = open("/usr/share/registerclient/status.ini", "w")
            writestatus_temp = "1 " + get_data.contents.SC_ValidTime + " " + code
            writestatus = base64.encodestring(writestatus_temp)
            fp.write(writestatus)
            fp.close()
            # clear reginfo
            os.system("echo > /usr/share/registerclient/reginfo")
            fp = open("/usr/share/registerclient/status.ini", "r")
            # status = fp.read(1)
            regstatus_temp = fp.read()  # read file all content
            regstatus = base64.decodestring(regstatus_temp)
            statuslist = regstatus.split()  # status list
            statuslistlen = len(statuslist)  # status list length
            # fp.readline()#'\n'
            print statuslist[0]
            if statuslist[0] == "1":
                if statuslistlen >= 2:
                    time = statuslist[1]
                r['title'] = "填写密钥(已更新 到期时间" + time + ")"
                registerafterThread = Thread(target=self.register_after, args=['update'])
                registerafterThread.start()
            else:
                r['title'] = "填写密钥(未注册)"
            fp.close()

        return json.dumps(r)

    def find_usb_storage(self):
        comm = 'find /media -maxdepth 3 -type d -name nfs-register-code 2>/dev/null'
        db_file_dir = os.popen(comm).readlines()
        comm = 'find ' + db_file_dir[0].strip() + ' -maxdepth 3 -type f -name "*.db" 2>/dev/null'
        db_file_list = os.popen(comm).readlines()
        return db_file_list

    def get_unused_register_code(self):
        for db_file in self.find_usb_storage():
            db_file = db_file.strip()
            if not db_file:
                tip = 'not fount db file'
                print tip
                raise Exception(tip)
            conn = sqlite.connect(db_file)
            c = conn.cursor()
            c.execute("PRAGMA key='qwe123'")
            c.execute(
                'select * from register_code where hdserial is null limit 0,1')
            values = c.fetchall()
            conn.commit()
            c.close()
            if len(values) > 0:
                self.db_file = db_file
                return values[0][0]

        return None

    def get_hdserial(self):
        hdserial = os.popen(
            "find /sys/devices/ -type f| grep -v virtual | xargs grep 'DEVTYPE=disk' 2>/dev/null | awk -F'/uevent' '{print $1}'| xargs -I {} echo {}/../../ 2>/dev/null | xargs -I {} find {} -type f | grep 'wwid\|serial' |xargs cat 2>/dev/null| awk -F' ' '{print $NF}' | head -n1"
        ).readlines()
        if not hdserial:
            hdserial = os.popen(
                "smartctl -i /dev/nvme0n1 | grep \"Serial Number:\" | awk '{print $3}'"
            ).readlines()
        return hdserial[0].strip()

    def get_osuuid(self):
        osuuid = os.popen("dmidecode -s system-uuid").readlines()
        return osuuid[0].strip()

    def get_osserialnumber(self):
        print "get_osserialnumber----"
        osserialnumber = os.popen("dmidecode -s system-serial-number").readlines()
        return osserialnumber[0].strip()

    def get_osrelease(self):
        version = os.popen(
            "cat /etc/os-release | grep ^VERSION_ID").readlines()
        version = version[0].split('=')
        return version[1].strip().strip('"')

    def register_code_in_usb(self, code):
        db_file = self.db_file
        conn = sqlite.connect(db_file)
        c = conn.cursor()
        c.execute("PRAGMA key='qwe123'")
        createdate = datetime.datetime.now().strftime("%Y-%m-%d")

        sql = "%s createdate = '%s', hdserial = '%s', osuuid = '%s', osrelease = '%s', osserialnumber = '%s' WHERE  regcode = '%s'" % (
            'UPDATE register_code SET ', createdate, self.get_hdserial(),
            self.get_osuuid(), self.get_osrelease(), self.get_osserialnumber(), code)
        c.execute(sql)
        print sql

        conn.commit()
        c.close()

    def delete_register_code(self, code):
        db_file = self.db_file
        conn = sqlite.connect(db_file)
        c = conn.cursor()
        c.execute("PRAGMA key='qwe123'")
        createdate = datetime.datetime.now().strftime("%Y-%m-%d")

        sql = "%s createdate = '%s', hdserial = '%s', osuuid = '%s', osrelease = '%s' WHERE  regcode = '%s'" % (
            'UPDATE register_code SET ', createdate, self.get_hdserial(),
            self.get_osuuid(), self.get_osrelease(), code)
        c.execute(sql)
        print sql

        conn.commit()
        c.close()

    def usb_registor_button_press(self):
        r = {}
        fp = open("/usr/share/registerclient/status.ini", "r")
        regstatus_temp = fp.read()  # read file all content
        regstatus = base64.decodestring(regstatus_temp)
        statuslist = regstatus.split()  # status list
        statuslistlen = len(statuslist)  # status list length
        print statuslist[0]
        if statuslist[0] == "1":
            if statuslistlen >= 2:
                time = statuslist[1]
                if cmp(time, "NoRegister") == 0:
                    r['NoRegister'] = True
                else:
                    time = statuslist[1]
                    time = datetime.datetime.strptime(time, '%Y-%m-%d')
                    if datetime.datetime.today() > time:
                        pass
                    else:
                        tip = "此产品已经完成注册，无需再次注册！"
                        r['tip'] = "<span foreground='#8A2BE2' font_desc='12'>%s</span>" % (
                            tip)
                        return json.dumps(r)

        code = None
        try:
            code = self.get_unused_register_code()
        except Exception:
            print 'Exception'
            tip = "注册码失败，未输入注册码且未在u盘中发现可用注册码！"
            r['tip'] = "<span foreground='#DC143C' font_desc='12'>%s</span>" % (
                tip)
        print code
        if code is not None:
            if self.check_pw_compliance(code):
                tip = "注册码错误,请联系注册码发售商！"
                r['tip'] = "<span foreground='#DC143C' font_desc='12'>%s</span>" % (
                    tip)
                r['exp'] = True
                return json.dumps(r)
            else:
                self.register_code_in_usb(code)
                fp = open("/usr/share/registerclient/status.ini", "w")
                writestatus_temp = "1 NoRegister " + code
                # writestatus_temp = "1 " + (
                #     datetime.datetime.now() +
                #     datetime.timedelta(days=360)).strftime("%Y-%m-%d")
                writestatus = base64.encodestring(writestatus_temp)
                # fp.write("1 "+get_data.contents.SC_ValidTime)
                fp.write(writestatus)
                fp.close()

                fp = open("/usr/share/registerclient/unregist_code", "w")
                writecode = base64.encodestring(code)
                fp.write(writecode)
                fp.close()
                
                print "Read user reginfo"
                hostinfo = lib._SDK_GetHostInfo
                hostinfo.argtypes = [c_char_p, c_char_p]
                hostinfo.restype = c_char_p
                host_data = create_string_buffer("", 1960)
                # s3 = hostinfo(code, host_data)
                hostinfo(code, host_data)
                print "reginfo:", host_data.value

                # 保存用户注册信息
                fp = open("/usr/share/registerclient/reginfo", "w")
                reginfo_tmp = base64.encodestring(host_data.value)  # 保存所有注册信息
                fp.write(reginfo_tmp)
                fp.close()
                print reginfo_tmp

                r['reginfo'] = True

                # os.system("echo > /usr/share/registerclient/reginfo"
                #           )  # clear reginfo

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
                        r['title'] = "填写密钥(已注册)"
                        tip = "注册成功！"
                        r['tip'] = "<span foreground='#8A2BE2' font_desc='12'>%s</span>" % (
                            tip)
                        registerafterThread = Thread(target=self.register_after)
                        registerafterThread.start()
                else:
                    r['title'] = "填写密钥(未注册)"
                fp.close()
                # os.system("/usr/share/registerclient/registerafter.sh")
        else:
            tip = "注册码失败，未输入注册码且未在u盘中发现可用注册码！"
            r['tip'] = "<span foreground='#DC143C' font_desc='12'>%s</span>" % (
                tip)
        return json.dumps(r)

    @dbus.service.method(INTERFACE, in_signature='', out_signature='b')
    def check_register(self):
        print "check_register"
        #if os.system('ping -c 2 -W 2 nisc.nfschina.com'):
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
            return False
        else:
            lib._SDK_CheckRegister.restype = POINTER(StructPointer)
            get_data = lib._SDK_CheckRegister()
            print "SC_RespCode"
            print get_data.contents.SC_RespCode
            if get_data.contents.SC_RespCode == 400:
                print "check result: not register"
                # fp = open("/usr/share/registerclient/status.ini", "w")
                # writestatus_temp = "0"
                # writestatus = base64.encodestring(writestatus_temp)
                # fp.write(writestatus)
                # fp.close()
                return False
            if get_data.contents.SC_RespCode == 202:
                print get_data.contents.SC_RespInfo
                print get_data.contents.SC_ValidTime
                fp = open("/usr/share/registerclient/status.ini", "w")
                writestatus_temp = "1 " + get_data.contents.SC_ValidTime + " " + get_data.contents.SC_RespInfo
                writestatus = base64.encodestring(writestatus_temp)
                fp.write(writestatus)
                fp.close()
                return True
            return False


    @dbus.service.method(INTERFACE, in_signature='ssss', out_signature='s')
    def register(self, code, p, org_name, org_contact):
        r = {}
        if not code or len(code) < 1:
            # self.usb_registor_button_press()
            return self.usb_registor_button_press()

        if len(code) == 20:
            if check_regcode(code):
                validperiod = get_validperiod(code)
                valid_date = datetime.datetime.now() + datetime.timedelta(days=validperiod)
                print valid_date
                tip = "注册成功！"
                r['tip'] = "<span foreground='#DC143C' font_desc='12'>%s</span>" % (tip)
                fp = open("/usr/share/registerclient/status.ini", "w")
                #writestatus_temp = "1 " + "NoRegister" + " " + code
                writestatus_temp = "1 " + str(valid_date)[:10] + " " + code + " NoRegister"
                writestatus = base64.encodestring(writestatus_temp)
                fp.write(writestatus)
                fp.close()
                hostinfo = lib._SDK_GetHostInfo
                hostinfo.argtypes = [c_char_p, c_char_p]
                hostinfo.restype = c_char_p
                host_data = create_string_buffer("", 1960)
                # s3 = hostinfo(code, host_data)
                hostinfo(code, host_data)
                print "reginfo:", host_data.value

                # 保存用户注册信息
                fp = open("/usr/share/registerclient/reginfo", "w")
                final_info = host_data.value + "&valid_period=" + str(validperiod)
                reginfo_tmp = base64.encodestring(final_info)  # 保存所有注册信息
                fp.write(reginfo_tmp)
                fp.close()
                return json.dumps(r)

        if len(code) < 25:
            tip = "注册码错误！"
            r['tip'] = "<span foreground='#DC143C' font_desc='12'>%s</span>" % (
                tip)
            return json.dumps(r)

        if self.check_pw(code):
            r['text'] = ''
            tip = "注册码含非法字符！"
            r['tip'] = "<span foreground='#DC143C' font_desc='12'>%s</span>" % (
                tip)
            print "TRUE"
            return json.dumps(r)
        #if os.system('ping -c 2 -W 2 nisc.nfschina.com'):
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
            print code
            if self.check_pw_compliance(code):
                r['text'] = ''
                tip = "请检查网络配置!(注册码规则检查不通过)"
                r['tip'] = "<span foreground='#DC143C' font_desc='12'>%s</span>" % (
                    tip)
                r['title'] = "填写密钥(未注册)"
                return json.dumps(r)
            else:
                tip = "请检查网络配置!(注册码规则检查通过)"
                r['tip'] = "<span foreground='#DC143C' font_desc='12'>%s</span>" % (
                    tip)

                print "Read user reginfo"
                hostinfo = lib._SDK_GetHostInfo
                hostinfo.argtypes = [c_char_p, c_char_p]
                hostinfo.restype = c_char_p
                host_data = create_string_buffer("", 1960)
                # s3 = hostinfo(code, host_data)
                hostinfo(code, host_data)
                print "reginfo:", host_data.value

                # 保存用户注册信息
                fp = open("/usr/share/registerclient/reginfo", "w")
                reginfo_tmp = base64.encodestring(host_data.value)  # 保存所有注册信息
                fp.write(reginfo_tmp)
                fp.close()
                print reginfo_tmp

                r['text'] = ''

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
                writestatus = base64.encodestring("1 NoRegister " + code)
                fp.write(writestatus)
                fp.close()
                fp = open("/usr/share/registerclient/unregist_code", "w")
                writecode = base64.encodestring(code)
                fp.write(writecode)
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
                    r['title'] = "注册码已通过规则检查"
                else:
                    r['title'] = "注册码已通过规则检查"
                fp.close()
        else:
            lib._SDK_DoRegister.restype = POINTER(StructPointer)
            code = str(code)
            get_data = lib._SDK_DoRegister(code, org_name, org_contact)

            print get_data.contents.SC_RespCode
            #      get_data.contents.SC_RespCode = 201
            if get_data.contents.SC_RespCode == 201:
                tip = "注册成功！"
                r['tip'] = "<span foreground='#DC143C' font_desc='12'>%s</span>" % (
                    tip)
                # self.tip_label.set_markup("<span foreground='#8A2BE2' font_desc='12'>%s</span>"%("注册成功！"))
                fp = open("/usr/share/registerclient/status.ini", "w")
                writestatus_temp = "1 " + get_data.contents.SC_ValidTime + " " + code
                writestatus = base64.encodestring(writestatus_temp)
                # fp.write("1 "+get_data.contents.SC_ValidTime)
                fp.write(writestatus)
                fp.close()
                # clear reginfo
                os.system("echo > /usr/share/registerclient/reginfo")
                print get_data.contents.SC_RespInfo
                fp = open("/usr/share/registerclient/status.ini", "r")
                # status = fp.read(1)
                regstatus_temp = fp.read()  # read file all content
                regstatus = base64.decodestring(regstatus_temp)
                statuslist = regstatus.split()  # status list
                statuslistlen = len(statuslist)  # status list length
                print statuslist[0]
                if statuslist[0] == "1":
                    if statuslistlen >= 2:
                        time = statuslist[1]
                    print time
                    r['title'] = "填写密钥(已注册 到期时间" + time + ")"
                    registerafterThread = Thread(target=self.register_after)
                    registerafterThread.start()
                else:
                    r['title'] = "填写密钥(未注册)"
                fp.close()
                # os.system("/usr/share/registerclient/registerafter.sh")
            else:
                if get_data.contents.SC_RespCode == 302:
                    # d = Gtk.MessageDialog(None,
                    #                       Gtk.DialogFlags.DESTROY_WITH_PARENT,
                    #                       Gtk.MessageType.QUESTION,
                    #                       Gtk.ButtonsType.YES_NO, None)
                    # d.set_markup("本机已注册，是否确认更新？")
                    # resp = d.run()
                    # d.destroy()
                    r['dialogMsg'] = '本机已注册，是否确认更新？'
                    r['tip'] = ""
                    # if resp == Gtk.ResponseType.YES:
                    #     print 'yes'
                    #     lib._SDK_ConfirmRegister.restype = POINTER(
                    #         StructPointer)
                    #     get_data = lib._SDK_ConfirmRegister(
                    #         self.entry_registor.get_text())
                    #     tip = "更新成功"
                    #     fp = open("/usr/share/registerclient/status.ini", "w")
                    #     writestatus_temp = "1 " + get_data.contents.SC_ValidTime
                    #     writestatus = base64.encodestring(writestatus_temp)
                    #     fp.write(writestatus)
                    #     fp.close()
                    #     # clear reginfo
                    #     os.system("echo > /usr/share/registerclient/reginfo")
                    #     print get_data.contents.SC_RespInfo
                    #     fp = open("/usr/share/registerclient/status.ini", "r")
                    #     #status = fp.read(1)
                    #     regstatus_temp = fp.read()  # read file all content
                    #     regstatus = base64.decodestring(regstatus_temp)
                    #     statuslist = regstatus.split()  # status list
                    #     statuslistlen = len(statuslist)  # status list length
                    #     # fp.readline()#'\n'
                    #     print statuslist[0]
                    #     if statuslist[0] == "1":
                    #         # fp.seek(1,1)
                    #         #time = fp.read(10)
                    #         if statuslistlen == 2:
                    #             time = statuslist[1]
                    #         print time
                    #         self.window.set_title("填写密钥(已注册 到期时间" + time + ")")
                    #     else:
                    #         self.window.set_title("填写密钥(未注册)")
                    #     fp.close()
                    #     os.system("/usr/share/registerclient/registerafter.sh")
                    #     # self.tip_label.set_markup("<span foreground='#8A2BE2' font_desc='12'>%s</span>"%("更新成功！"))
                    # else:
                    #     print 'no'
                elif get_data.contents.SC_RespCode == 202:
                    tip = "本机已使用此码注册！"
                    r['tip'] = "<span foreground='#DC143C' font_desc='12'>%s</span>" % (
                        tip)
                    fp = open("/usr/share/registerclient/status.ini", "w")
                    writestatus_temp = "1 " + get_data.contents.SC_ValidTime + " " + get_data.contents.SC_RespInfo
                    #writestatus_temp = "1 " + get_data.contents.SC_ValidTime
                    writestatus = base64.encodestring(writestatus_temp)
                    # fp.write("1 "+get_data.contents.SC_ValidTime)
                    fp.write(writestatus)
                    # fp.write("1 2015-09-18")
                    fp.close()
                    print writestatus_temp
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
                        r['title'] = "填写密钥(已注册 到期时间" + time + ")"
                        registerafterThread = Thread(target=self.register_after)
                        registerafterThread.start()
                    else:
                        r['title'] = "填写密钥(未注册)"
                    fp.close()
                    # os.system("/usr/share/registerclient/registerafter.sh")

                elif get_data.contents.SC_RespCode == 400:
                    tip = '注册失败！'
                    r['tip'] = "<span foreground='#DC143C' font_desc='12'>%s</span>" % (
                        tip)
                    print get_data.contents.SC_RespInfo
                elif get_data.contents.SC_RespCode == 401:
                    print get_data.contents.SC_RespInfo
                    tip = "注册码已注册！"
                    r['tip'] = "<span foreground='#DC143C' font_desc='12'>%s</span>" % (
                        tip)
                elif get_data.contents.SC_RespCode == 402:
                    print get_data.contents.SC_RespInfo
                elif get_data.contents.SC_RespCode == 405:
                    if self.check_pw_compliance(code):
                        r['text'] = ''
                        tip = "请检查网络配置!(注册码规则检查不通过)"
                        r['tip'] = "<span foreground='#DC143C' font_desc='12'>%s</span>" % (
                            tip)
                        print "TRUE"
                        r['title'] = "填写密钥(未注册)"
                        return json.dumps(r)
                    else:
                        r['text'] = ""
                        tip = "请检查网络配置!(注册码规则检查通过)"
                        r['tip'] = "<span foreground='#DC143C' font_desc='12'>%s</span>" % (
                            tip)
                        print "FALSE"
                        fp = open("/usr/share/registerclient/status.ini", "w")
                        writestatus = base64.encodestring("1 NoRegister")
                        fp.write(writestatus)
                        fp.close()
                    print get_data.contents.SC_RespInfo
        # r['tip'] = "<span foreground='#DC143C' font_desc='12'>%s</span>" % (tip)
        return json.dumps(r)


if __name__ == '__main__':
    os.environ[
        "PATH"] = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/X11R6/bin"
    loop = GLib.MainLoop()
    DbusDaemon(loop)
    loop.run()
