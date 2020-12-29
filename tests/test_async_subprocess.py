import pytest

@pytest.mark.asyncio
async def test_exec_ok():
    from kodi_wol_listener.async_subprocess import AsyncSubprocess
    import sys
    python = AsyncSubprocess(bytes(sys.executable, 'ASCII'))
    hello = await python.run_wait(b'-c "print(\'Hello World\')"')
    assert hello == b'Hello World\n'

@pytest.mark.asyncio
async def test_exec_bad():
    from kodi_wol_listener.async_subprocess import AsyncSubprocess
    import sys
    prog=b"import sys\n" \
         b"print('Hello', file=sys.stdout)\n" \
         b"print('World', file=sys.stderr)\n" \
         b"sys.exit(1)"
    python = AsyncSubprocess(bytes(sys.executable, 'ASCII'))
    with pytest.raises(OSError):
        await python.run_wait(b"-c \"" + prog + b"\"")
    python = AsyncSubprocess(bytes(sys.executable, 'ASCII'), abort_on_fail=False)
    await python.run_wait(b"-c \"" + prog + b"\"")
