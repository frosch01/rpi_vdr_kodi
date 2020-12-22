"""A wrapper around the Raspberry PI vcgencmd display_power command"""

#TODO: Get things done without using subprocess, provide native implementation

import logging
from async_subprocess import AsyncSubprocess

class RaspberryPiHdmi(AsyncSubprocess):
    """Frontend to vcgencmd for getting/setting HDMI state"""
    def __init__(self):
        super().__init__(b'/usr/bin/vcgencmd display_power')

    async def get_state(self):
        """Return the HDMI output state as bool"""
        result = await self.run_wait()
        return b'=1' in result

    async def set_state(self, state):
        """Set the HDMI output state"""
        arg = b'1' if state else b'0'
        await self.run_wait(arg)
        logging.debug("HDMI port %sabled sucessfully", 'en' if state else 'dis')
