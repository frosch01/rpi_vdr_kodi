"""A wrapper around the Raspberry PI vcgencmd display_power command"""

#TODO: Get things done without using subprocess, provide native implementation

import logging
from kodi_wol_listener.async_subprocess import AsyncSubprocess

class RaspberryPiHdmi():
    """Frontend to vcgencmd for getting/setting HDMI state

    This class is Raspberry PI specific
    """
    def __init__(self):
        self.vcgencmd = AsyncSubprocess(b'/usr/bin/vcgencmd display_power')

    async def get_state(self):
        """Return the HDMI output state as bool"""
        state = b'=1' in (await self.vcgencmd.run_wait())[1]
        logging.debug("HDMI is currently %sabled", 'en' if state else 'dis')
        return state

    async def set_state(self, state):
        """Set the HDMI output state"""
        arg = b'1' if state else b'0'
        await self.vcgencmd.run_wait(arg)
        logging.debug("HDMI port %sabled sucessfully", 'en' if state else 'dis')
