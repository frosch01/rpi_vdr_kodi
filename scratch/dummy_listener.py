#!/usr/bin/env python3

# Python version required: >= 3.7

"""A simple subscriber/listener for systemd unit signals"""
import sys
import asyncio
from dbus_next.aio import MessageBus
from dbus_next import BusType

class DbusDummyService():  # pylint: disable=no-self-use
    """Asyncio based dummy.service listener"""
    async def init(self, bus_type=BusType.SESSION):
        """Register listener callback with dbus bus_type"""
        bus = await MessageBus(bus_type=bus_type).connect()
        # Get introspection XML
        introspection = await bus.introspect('org.freedesktop.systemd1',
                                             '/org/freedesktop/systemd1/unit/dummy_2eservice')
        # Select systemd service object
        obj = bus.get_proxy_object('org.freedesktop.systemd1',
                                   '/org/freedesktop/systemd1/unit/dummy_2eservice', introspection)
        # Get required interfaces
        properties_if = obj.get_interface('org.freedesktop.DBus.Properties')
        # Monitor service status changes
        properties_if.on_properties_changed(self.on_properties_changed_cb)

    def on_properties_changed_cb(self, interface_name, changed_props, invalidated_props):
        """Callback expected to be called on unit property changes"""
        print(f"Callback invoked for interface {interface_name}:")
        print(f"  Properties updated")
        for prop, val in changed_props.items():
            print(f"    {prop} set to {val.value}")
        print(f"  Properties invalidated")
        for prop in invalidated_props:
            print(f"    {prop} invalidated")

async def main(bus_type):
    """Asyncio main"""
    # Initialize dbus listener
    await DbusDummyService().init(bus_type)
    # Run loop forever (waiting for dbus signals)
    await asyncio.get_running_loop().create_future()

if __name__ == "__main__":
    try:
        BUS_TYPE = BusType.SYSTEM if 'sys' in sys.argv[1] else BusType.SESSION
    except BaseException:
        BUS_TYPE = BusType.SESSION

    asyncio.run(main(BUS_TYPE))
