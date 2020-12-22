"""Provides a Wake-On-LAN pattern receiver that triggers a callback"""
import asyncio
import logging
import getmac

class WolReceiver(asyncio.DatagramProtocol):
    """Asyncio based Wake On LAN receiver listening on UDP port"""

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
        """Async initialization method

        Args:
            port (int) UDP port the receiver shall be listening
        """
        logging.debug("WOL listener running")
        loop = asyncio.get_running_loop()
        await loop.create_datagram_endpoint(lambda: self, local_addr=('0.0.0.0', port))
