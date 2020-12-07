
from dbus_next.aio import MessageBus
from dbus_next import BusType

import asyncio

loop = asyncio.get_event_loop()


async def main():

    # The typical path of systemd service on system DBUS
    DBUS_SERVICE_SYSTEMD = 'org.freedesktop.systemd1'

    # Path of kodi unit within systemd DBUS service
    DBUS_OBJECT_UNIT_KODI = '/org/freedesktop/systemd1/unit/kodi_2eservice'

    # Properties interface of DBUS (avaiable for all objects)
    DBUS_INTERFACE_UNIT = 'org.freedesktop.systemd1.Unit'

    # systemd.unit interface of DBUS systemd.unit objects
    DBUS_INTERFACE_PROPERTIES = 'org.freedesktop.DBus.Properties'

    bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
    # the introspection xml would normally be included in your project, but
    # this is convenient for development
    introspection = await bus.introspect(DBUS_SERVICE_SYSTEMD, DBUS_OBJECT_UNIT_KODI)

    obj = bus.get_proxy_object(DBUS_SERVICE_SYSTEMD, DBUS_OBJECT_UNIT_KODI, introspection)
    kodi = obj.get_interface(DBUS_INTERFACE_UNIT)
    properties = obj.get_interface(DBUS_INTERFACE_PROPERTIES)

    # Get current unit state
    current_state = await properties.call_get(DBUS_INTERFACE_UNIT, 'ActiveState')
    print(current_state.value)

    #breakpoint()

    # listen to properties changed signal.
    # Of major interest is the property 'ActiveState'
    def on_properties_changed(interface_name, changed_properties, invalidated_properties):
        try:
            print(changed_properties['ActiveState'].value)
        except KeyError:
            pass
    properties.on_properties_changed(on_properties_changed)

    # call methods on the interface (this causes kodi to stop)
    await kodi.call_stop('fail')

    # Wait for a never completing future - forever
    await asyncio.get_running_loop().create_future()

loop.run_until_complete(main())
