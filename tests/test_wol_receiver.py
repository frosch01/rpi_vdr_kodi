import pytest

# Code has low complexity. A single function is enough
@pytest.mark.asyncio
async def test_all(caplog, mocker, event_loop):
    from kodi_wol_listener.wol_receiver import WolReceiver
    import socket
    import getmac
    import asyncio

    caplog.set_level('DEBUG')
    # create a mock callback that triggers termintate future
    terminate = event_loop.create_future()
    callback = mocker.Mock()
    def callback_func(*args):
        terminate.set_result(None)
    callback.side_effect = callback_func
    # Initialize WolReceiver
    wol = WolReceiver(callback)
    dst_port = await wol.init()
    # Create socket for sending wakeup pattern
    sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    sock.bind(('127.0.0.1', 0))
    src_addr = sock.getsockname()
    dst_addr = ('127.0.0.1', dst_port)

    # Send an arbitrary packet -> Rejected
    sock.sendto(b'hello world', dst_addr)
    # Send a valid WOL packet -> Accepted
    mac_hex_str = getmac.get_mac_address(interface="eth0")
    mac_bytes = bytes.fromhex(mac_hex_str.replace(':', ''))
    sock.sendto(b'\xff' * 6 + mac_bytes, dst_addr)

    # Evaluate results, a single call is expected
    await asyncio.wait_for(terminate, 1)
    callback.assert_called_once_with(src_addr)
