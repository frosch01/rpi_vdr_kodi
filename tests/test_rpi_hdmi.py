import pytest

@pytest.fixture
def hdmi(mock_coroutine):
    coro, coro_mock = mock_coroutine('kodi_wol_listener.rpi_hdmi.AsyncSubprocess.run_wait')
    from kodi_wol_listener.rpi_hdmi import RaspberryPiHdmi
    return RaspberryPiHdmi(), coro, coro_mock


@pytest.mark.parametrize('ret, state', [(b'display_power=0', False), (b'display_power=1', True)])
@pytest.mark.asyncio
async def test_get_state(hdmi, ret, state):
    hdmi, _, coro_mock = hdmi
    coro_mock.return_value = ret
    assert await hdmi.get_state() == state

@pytest.mark.parametrize('state, arg', [(False, b'0'), (True, b'1')])
@pytest.mark.asyncio
async def test_set_state(hdmi, state, arg):
    hdmi, _, coro_mock = hdmi
    await hdmi.set_state(state)
    coro_mock.assert_called_once_with(hdmi.vcgencmd, arg)
