#!/usr/bin/env python3

import socket
import sys
import subprocess
import dbus
import getmac

mymac_bytes = bytes.fromhex(getmac.get_mac_address(interface="eth0").replace(':', ''))

dbus_systemd='org.freedesktop.systemd1'
dbus_systemd_kodi='/org/freedesktop/systemd1/unit/kodi_2eservice'
dbus_intrfc_properties='org.freedesktop.DBus.Properties'
dbus_intrfc_unit='org.freedesktop.systemd1.Unit'

sysbus = dbus.SystemBus()
kodi_service=sysbus.get_object(dbus_systemd, dbus_systemd_kodi)

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
                if (kodi_service.Get(dbus_intrfc_unit, 'ActiveState', dbus_interface=dbus_intrfc_properties) == "inactive"):
                    kodi_service.Start('fail', dbus_interface=dbus_intrfc_unit)
                    print("Kodi.service started successfully")
            except:
                 print("Unable to Start() kodi.service", file=sys.stderr)
        else:
            print("Unable to enable HDMI port, vcgencmd output: {}".format(result.stdout), file=sys.stderr)
