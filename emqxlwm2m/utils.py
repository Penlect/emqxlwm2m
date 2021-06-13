"""High level functions and utilities"""

# pylint: disable=maybe-no-member

# Built-in
import asyncio
import time
import queue
import datetime as dt

# Package
import emqxlwm2m
from emqxlwm2m.lwm2m import Endpoint, AsyncEndpoint
from emqxlwm2m.oma import LwM2MServer, Device, FirmwareUpdate


def trigger_update(ep: Endpoint, timeout=None, *, iid=0):
    q = ep.updates()
    resp = ep[LwM2MServer][iid].registration_update_trigger.execute(
        timeout=timeout
    )
    resp.check()
    return q.get(timeout=timeout)


def reboot(ep: Endpoint, block=True, timeout=None, *, iid=0):
    ep.log.info("Rebooting")
    t0 = dt.datetime.now()
    if block:
        q = ep.registrations()
    resp = ep[Device][iid].reboot.execute(timeout=timeout)
    resp.check()
    ep.log.info("Execute response: %r", resp.code)
    if block:
        ep.log.info("Waiting for registration")
        packet = q.get()
        t1 = packet.timestamp
        ep.log.info("Registration received. Reboot duration: %s", t1 - t0)


class FirmwareUpdateError(Exception):
    pass


class DownloadError(FirmwareUpdateError):
    pass


class UpdateError(FirmwareUpdateError):
    pass


def firmware_update(
    ep: Endpoint,
    package_uri: str,
    wait: bool = True,
    reg_timeout: float = None,
    *,
    iid=0,
    exec_ok=None,
) -> int:
    ep.log.info("Firmware update started.")

    # Enums used for checking state.
    state = FirmwareUpdate.state.Enum
    result = FirmwareUpdate.update_result.Enum

    # Firmware Update Object
    obj = ep[FirmwareUpdate][iid]

    # Download firmware.
    ep.log.info("Writing package uri: %r", package_uri)
    resp = obj.package_uri.write(package_uri)
    resp.check()
    t0 = dt.datetime.now()

    while True:

        time.sleep(15)
        resp = obj.state.read(timeout=15, retry=4)

        if resp.value == state.DOWNLOADING:
            ep.log.info("Downloading ...")
        elif resp.value == state.DOWNLOADED:
            t1 = dt.datetime.now()
            ep.log.info("Firmware downloaded after %s", t1 - t0)
            break
        elif resp.value == state.UPDATING:
            raise FirmwareUpdateError(f"Unexpected state: {resp.value}")
        elif resp.value == state.IDLE:
            resp = obj.update_result.read()
            raise DownloadError(resp.value)
        else:
            raise FirmwareUpdateError(f"Unexpected state: {resp.value}")

    # Update firmware
    ep.log.debug("Sleeping for 3 seconds")
    time.sleep(3)
    if callable(exec_ok) and not exec_ok(ep):
        ep.log.debug("Aborting because NOK exec_ok")
        return None
    if wait:
        reg_q = ep.registrations()
        t0 = dt.datetime.now()

    # When in Downloaded state, and the executable Resource Update is
    # triggered, the state changes to Updating.  If the Update
    # Resource failed, the state returns at Downloaded.  If performing
    # the Update Resource was successful, the state changes from
    # Updating to Idle.
    ep.log.info("Firmware update execute")
    try:
        resp = obj.update.execute()
        resp.check()
    except emqxlwm2m.NoResponseError:
        ep.log.warning("No response after execute")

    if not wait:
        return None
    ep.log.info("Waiting for registration")
    try:
        reg_q.get(timeout=reg_timeout)
    except queue.Empty:
        raise FirmwareUpdateError(
            "Timeout when waiting for registration"
        ) from None
    t1 = dt.datetime.now()
    ep.log.info("Registration received after %s", t1 - t0)
    ep.log.debug("Sleeping for 3 seconds")
    time.sleep(3)

    # Check status of firmware
    ep.log.debug("Reading update result")
    resp = obj.update_result.read(timeout=10, retry=1)
    if resp.value == result.UPDATE_SUCCESSFUL:
        ep.log.info("Firmware update result: %r", resp.value)
        return True
    raise UpdateError(resp.value)


async def async_firmware_update(
    ep: AsyncEndpoint,
    package_uri: str,
    wait: bool = True,
    reg_timeout: float = None,
    *,
    iid=0,
    exec_ok=None,
) -> int:
    ep.log.info("Firmware update started.")

    # Enums used for checking state.
    state = FirmwareUpdate.state.Enum
    result = FirmwareUpdate.update_result.Enum

    # Firmware Update Object
    obj = ep[FirmwareUpdate][iid]

    # Download firmware.
    ep.log.info("Writing package uri: %r", package_uri)
    resp = await obj.package_uri.write(package_uri)
    resp.check()
    t0 = dt.datetime.now()

    while True:

        await asyncio.sleep(15)
        resp = await obj.state.read(timeout=15, retry=4)

        if resp.value == state.DOWNLOADING:
            ep.log.info("Downloading ...")
        elif resp.value == state.DOWNLOADED:
            t1 = dt.datetime.now()
            ep.log.info("Firmware downloaded after %s", t1 - t0)
            break
        elif resp.value == state.UPDATING:
            raise FirmwareUpdateError(f"Unexpected state: {resp.value}")
        elif resp.value == state.IDLE:
            resp = await obj.update_result.read()
            raise DownloadError(resp.value)
        else:
            raise FirmwareUpdateError(f"Unexpected state: {resp.value}")

    # Update firmware
    ep.log.debug("Sleeping for 3 seconds")
    await asyncio.sleep(3)
    if callable(exec_ok) and not await exec_ok(ep):
        ep.log.debug("Aborting because NOK exec_ok")
        return None
    if wait:
        reg_q = await ep.registrations()
        t0 = dt.datetime.now()

    # When in Downloaded state, and the executable Resource Update is
    # triggered, the state changes to Updating.  If the Update
    # Resource failed, the state returns at Downloaded.  If performing
    # the Update Resource was successful, the state changes from
    # Updating to Idle.
    ep.log.info("Firmware update execute")
    try:
        resp = await obj.update.execute()
        resp.check()
    except emqxlwm2m.NoResponseError:
        ep.log.warning("No response after execute")

    if not wait:
        return None
    ep.log.info("Waiting for registration")
    try:
        await reg_q.get(timeout=reg_timeout)
    except asyncio.QueueEmpty:
        raise FirmwareUpdateError(
            "Timeout when waiting for registration"
        ) from None
    t1 = dt.datetime.now()
    ep.log.info("Registration received after %s", t1 - t0)
    ep.log.debug("Sleeping for 3 seconds")
    await asyncio.sleep(3)

    # Check status of firmware
    ep.log.debug("Reading update result")
    resp = await obj.update_result.read(timeout=10, retry=1)
    if resp.value == result.UPDATE_SUCCESSFUL:
        ep.log.info("Firmware update result: %r", resp.value)
        return True
    raise UpdateError(resp.value)
