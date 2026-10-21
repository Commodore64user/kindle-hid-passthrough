import asyncio
import sys
from pathlib import Path

import pytest

pytest.importorskip('bumble')
sys.path.insert(0, str(Path(__file__).parent.parent / 'kindle_hid_passthrough'))

import ble
from bumble.hci import HCI_COMMAND_DISALLOWED_ERROR, HCI_Error


class FakeDevice:
    def __init__(self, failures):
        self.failures = failures
        self.starts = 0
        self.address_resolver = None

    def on(self, *a):
        pass

    def remove_listener(self, *a):
        pass

    async def start_scanning(self, **kw):
        self.starts += 1
        if self.starts <= self.failures:
            raise HCI_Error(HCI_COMMAND_DISALLOWED_ERROR)

    async def stop_scanning(self, **kw):
        pass


def scan_host(failures):
    host = ble.BLEMixin()
    host.device = FakeDevice(failures)
    host._radio_lock = asyncio.Lock()
    host.BLE_SCAN_START_RETRY_DELAY = 0
    return host


def test_scan_retries_while_the_controller_is_still_initiating():
    host = scan_host(failures=2)
    assert asyncio.run(host._ble_scan_for_rotated(set(), 0.01)) is None
    assert host.device.starts == 3  # two refusals, then a real scan window


def test_scan_gives_up_after_the_retries():
    host = scan_host(failures=99)
    assert asyncio.run(host._ble_scan_for_rotated(set(), 0.01)) is None
    assert host.device.starts == host.BLE_SCAN_START_RETRIES + 1
