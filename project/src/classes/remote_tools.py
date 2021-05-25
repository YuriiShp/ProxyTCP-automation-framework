import time
import logging

from pyats.topology import Device

from src.classes.troubleshooting import retry_on_unicon_error


_log = logging.getLogger(__name__)
_log.setLevel(logging.INFO)


class SeleniumGrid:
    """Connection manager for remote selenium server."""

    def __init__(self, device: Device, logfile: str = None):
        self._device = device
        self._loghead = f"SeleniumGrid@{device.name}"
        self._logfile = logfile

    @retry_on_unicon_error
    def start(self):
        command = "docker-compose start"
        self._device.connect(alias="grid", logfile=self._logfile)
        self._device.grid.execute("docker-compose start")
        time.sleep(10)  # temporary solution
        _log.info(f"{self._loghead} - started via CLI: {command}")

    @retry_on_unicon_error
    def restart(self):
        self._device.grid.execute("docker-compose restart")
        time.sleep(10)  # temporary solution
        _log.info(f"{self._loghead} - restarted")

    @retry_on_unicon_error
    def is_alive(self):
        self._device.grid.execute("echo -ne '\n'")
        pid = self._device.grid.execute("pidof java")
        status = "ON" if pid else "OFF"
        _log.info(f"{self._loghead} - check status: {status}")
        return bool(pid)

    @retry_on_unicon_error
    def stop(self):
        self._device.grid.execute("docker-compose stop")
        self._device.grid.disconnect()
        _log.info(f"{self._loghead} - disconnected")
