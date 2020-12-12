#!/usr/bin/env python3
import subprocess
import asyncio
import logging
import coloredlogs
import getmac

from dbus_next.aio import MessageBus
from dbus_next import BusType

class WolReceiver(asyncio.DatagramProtocol):
    """Asyncio based Wake On LAN receiver listening on UDP port 9"""

    def __init__(self, wol_callback):
        super().__init__()
        # TODO: Fetch MACs from all the present interfaces
        mac_hex = getmac.get_mac_address(interface="eth0")
        self.mymac_bytes = bytes.fromhex(mac_hex.replace(':', ''))
        self.wol_callback = wol_callback
        self.transport = None

    def connection_made(self, transport):
        super().connection_made(transport)
        self.transport = transport

    def datagram_received(self, data, addr):
        super().datagram_received(data, addr)
        if b'\xff'*6 == data[:6] and self.mymac_bytes == data[6:12]:
            self.wol_callback(addr)

    async def init(self):
        logging.debug("WOL listener running")
        loop = asyncio.get_running_loop()
        await loop.create_datagram_endpoint(lambda: self, local_addr=('0.0.0.0', 9))


class RaspberryPiHdmi():  # pylint: disable = too-few-public-methods
    """Frontend to vcgencmd for getting/setting HDMI state"""
    def __init__(self):
        logging.debug("Current display power status is %s", 'ON' if self.state else 'OFF')

    @property
    def state(self):  # pylint: disable = no-self-use
        result = bytes(subprocess.check_output([b'vcgencmd', b'display_power']))
        return b'=1' in result

    @state.setter
    def state(self, state):  # pylint: disable = no-self-use
        arg = b'1' if state else b'0'
        subprocess.check_output([b'vcgencmd', b'display_power', arg])
        logging.debug("HDMI port %sabled sucessfully", 'en' if state else 'dis')


class DbusSystemdService():
    """Asyncio based Systemd.service interface"""

    # The typical path of systemd service on system DBUS
    DBUS_SERVICE_SYSTEMD = 'org.freedesktop.systemd1'

    # Base path of units within systemd DBUS service
    DBUS_OBJECT_UNIT_BASE = '/org/freedesktop/systemd1/unit/'

    # Properties interface of DBUS (avaiable for all objects)
    DBUS_INTERFACE_UNIT = 'org.freedesktop.systemd1.Unit'

    # systemd.unit interface of DBUS systemd.unit objects
    DBUS_INTERFACE_PROPERTIES = 'org.freedesktop.DBus.Properties'

    def get_mangled_unit_object_name(self):
        """Return a string with delimiters replaced by _<hex(ascii(delimiter))>
        """
        # Each delimiter in a service name is replaced by '_<hex(ascii(delimiter))>'
        return ''.join(map(lambda x: x if x not in ' _.' else '_' + format(ord(x), 'x'), self.service_name))

    def __init__(self, name, status_callback=None):
        self.service_name = name
        self.service_if = None
        self.service_state = None
        self.properties_if = None
        self.previous_hdmi_state = None
        self.status_callback = status_callback

    @property
    def state(self):
        return self.service_state

    @state.setter
    def state(self, val):
        logging.debug("Service %s entered state %s", self.service_name, val)
        self.service_state = val

    async def init(self):
        dbus_name = self.DBUS_OBJECT_UNIT_BASE + self.get_mangled_unit_object_name()
        bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
        # Get introspection XML
        introspection = await bus.introspect(self.DBUS_SERVICE_SYSTEMD, dbus_name)
        # Select systemd service object
        obj = bus.get_proxy_object(self.DBUS_SERVICE_SYSTEMD, dbus_name, introspection)
        # Get required interfaces
        self.service_if = obj.get_interface(self.DBUS_INTERFACE_UNIT)
        self.properties_if = obj.get_interface(self.DBUS_INTERFACE_PROPERTIES)
        # Monitor service status changes
        self.properties_if.on_properties_changed(self.on_properties_changed_cb)
        # Get initial service state
        state = await self.properties_if.call_get(self.DBUS_INTERFACE_UNIT, 'ActiveState')
        self.state = state.value

    def on_properties_changed_cb(self, interface_name, changed_properties, invalidated_properties):
        try:
            new_service_state = changed_properties['ActiveState'].value
            if new_service_state != self.state:
                self.state = new_service_state
                if self.status_callback:
                    self.status_callback(new_service_state)
        except KeyError:
            pass

    def service_status_changed(self, task):  # pylint: disable = no-self-use
        if task.exception():
            raise task.exception

    def start(self):
        if self.state == 'inactive':
            logging.debug("Starting %s...", self.service_name)
            loop = asyncio.get_running_loop()
            task = loop.create_task(self.service_if.call_start('replace'))
            task.add_done_callback(self.service_status_changed)

    def stop(self):
        if self.state == 'active':
            logging.debug("Stopping %s...", self.service_name)
            loop = asyncio.get_running_loop()
            task = loop.create_task(self.service_if.call_stop('replace'))
            task.add_done_callback(self.service_status_changed)

class KodiManager():
    def __init__(self):
        self.hdmi = RaspberryPiHdmi()
        self.kodi = DbusSystemdService('kodi.service', self.kodi_status_change)
        self.wol_receiver = WolReceiver(self.kodi_start)
        self.display_state_original = self.hdmi.state

    async def init(self):
        await self.kodi.init()
        await self.wol_receiver.init()

    def kodi_start(self, addr):
        logging.debug("Kodi start requested by %s:%d", addr[0], addr[1])
        self.kodi.start()

    def kodi_status_change(self, new_state):
        if new_state == 'active':
            logging.debug("Kodi status changed to %s", new_state)
            self.display_state_original = self.hdmi.state
            self.hdmi.state = True
        elif new_state == 'inactive':
            self.hdmi.state = self.display_state_original

if __name__ == "__main__":

    async def main():
        # Create an instance of kodi manager and initialize
        kodi_manager = KodiManager()
        await kodi_manager.init()

        # Wait for a never completing future - forever
        await asyncio.get_running_loop().create_future()

    coloredlogs.install(level='DEBUG')

    asyncio.run(main())
