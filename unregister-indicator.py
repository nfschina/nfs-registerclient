#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
import os
import signal
import base64
import datetime
import gi
import dbus
gi.require_version('Gtk', '3.0')
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, GObject, Gio, GLib
from gi.repository import Gdk

CURRPATH = os.path.dirname(os.path.realpath(__file__))
STATUS_FILE = CURRPATH + "/status.ini"

def is_cdrom():
    try:
        fp = open("/proc/cmdline", "r")
        cmdline = fp.read()
        fp.close()
        print cmdline
        if "file=/cdrom" not in cmdline:
            return False
        else:
            return True
    except:
        return True

class TrayIndicator(object):
    def __init__(self):
        self.state = False
        self.menu = None
        #是否过期
        self.past_due = False
        self.check_state()

    def load(self):
        #icon:unregistered.png
        if (self.state == True and self.past_due == False):
            return
        if (self.past_due == True):
            tooltip = "注册已过期,请重新注册"
            icon_name = "past-due"
        else:
            tooltip = "未注册用户"
            icon_name = "unregistered"
        self.indicator = Gtk.StatusIcon.new_from_icon_name(icon_name)
        self.indicator.set_tooltip_text(tooltip)
        self.indicator.set_name("unregistered")
        self.indicator.set_title("unregistered")
        self.indicator.set_visible(True)
        self.indicator.connect("activate", self.on_activate)
        self.indicator.connect("popup-menu", self.build_menu)
        #监听状态文件,响应注册状态的变化
        self.file = Gio.File.new_for_path(STATUS_FILE)
        self.file_monitor = Gio.File.monitor_file(self.file, Gio.FileMonitorFlags.NONE, None)
        self.file_monitor.connect("changed", self.may_status_on_changed)

    def may_status_on_changed(self, monitor, file, other_file, event_type):
        self.check_state()
        if (self.state):
             sys.exit(0)

    def on_activate(self, status_icon):
        self.open_client()

    def item_on_activate(self, item):
        self.open_client()

    def open_client(self):
        cmd = os.path.expanduser("registerclient-launcher")
        display = Gdk.Display.get_default()
        timestamp = Gtk.get_current_event_time()
        context = display.get_app_launch_context()
        context.set_timestamp(timestamp)
        appinfo = Gio.AppInfo.create_from_commandline(cmd, "Register Client", Gio.AppInfoCreateFlags.NONE)
        launched = appinfo.launch(None, context)
        return launched

    def build_menu(self, status_icon, button, time):
        if (button == 3 and self.menu == None):
            self.menu = Gtk.Menu()
            item = Gtk.MenuItem("现在注册")
            item.connect("activate", self.item_on_activate)
            self.menu.append(item)
        self.menu.show_all()
        self.menu.popup(None, None, status_icon.position_menu, status_icon, button, time)

    def check_state(self):
        fp = open(STATUS_FILE, "r")
        regstatus = fp.read()
        regstatus = base64.decodestring(regstatus)
        statuslist = regstatus.split()
        statuslistlen = len(statuslist)
        if statuslist[0] == "1":
            self.state = True
            if statuslistlen >= 2:
                time = statuslist[1]
                if cmp(time,"NoRegister")!=0:
                    timeObjet = datetime.datetime.strptime(time, '%Y-%m-%d')
                    if datetime.datetime.today() > timeObjet:
                        self.past_due = True
                    else:
                        self.past_due = False
        else:
            self.state = False
        fp.close()

if __name__ == "__main__":
    if is_cdrom():
        sys.exit(0)
    system_bus = dbus.SystemBus()
    nfsmount = system_bus.get_object('com.nfs.register', '/')
    iface = dbus.Interface(nfsmount, dbus_interface='com.nfs.register')
    check_register = iface.get_dbus_method("check_register", dbus_interface=None)
    if check_register():
        sys.exit(0)
    indicator = TrayIndicator()
    if (indicator.state == False or indicator.past_due == True):
        indicator.load()
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        Gtk.main()
    else :
        sys.exit(0)