Name: registerclient

Version: 1.01

Release: 3nfs33.1%{?dist}

Summary: compiled from 1.01+3nfs33 by wqx

Group: System Environment/Daemons

License: GPL

URL: http://www.nfs.com

Source0: registerclient-1.01.tar.xz

Patch0:  0001-usb-register.patch

BuildRoot: %(mktemp -ud %{_tmppath}/%{name}-%{version}-%{release}-XXXXXX)

BuildRequires: gcc, gcc-c++, smartmontools, python2

Requires:pygobject3-base dbus-python python2-requests python2-notify

%description

register client. Compiled by wqx

%prep

%setup -q

%patch0 -p1

%define debug_package %{nil}

%build
/usr/bin/python2 -m compileall -f -q ./

%install
mkdir -p %{buildroot}/usr/bin
mkdir -p %{buildroot}/lib64
mkdir -p %{buildroot}/usr/share/applications
mkdir -p %{buildroot}/usr/share/registerclient/pixmaps
mkdir -p %{buildroot}/usr/lib64/python2.7/site-packages/pysqlcipher3
mkdir -p %{buildroot}/usr/lib64/registerclient
mkdir -p %{buildroot}/etc/dbus-1/system.d
mkdir -p %{buildroot}/usr/share/dbus-1/system-services
mkdir -p %{buildroot}/usr/share/icons
mkdir -p %{buildroot}/etc/xdg/autostart
chmod a+x clientdisplay.pyc
cp -a clientdisplay.pyc %{buildroot}/usr/bin/
cp -a configure_file/registerclient.desktop %{buildroot}/usr/share/applications
chmod a+x configure_file/registerclient-launcher
cp -a configure_file/registerclient-launcher %{buildroot}/usr/bin/
cp -a configure_file/registerclient.png %{buildroot}/usr/share/registerclient/pixmaps/
cp -ar ui %{buildroot}/usr/share/registerclient/
cp -ar pic %{buildroot}/usr/share/registerclient/
chmod a+x lib/libsqlcipher.so.0
cp -a lib/libsqlcipher.so.0 %{buildroot}/lib64/
chmod a+x -R pysqlcipher3
cp -ar pysqlcipher3 %{buildroot}/usr/lib64/python2.7/site-packages/
chmod a+x reg_status.pyc
cp -a reg_status.pyc %{buildroot}/usr/lib64/python2.7/site-packages/
cp -a registerafter.sh %{buildroot}/usr/share/registerclient/
cp -a savestatus.sh %{buildroot}/usr/share/registerclient/
chmod a+x tips/registershowtips.pyc
cp -a tips/registershowtips.pyc %{buildroot}/usr/share/registerclient/
chmod a+x tips/registertips.desktop
cp -a tips/registertips.desktop %{buildroot}/etc/xdg/autostart
chmod a+x regcode-dbus-server
cp -a regcode-dbus-server %{buildroot}/usr/bin/
chmod a+x regcode-dbus-server.pyc
cp -a regcode-dbus-server.pyc %{buildroot}/usr/bin/
cp -a configure_file/com.nfs.register.conf %{buildroot}/etc/dbus-1/system.d/
cp -a configure_file/com.nfs.register.service %{buildroot}/usr/share/dbus-1/system-services
cp -a unregister-indicator.pyc %{buildroot}/usr/share/registerclient/
cp -a configure_file/unregister-indicator %{buildroot}/usr/share/registerclient/
cp -a configure_file/unregister-indicator.desktop %{buildroot}/etc/xdg/autostart/
cp -a style.css %{buildroot}/usr/share/registerclient/
cp -ar icons/hicolor %{buildroot}/usr/share/icons/

%clean

rm -rf %{buildroot}

%files

%defattr(-,root,root,-)

/usr/bin/*

#/usr/share/applications/*

/usr/lib64/*

/lib64/*

#/usr/share/registerclient/*

#/usr/lib64/python2.7/site-packages/*

/etc/*

/usr/share/*

%post

if [ -f /usr/share/registerclient/status.ini ]; then
        echo 'update status.ini'
else
        echo "MA==" > /usr/share/registerclient/status.ini
        echo "" >> /usr/share/registerclient/status.ini
fi
chmod a+w /usr/share/registerclient/status.ini
mv /usr/lib64/python2.7/site-packages/pysqlcipher3/_sqliteso /usr/lib64/python2.7/site-packages/pysqlcipher3/_sqlite.so

%preun

mv /usr/lib64/python2.7/site-packages/pysqlcipher3/_sqlite.so /usr/lib64/python2.7/site-packages/pysqlcipher3/_sqliteso

%changelog

* Mon Jul 19 2020 qixu<qixu@cpu-os.ac.cn@nfs.com>
- fix usb register
* Tue May 19 2020 qixu<qixu@cpu-os.ac.cn@nfs.com>
-
