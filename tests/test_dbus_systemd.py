import os
import pytest

pytestmark = [
    pytest.mark.skipif(not os.environ.get('XDG_RUNTIME_DIR'), reason='Systemd environment required'),
    pytest.mark.skipif(not os.environ.get('DBUS_SESSION_BUS_ADDRESS'), reason='DBUS environment required')]

@pytest.fixture
async def systemd():
    from kodi_wol_listener.dbus_systemd import DbusSystemd
    return await DbusSystemd().init()


@pytest.mark.asyncio
async def test_dbus_systemd(systemd):
    await systemd.get_object('/org/freedesktop/systemd1')


@pytest.mark.asyncio
async def test_manager(systemd):
    import os
    from kodi_wol_listener.dbus_systemd import SystemdManager
    manager = await SystemdManager().init(systemd)
    await manager.link_unit(os.path.dirname(__file__) + '/dummy.service')
    await manager.reload()
    await manager.enable_unit('dummy.service')
    await manager.start_unit('dummy.service')
    await manager.stop_unit('dummy.service')
    await manager.disable_unit('dummy.service')
    await manager.reload()
