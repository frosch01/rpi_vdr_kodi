#!/usr/bin/env python3

import socket
import sys
import subprocess
import dbus
import getmac

mymac_bytes = bytes.fromhex(getmac.get_mac_address(interface="eth0").replace(':', ''))

sysbus = dbus.SystemBus()
kodi_service=sysbus.get_object('org.freedesktop.systemd1', '/org/freedesktop/systemd1/unit/kodi_2eservice')
kodi_interface=dbus.Interface(kodi_service, 'org.freedesktop.systemd1.Unit')
kodi_properties=dbus.Interface(kodi_service, 'org.freedesktop.DBus.Properties')

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('', 9))
while True:
    data, address = sock.recvfrom(65536)
    # Simple check the payload to be started with 6 bytes of 0xff followed by
    # this machines MAC address
    if b'\xff'*6 == data[:6] and mymac_bytes == data[6:12]:
        result = subprocess.run(['vcgencmd', 'display_power 1'], stdout=subprocess.PIPE)
        if result.stdout.find(b"error") == -1:
            print("HDMI port enabled sucessfully")
            try:
                if (kodi_properties.Get('org.freedesktop.systemd1.Unit', 'ActiveState') == "inactive"):
                    kodi_interface.Start('fail')
                    kodi_properties.Get('org.freedesktop.systemd1.Unit', 'ActiveState')
                    print("Kodi.service started successfully")
            except:
                 print("Unable to Start() kodi.service", file=sys.stderr)
        else:
            print("Unable to enable HDMI port, vcgencmd output: {}".format(result.stdout), file=sys.stderr)
