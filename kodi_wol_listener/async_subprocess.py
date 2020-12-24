"""Provides a higher level abstaction for asyncio.create_subprocess_exec"""
import logging
import asyncio

class AsyncSubprocess():  # pylint: disable=logging-fstring-interpolation
    """Asyncio based subprocess runner"""
    def __init__(self, cmd_base, abort_on_fail=True, logging_level=logging.WARNING):
        self.cmd_base = cmd_base
        self.abort_on_fail = abort_on_fail
        if abort_on_fail:
            self.abort_level = logging.ERROR
        else:
            self.abort_level = logging_level
        self.proc = None
        self.cmd = None

    async def run(self, cmd_args=b''):
        """Run a subprocess with the given addon argument

        Args:
            cmd_args (bytes) Additional argument to be added to the command string
        """
        self.cmd = self.cmd_base + b' ' + cmd_args
        self.proc = await asyncio.create_subprocess_shell(
            self.cmd,
            stdout=asyncio.subprocess.PIPE,  #pylint: disable=no-member
            stderr=asyncio.subprocess.PIPE)  #pylint: disable=no-member

    async def wait_completed(self):
        """Return result from running process, wait if process is still executing

        Returns:
            (bytes) The output from the executed process
        """
        stdout, stderr = await self.proc.communicate()
        self._handle_subprocess_return(self.proc.returncode, stdout, stderr)
        self.proc = None
        self.cmd = None
        return stdout

    async def run_wait(self, cmd_args=b''):
        """Run process and return output, ewait until process has completed

        Args:
            cmd_args (bytes) Additional argument to be added to the command string
        Returns:
            (bytes) The output from the executed process
        """
        await self.run(cmd_args)
        return await self.wait_completed()

    def _handle_subprocess_return(self, returncode, stdout, stderr):
        """Error handling method, raises OSError exception in case of abort_on_fail

        Args:
            returncode (int) Return code from process execution
            stdout (bytes) Output from process execution
            stderr (bytes) Error output from process execution
        """
        if returncode != 0:
            logging.log(self.abort_level,
                        f"subprocess {self.cmd} exited with error code {returncode}")
            if stdout:
                logging.log(self.abort_level, f'[stdout]\n{stdout.decode()}')
            if stderr:
                logging.log(self.abort_level, f'[stderr]\n{stderr.decode()}')
            if self.abort_on_fail:
                raise OSError(f"Error when executing command {self.cmd}: {stderr.decode()}")
