#! /bin/sh

statusfile="/usr/share/registerclient/status.ini"
statusbakfile="/usr/share/registerclient/status-bak.ini"

if [ -f "$statusbakfile" ]; then
	mv $statusbakfile $statusfile
fi

