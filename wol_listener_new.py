#!/usr/bin/env python3
import subprocess
import asyncio
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
        print("WOL listener running")
        loop = asyncio.get_running_loop()
        await loop.create_datagram_endpoint(lambda: self, local_addr=('0.0.0.0', 9))


class RaspberryPiHdmi():  # pylint: disable = too-few-public-methods
    """Frontend to vcgencmd for getting/setting HDMI state"""

    @property
    def state(self):  # pylint: disable = no-self-use
        result = str(subprocess.check_output([b'vcgencmd', b'display_power']))
        return b'=1' in result

    @state.setter
    def state(self, state):  # pylint: disable = no-self-use
        arg = b'1' if state else b'0'
        subprocess.check_output([b'vcgencmd', b'display_power', arg])
        print(f"HDMI port {'en' if state else 'dis'}abled sucessfully")


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

    @classmethod
    def mangle_unit_object_name(cls, name):
        """Return a string with delimiters replaced by _<hex(ascii(delimiter))>
        """
        # Each delimiter in a service name is replaced by '_<hex(ascii(delimiter))>'
        return ''.join(map(lambda x: x if x not in ' _.' else '_' + format(ord(x), 'x'), name))

    def __init__(self, name):
        self.service_name = name
        self.dbus_name = self.DBUS_OBJECT_UNIT_BASE + self.mangle_unit_object_name(name)
        self.service_if = None
        self.service_state = None
        self.properties_if = None
        self.previous_hdmi_state = None

    @property
    def state(self):
        return self.service_state

    @state.setter
    def state(self, val):
        print(f"Service {self.service_name} entered state {val}")
        self.service_state = val

    async def init(self):
        bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
        # Get introspection XML
        introspection = await bus.introspect(self.DBUS_SERVICE_SYSTEMD, self.dbus_name)
        # Select systemd service object
        obj = bus.get_proxy_object(self.DBUS_SERVICE_SYSTEMD, self.dbus_name, introspection)
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
        except KeyError:
            pass

    async def start(self):
        if self.state == 'inactive':
            print(f"Starting {self.service_name}...")
            await self.service_if.call_start('replace')

    async def stop(self):
        if self.state == 'active':
            print(f"Stoping {self.service_name}...")
            await self.service_if.call_stop('replace')


async def main():
    hdmi = RaspberryPiHdmi()
    print(hdmi.state)

    kodi = DbusSystemdService('kodi.service')
    await kodi.init()

    await kodi.start()

    await asyncio.sleep(5)

    await kodi.stop()

    # Commented for now...
    #wol_receiver = WolReceiver(kodi.start_kodi)
    #await wol_receiver.init()

    # Wait for a never completing future - forever
    #await asyncio.get_running_loop().create_future()

if __name__ == "__main__":
    asyncio.run(main())
