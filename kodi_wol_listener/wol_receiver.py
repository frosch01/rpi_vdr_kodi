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
        accepted = b'\xff'*6 + self.mymac_bytes == data[:12]
        if accepted:
            self.wol_callback(addr)
        logging.debug("WOL listener %s from %s:%d: %s",
                      'accepted' if accepted else 'rejected',
                      addr[0], addr[1],
                      data.hex())

    async def init(self, port=0):
        """Async initialization method

        Args:
            port (int) UDP port the receiver shall be listening
        Returns:
            (int) The port actually taken (in case of 0 port argument)
        """
        loop = asyncio.get_running_loop()
        await loop.create_datagram_endpoint(lambda: self, local_addr=('0.0.0.0', port))
        sock = self.transport.get_extra_info('socket')
        port = sock.getsockname()[1]
        logging.debug("WOL listener running on port %d", port)
        return port
