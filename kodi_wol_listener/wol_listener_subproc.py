#!/usr/bin/env python3
"""This program is listening on an UDP port for an incoming WOL pattern. On
receiption of the pattern kodi is started.

The reason for this is that the Kodi remote control app "kore" is able to
wake up a kodi PC from suspend based on BIOS WOL wakeups. For RPI, the firmware
does not offer any WOL support wich also not really applicable, as the PI
consumes very little power if in idle. But WOL pattern cal also received by
a user space application as they are based on UDP/IP communication.
"""
import sys
import os
import asyncio
import logging
import signal
import functools
import enum
from typing import Optional
import coloredlogs
import typer

from kodi_wol_listener.async_subprocess import AsyncSubprocess
from kodi_wol_listener.rpi_hdmi import RaspberryPiHdmi
from kodi_wol_listener.wol_receiver import WolReceiver
from kodi_wol_listener.dbus_systemd import DbusSystemd, SystemdManager

class KodiManager():
    """Application that runs kodi as a subprocess on an incoming WOL pattern

    The kodi display output is activated and put into the same state it was
    before kodi has been activated.
    """

    SYSTEMD_SERVICE = 'kodi_wol_listener.service'

    class DebugLevel(enum.Enum):
        """Enumeration for logging related cli handling"""
        NOTSET = 'notset'
        DEBUG = 'debug'
        INFO = 'info'
        WARNING = 'warning'
        ERROR = 'error'
        CRITICAL = 'critical'


    def __init__(self):
        self.hdmi = RaspberryPiHdmi()
        self.kodi = AsyncSubprocess(b'/usr/bin/kodi', abort_on_fail=False)
        self.wol_receiver = WolReceiver(self.kodi_start)
        self.kodi_running = False
        self.exit_future = None

    def _exit(self, signame, loop):
        if self.exit_future:
            self.exit_future.set_result(signame)
        else:
            loop.stop()

    def _typer_run(self,
                   port: int = typer.Option(42429, help = "UDP/IP port to listen for WOL pattern"),
                   debug_level: DebugLevel = 'warning',
                   install: Optional[bool] = typer.Option(
                       None, "--install", help = "Activate autostart via systemd user session"),
                   uninstall: Optional[bool] = typer.Option(
                       None, "--uninstall", help = "Remove autostart configuration")):
        coloredlogs.install(debug_level.value)
        if install:
            asyncio.run(self.install())
        elif uninstall:
            asyncio.run(self.uninstall())
        else:
            asyncio.run(self.main(port))

    async def install(self):
        """Install listener as a systemd service"""
        systemd_session = await DbusSystemd().init()
        manager = await SystemdManager().init(systemd_session)
        await manager.link_unit(os.path.dirname(__file__) + '/' + self.SYSTEMD_SERVICE)
        await manager.reload()
        await manager.enable_unit(self.SYSTEMD_SERVICE)
        await manager.start_unit(self.SYSTEMD_SERVICE)

    async def uninstall(self):
        """Uninstall listener from systemd"""
        systemd_session = await DbusSystemd().init()
        manager = await SystemdManager().init(systemd_session)
        await manager.stop_unit(self.SYSTEMD_SERVICE)
        await manager.disable_unit(self.SYSTEMD_SERVICE)
        await manager.reload()

    def run(self):
        """Execute the application. Returns as application exits"""
        typer.run(self._typer_run)

    async def main(self, port):
        """The asyncio based application main()"""
        # Install a signal handler for common UNIX signals
        loop = asyncio.get_running_loop()
        for signame in ('SIGINT', 'SIGTERM'):
            loop.add_signal_handler(
                getattr(signal, signame),
                functools.partial(self._exit, signame, loop))
        # Initialize WOL receiver. Any activity will be triggerd by this
        # WOL protocol
        await self.wol_receiver.init(port)
        # Wait for a never completing future - forever
        self.exit_future = loop.create_future()
        ret = await self.exit_future
        if isinstance(ret, Exception):
            raise ValueError(ret) from ret

    async def kodi_exec(self):
        """Run kodi as subprocess and wait until finished, activate HDMI output

        After kodi has finished, the HDMI output is set to the state it was
        before.
        """
        try:
            display_state = await self.hdmi.get_state()
            if not display_state:
                await self.hdmi.set_state(True)
            logging.debug("Running Kodi")
            await self.kodi.run_wait()
            logging.debug("Kodi finshed")
            if not display_state:
                await self.hdmi.set_state(display_state)
        except OSError as excp:
            logging.error("Running external commands caused an exception:", exc_info=excp)
            sys.exit(1)

    def kodi_done_cb(self, fut):
        """Callback called as kodi_exec() coroutine has finished"""
        # All excpetion are expected to be handled....
        fut.result()
        self.kodi_running = False

    def kodi_start(self, addr):
        """API to trigger start of kodi

        Creates an asyncio task that will run kodi. Returns immediately.
        Task execution result is given to a callback.

        In case Kodi was started already, another start is omitted until prev.
        started kodi process has finished.
        """
        if not self.kodi_running:
            logging.debug("Kodi start requested by %s:%d", addr[0], addr[1])
            self.kodi_running = True
            start_task = asyncio.get_running_loop().create_task(self.kodi_exec())
            start_task.add_done_callback(self.kodi_done_cb)

        else:
            logging.debug("Kodi start requested by %s:%d but kodi is running already",
                          addr[0], addr[1])
