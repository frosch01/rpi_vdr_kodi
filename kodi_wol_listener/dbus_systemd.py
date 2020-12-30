"""DBUS interface to systemd based on dbus_next"""
import os
import logging
import asyncio

from dbus_next.aio import MessageBus
from dbus_next import BusType

class DbusSystemd():
    """Base class containing common definitions and methods"""

    # The typical path of systemd service on system DBUS
    DBUS_SERVICE_SYSTEMD = 'org.freedesktop.systemd1'

    def __init__(self):
        self.bus = None

    async def init(self, use_system_bus=False):
        """Asyncio initialization

        Initialize connection to the bus

        Args:
            use_system_bus (bool) True to connect to system bus
        """
        bus_type = BusType.SYSTEM if use_system_bus else BusType.SESSION
        self.bus = MessageBus(bus_type=bus_type)
        await self.bus.connect()
        return self

    async def get_object(self, obj_path):
        """Get an object from systemd dbus service"""
        introspection = await self.bus.introspect(self.DBUS_SERVICE_SYSTEMD, obj_path)
        # Select systemd service object
        return self.bus.get_proxy_object(self.DBUS_SERVICE_SYSTEMD, obj_path, introspection)


class SystemdUnit():
    """Asyncio based Systemd.unit wrapper"""

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
        return ''.join(map(lambda x: x if x not in ' _.' else '_' + format(ord(x), 'x'),
                           self.service_name))

    def __init__(self, name, status_callback=None):
        self.service_name = name
        self.service_if = None
        self.service_state = None
        self.properties_if = None
        self.previous_hdmi_state = None
        self.status_callback = status_callback

    @property
    def state(self):
        """Get the service state

        Returns:
            (str) Current service state, e.g. 'inactive'
        """
        return self.service_state

    @state.setter
    def state(self, val):
        """Set the service state

        Args:
            val (str) New service state, e.g. 'inactive'
        """
        logging.debug("Service %s entered state %s", self.service_name, val)
        self.service_state = val

    async def init(self, systemd):
        """Initialize a unit wrapper on given bus

        The bus shall be connected when handed over. It may be initialized
        using:
            bus = await DbusSystemd().init()

        Args:
            systemd (DbusSystemd) Initialized systemd object
        """
        # Select systemd service object
        dbus_name = self.DBUS_OBJECT_UNIT_BASE + self.get_mangled_unit_object_name()
        obj = await systemd.get_object(dbus_name)
        # Get required interfaces
        self.service_if = obj.get_interface(self.DBUS_INTERFACE_UNIT)
        self.properties_if = obj.get_interface(self.DBUS_INTERFACE_PROPERTIES)
        # Monitor service status changes
        self.properties_if.on_properties_changed(self.on_properties_changed_cb)
        # Get initial service state
        state = await self.properties_if.call_get(self.DBUS_INTERFACE_UNIT, 'ActiveState')
        self.state = state.value
        return self

    def on_properties_changed_cb(self, interface_name, changed_properties, invalidated_properties):
        """Callback for receiving properties changed signals for given unit

        Args:
            interface_name (str) Name of the interface the callback is invoked for
            changed_properties (dict[str:value]) Changed properties
            invalidated_properties (dict[str:value]) Invalidated properties
        """
        try:
            new_service_state = changed_properties['ActiveState'].value
            if new_service_state != self.state:
                self.state = new_service_state
                if self.status_callback:
                    self.status_callback(new_service_state)
        except KeyError:
            pass

    def service_status_changed(self, task):  # pylint: disable = no-self-use
        """Callback called on finishing start/stop async tasks

        Handles exceptions occured from asyncio task

        Args:
            task (asyncio.Task) The task that finished
        """
        if task.exception():
            raise task.exception

    def start(self):
        """Create a start job for this unit"""
        if self.state == 'inactive':
            logging.debug("Starting %s...", self.service_name)
            loop = asyncio.get_running_loop()
            task = loop.create_task(self.service_if.call_start('replace'))
            task.add_done_callback(self.service_status_changed)

    def stop(self):
        """Create a stop job for this unit"""
        if self.state == 'active':
            logging.debug("Stopping %s...", self.service_name)
            loop = asyncio.get_running_loop()
            task = loop.create_task(self.service_if.call_stop('replace'))
            task.add_done_callback(self.service_status_changed)

class SystemdManager():
    """Asyncio based Systemd.manager wrapper"""

    # Base path of units within systemd DBUS service
    DBUS_OBJECT_SYSTEMD = '/org/freedesktop/systemd1'

    # Properties interface of DBUS (avaiable for all objects)
    DBUS_INTERFACE_MANAGER = 'org.freedesktop.systemd1.Manager'

    def __init__(self):
        self.manager_if = None

    async def init(self, systemd):
        """Initialize a system wrapper on given bus

        The bus shall be connected when handed over. It may be initialized
        using:
            bus = await DbusSystemd().init()

        Args:
            systemd (DbusSystemd) Initialized systemd object
        """
        # Select systemd service object
        obj = await systemd.get_object(self.DBUS_OBJECT_SYSTEMD)
        # Get required interface
        self.manager_if = obj.get_interface(self.DBUS_INTERFACE_MANAGER)

        return self

    async def reload(self):
        """Equivalent to systemctl daemon-reload"""
        await self.manager_if.call_reload()

    async def link_unit(self, unit):
        """Equivalent to systemctl link

        Args:
            unit (str) Unit to register. Shall be path, not only name
        """
        unit = os.path.abspath(unit)
        await self.manager_if.call_link_unit_files([unit], False, False)

    async def enable_unit(self, unit):
        """Equivalent to systemctl enable

        Args:
            unit (str) Unit to enable. Should be unit name, not path
        """
        await self.manager_if.call_enable_unit_files([unit], False, False)

    async def disable_unit(self, unit):
        """Equivalent to systemctl disable

        If the unit is registered using link_unit, systemd will automatically
        remove the link, too

        Args:
            unit (str) Unit to disable. Should be unit name, not path
        """
        await self.manager_if.call_disable_unit_files([unit], False)

    async def start_unit(self, unit):
        """Equivalent to systemctl start

        Args:
            unit (str) Unit to start. Should be unit name, not path
        """
        await self.manager_if.call_start_unit(unit, 'fail')

    async def stop_unit(self, unit):
        """Equivalent to systemctl stiop

        Args:
            unit (str) Unit to stop. Should be unit name, not path
        """
        await self.manager_if.call_stop_unit(unit, 'fail')


#if __name__ == "__main__":
    #async def main():
        #"""Async main function to be executed using asyncio.run()"""
        #systemd_session = await DbusSystemd().init()
        #manager = await SystemdManager().init(systemd_session)
        #await manager.link_unit(os.path.dirname(__file__) + '/dummy.service')
        #await manager.reload()
        #await manager.enable_unit('dummy.service')
        #await manager.start_unit('dummy.service')
        #await manager.stop_unit('dummy.service')
        #await manager.disable_unit('dummy.service')
        #await manager.reload()

#asyncio.run(main())
