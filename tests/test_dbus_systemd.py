import os
import pytest

# Only execute tests in this module if systemd and dbus are available
pytestmark = [
    pytest.mark.skipif(not os.environ.get('XDG_RUNTIME_DIR'), reason='Systemd environment required'),
    pytest.mark.skipif(not os.environ.get('DBUS_SESSION_BUS_ADDRESS'), reason='DBUS environment required')]

@pytest.fixture
async def systemd():
    from kodi_wol_listener.dbus_systemd import DbusSystemd
    return await DbusSystemd().init()

@pytest.fixture
async def manager(systemd):
    import os
    from kodi_wol_listener.dbus_systemd import SystemdManager
    manager = await SystemdManager().init(systemd)
    await manager.link_unit(os.path.dirname(__file__) + '/wol_listener_test.service')
    await manager.reload()
    await manager.enable_unit('wol_listener_test.service')
    yield manager
    await manager.stop_unit('wol_listener_test.service')
    await manager.disable_unit('wol_listener_test.service')
    await manager.reload()

@pytest.mark.asyncio
async def test_dbus_systemd(systemd):
    await systemd.get_object('/org/freedesktop/systemd1')

@pytest.mark.asyncio
async def test_manager(manager):
    await manager.start_unit('wol_listener_test.service')
    await manager.get_unit('wol_listener_test.service')
    await manager.stop_unit('wol_listener_test.service')

@pytest.mark.asyncio
async def test_unit(mocker, systemd, manager):
    from kodi_wol_listener.dbus_systemd import SystemdUnit
    await manager.start_unit('wol_listener_test.service')
    mock_cb = mocker.Mock()
    dummy = await SystemdUnit('wol_listener_test.service', mock_cb).init(systemd)
    assert dummy.state == 'active'
    dummy.stop()
    await dummy.wait_for_job()
    # Signals on units only work when systemd is PID1. So call cb manually
    variant = mocker.Mock(value='inactive')
    dummy.on_properties_changed_cb(mocker.sentinel.interface,
                                   {'ActiveState' : variant}, {})
    mock_cb.assert_called_once_with('inactive')
    assert dummy.state == 'inactive'
    mock_cb.reset_mock()
    dummy.start()
    await dummy.wait_for_job()
    # Signals on units only work when systemd is PID1. So call cb manually
    variant.value='active'
    dummy.on_properties_changed_cb(mocker.sentinel.interface,
                                   {'ActiveState' : variant}, {})
    mock_cb.assert_called_once_with('active')
    variant = mocker.Mock(value='active')

@pytest.mark.asyncio
async def test_unit_errors(mocker):
    from kodi_wol_listener.dbus_systemd import SystemdUnit
    unit = SystemdUnit('dummy.unit')
    task = mocker.Mock()
    task.exception.return_value = UserWarning('Expected error')
    with pytest.raises(UserWarning):
        unit.service_status_changed(task)
    unit.on_properties_changed_cb(None, {}, {})
