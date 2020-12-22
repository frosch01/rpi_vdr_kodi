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
import asyncio
import logging
import signal
import functools
import enum
import coloredlogs
import typer

from async_subprocess import AsyncSubprocess
from rpi_hdmi import RaspberryPiHdmi
from wol_receiver import WolReceiver


class KodiManager():
    """Manages the activation of kodi as a subprocess an incoming WOL pattern.
    The kodi display output is activated and put into the same state it was
    before kodi has been activated.
    """

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

    def _typer_run(self, port: int=42429, debug_level: DebugLevel='warning'):
        coloredlogs.install(debug_level.value)
        asyncio.run(self.main(port))

    def run(self):
        typer.run(self._typer_run)

    async def main(self, port):
        """The asyncio based application main()"""
        # Install a signal handler for common UNIX signals
        loop = asyncio.get_running_loop()
        for signame in {'SIGINT', 'SIGTERM'}:
            loop.add_signal_handler(
                getattr(signal, signame),
                functools.partial(self._exit, signame, loop))
        # Initialize WOL receiver. Any activity will be triggerd by this
        # WOL protocol
        await self.wol_receiver.init(port)
        # Wait for a never completing future - forever
        self.exit_future = loop.create_future()
        await self.exit_future

    async def kodi_exec(self):
        try:
            display_state = await self.hdmi.get_state()
            if not display_state:
                await self.hdmi.set_state(True)
            logging.debug("Running Kodi")
            await self.kodi.run_wait()
            logging.debug("Kodi finshed")
            if not display_state:
                await self.hdmi.set_state(display_state)
        except BaseException as excp:
            logging.error("Running external commands caused an exception:", exc_info=excp)
            sys.exit(1)

    def kodi_done_cb(self, fut):
        # All excpetion are expected to be handled....
        fut.result()
        self.kodi_running = False

    def kodi_start(self, addr):
        if not self.kodi_running:
            logging.debug("Kodi start requested by %s:%d", addr[0], addr[1])
            self.kodi_running = True
            task = asyncio.get_running_loop().create_task(self.kodi_exec())
            task.add_done_callback(self.kodi_done_cb)
        else:
            logging.debug("Kodi start requested by %s:%d but kodi is running already",
                          addr[0], addr[1])


if __name__ == "__main__":
    KodiManager().run()
