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
        app.exit_future.set_result(
            AssertionError(f"The signal {sig.name} is expected to be handled by app"))
    prev_handler = signal.signal(sig, sig_handler)
    yield app, sig
    signal.signal(sig, prev_handler)

@pytest.mark.parametrize('app_signal_handler',
                         [signal.SIGINT, signal.SIGTERM],
                         indirect=['app_signal_handler'])
@pytest.mark.asyncio
async def test_graceful_signals_new(app_signal_handler, event_loop):
    import os
    import asyncio
    app, sig = app_signal_handler
    event_loop.call_later(0.01, os.kill, os.getpid(), sig)
    await asyncio.wait_for(app.main(0), 0.5, loop=event_loop)
