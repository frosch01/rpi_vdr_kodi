import signal
import pytest

@pytest.fixture
def app(mocker, mock_coroutine):
    from kodi_wol_listener.wol_listener_subproc import KodiManager

    AsyncSubprocess = mocker.patch('kodi_wol_listener.wol_listener_subproc.AsyncSubprocess')
    RaspberryPiHdmi = mocker.patch('kodi_wol_listener.wol_listener_subproc.RaspberryPiHdmi')
    WolReceiver = mocker.patch('kodi_wol_listener.wol_listener_subproc.WolReceiver')
    WolReceiver.return_value.init, mock_init = mock_coroutine()
    app = KodiManager()
    return app, (AsyncSubprocess, RaspberryPiHdmi, WolReceiver)

def test_init(app):
    app, (AsyncSubprocess, RaspberryPiHdmi, WolReceiver) = app
    assert app.hdmi == RaspberryPiHdmi.return_value
    assert app.kodi == AsyncSubprocess.return_value
    assert app.wol_receiver == WolReceiver.return_value

@pytest.fixture
def app_signal_handler(request, app):
    app, _ = app
    sig = request.param
    def sig_handler(*args):
        err_text = f"The signal {sig.name} is expected to be handled by the app"
        app.exit_future.set_result(AssertionError(err_text))
    prev_handler = signal.signal(sig, sig_handler)
    yield app, sig
    signal.signal(sig, prev_handler)

@pytest.mark.parametrize('app_signal_handler, handled',
                         [(signal.SIGINT, True),
                          (signal.SIGTERM, True),
                          (signal.SIGUSR1, False)],
                         indirect=['app_signal_handler'])
@pytest.mark.asyncio
async def test_graceful_signals_new(event_loop, app_signal_handler, handled):
    import os
    import asyncio
    app, sig = app_signal_handler
    event_loop.call_later(0.01, os.kill, os.getpid(), sig)
    if handled:
        await asyncio.wait_for(app.main(0), 0.5, loop=event_loop)
    else:
        with pytest.raises(ValueError):
            await asyncio.wait_for(app.main(0), 0.5, loop=event_loop)

def test_run(mocker, app):
    from kodi_wol_listener.wol_listener_subproc import KodiManager
    app, _ = app
    main = mocker.patch.object(app, 'main')
    main.return_value = mocker.sentinel.main_coro
    typer = mocker.patch('kodi_wol_listener.wol_listener_subproc.typer')
    asyncio = mocker.patch('kodi_wol_listener.wol_listener_subproc.asyncio')
    typer.run.side_effect = app._typer_run(mocker.sentinel.port, KodiManager.DebugLevel.INFO)
    app.run()
    typer.run.assert_called_once_with(app._typer_run)
    asyncio.run.assert_called_once_with(mocker.sentinel.main_coro)

@pytest.mark.parametrize('hdmi_state', [False, True])
@pytest.mark.asyncio
async def test_run_kodi_ok(mocker, app, mock_coroutine, hdmi_state):
    app, _ = app
    _, get_state_mock = mock_coroutine(app.hdmi, 'get_state')
    _, set_state_mock = mock_coroutine(app.hdmi, 'set_state')
    _, run_wait_mock = mock_coroutine(app.kodi, 'run_wait')
    get_state_mock.return_value = hdmi_state
    await app.kodi_exec()
    # Verify that HDMI output is activated and de-activated later if it was
    # initially
    if hdmi_state:
        assert mocker.call(False) not in set_state_mock.call_args_list
    else:
        set_state_mock.assert_has_calls([mocker.call(True), mocker.call(False)])
    # Verify that kodi is started
    run_wait_mock.assert_called_once_with()

@pytest.mark.asyncio
async def test_run_kodi_bad(app, mock_coroutine):
    app, _ = app
    _, get_state_mock = mock_coroutine(app.hdmi, 'get_state')
    get_state_mock.side_effect = AssertionError('Intended error')
    with pytest.raises(SystemExit):
        await app.kodi_exec()

def test_exit_no_run(mocker, event_loop, app):
    import asyncio
    app, _ = app
    app._exit(mocker.sentinel.signame, event_loop)
    assert not event_loop.is_running()

@pytest.mark.asyncio
async def test_start(caplog, mocker, event_loop, app, mock_coroutine):
    import asyncio
    caplog.set_level('DEBUG')
    app, _ = app
    _, get_state_mock = mock_coroutine(app, 'kodi_exec')
    app.kodi_done_cb = mocker.Mock(wraps=app.kodi_done_cb)
    # A new task is expected to be created
    assert len(asyncio.all_tasks(event_loop)) == 1
    app.kodi_start(('hello', 42))
    assert len(asyncio.all_tasks(event_loop)) == 2
    assert app.kodi_running
    # A 2nd start shall not be possible
    app.kodi_start(('world', 21))
    assert len(asyncio.all_tasks(event_loop)) == 2
    # Let the loop run for a short amount of time (kodi executes async)
    await asyncio.sleep(0.1)
    app.kodi_done_cb.assert_called_once()
    assert not app.kodi_running
