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
import getmac
import typer

class DebugLevel(enum.Enum):
    NOTSET = 'notset'
    DEBUG = 'debug'
    INFO = 'info'
    WARNING = 'warning'
    ERROR = 'error'
    CRITICAL = 'critical'


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

    async def init(self, port):
        logging.debug("WOL listener running")
        loop = asyncio.get_running_loop()
        await loop.create_datagram_endpoint(lambda: self, local_addr=('0.0.0.0', port))


class Subprocess():  # pylint: disable=logging-fstring-interpolation
    """Asyncio based subprocess runner"""
    def __init__(self, cmd_base, logging_level=logging.WARNING, abort_on_fail=True):
        self.cmd_base = cmd_base
        self.level = logging_level
        self.abort_on_fail = abort_on_fail
        if abort_on_fail:
            self.abort_level = logging.ERROR
        else:
            self.abort_level = logging_level
        self.proc = None
        self.cmd = None

    async def run(self, cmd_args=b''):
        self.cmd = self.cmd_base + b' ' + cmd_args
        self.proc = await asyncio.create_subprocess_shell(
            self.cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)

    async def wait_completed(self):
        stdout, stderr = await self.proc.communicate()
        self._handle_subprocess_return(self.proc.returncode, stdout, stderr)
        return stdout

    async def run_wait(self, cmd_args=b''):
        await self.run(cmd_args)
        return await self.wait_completed()

    def _handle_subprocess_return(self, returncode, stdout, stderr):
        if returncode != 0:
            level = self.abort_level if self.abort_on_fail else self.level
            logging.log(level, f"subprocess {self.cmd} exited with error code {returncode}")
            if stdout:
                logging.log(level, f'[stdout]\n{stdout.decode()}')
            if stderr:
                logging.log(level, f'[stderr]\n{stderr.decode()}')
            if self.abort_on_fail:
                raise OSError(f"Error when executing command {self.cmd}: {stderr.decode()}")


class RaspberryPiHdmi(Subprocess):
    """Frontend to vcgencmd for getting/setting HDMI state"""
    def __init__(self):
        super().__init__(b'/usr/bin/vcgencmd display_power')

    async def get_state(self):
        result = await self.run_wait()
        return b'=1' in result

    async def set_state(self, state):
        arg = b'1' if state else b'0'
        await self.run_wait(arg)
        logging.debug("HDMI port %sabled sucessfully", 'en' if state else 'dis')


class KodiManager():
    """Manages the activation of kodi as a subprocess an incoming WOL pattern.
    The kodi display output is activated and put into the same state it was
    before kodi has been activated.
    """
    def __init__(self):
        self.hdmi = RaspberryPiHdmi()
        self.kodi = Subprocess(b'/usr/bin/kodi', abort_on_fail=False)
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
