import pytest

@pytest.mark.asyncio
async def test_dbus_systemd():
    from kodi_wol_listener.dbus_systemd import DbusSystemd
    bus = await DbusSystemd().init()
    await bus.get_object('/org/freedesktop/systemd1')
