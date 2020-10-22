"""High level functions and utilities"""

# pylint: disable=maybe-no-member

# Built-in
import logging
import time
import queue
import datetime as dt

# Package
import emqxlwm2m
from emqxlwm2m.lwm2m import Endpoint
from emqxlwm2m.oma import (
    LwM2MServer,
    Device,
    FirmwareUpdate
)


def reboot(endpoint: Endpoint, block=True, timeout=None, *, iid=0):
    log = logging.getLogger(endpoint.endpoint)
    log.info('Reboot')
    t0 = dt.datetime.now()
    if block:
        q = endpoint.registrations()
    resp = endpoint[Device][iid].reboot.execute(timeout=timeout)
    log.info('Execute response: %r', resp)
    if block:
        log.info('Waiting for registration')
        packet = q.get()
        t1 = packet.timestamp
        log.info('Registration received. Reboot duration: %s', t1 - t0)


def firmware_update(endpoint: Endpoint, package_uri: str,
                    wait=True, reg_timeout=None, *, iid=0) -> int:
    log = logging.getLogger(endpoint.endpoint)
    client = endpoint[FirmwareUpdate][iid]
    # Download firmware
    log.info('Firmware update started.')
    log.info('Writing package uri: %r', package_uri)
    resp = client.package_uri.write(package_uri)
    log.info('Write response: %r', resp)
    while True:
        log.debug('Sleeping for 10 seconds')
        time.sleep(10)
        log.debug('Reading state')
        state = client.state.read()
        if state.value == FirmwareUpdate.state.Enum.DOWNLOADED:
            log.info('Download status: %r', state.value)
            break
        elif state.value != FirmwareUpdate.state.Enum.DOWNLOADING:
            log.error('Download status: %r', state.value)
            return False

    # Update firmware
    log.debug('Sleeping for 3 seconds')
    time.sleep(3)
    q = endpoint.registrations()
    log.info('Firmware update execute')
    t0 = dt.datetime.now()
    try:
        resp = client.update.execute()
    except emqxlwm2m.NoResponseError:
        pass
    else:
        log.info('Execute response: %r', resp)
    if not wait:
        return
    log.info('Waiting for registration')
    try:
        q.get(timeout=reg_timeout)
    except queue.Empty:
        log.error('Timeout when waiting for registration')
        return False
    t1 = dt.datetime.now()
    log.info('Registration received after %s', t1 - t0)
    log.debug('Sleeping for 3 seconds')
    time.sleep(3)

    # Check status of firmware
    log.debug('Reading update result')
    result = client.update_result.read()
    if result.value == FirmwareUpdate.update_result.Enum.UPDATE_SUCCESSFUL:
        log.info('Firmware update result: %r', result.value)
        return True
    log.error('Firmware update result: %r', result.value)
    return False


def trigger_update(endpoint: Endpoint, block=True, timeout=None, *, iid=0):
    log = logging.getLogger(endpoint.endpoint)
    log.info('Update')
    t0 = dt.datetime.now()
    if block:
        q = endpoint.updates()
    resp = endpoint[LwM2MServer][iid].registration_update_trigger.execute(
        timeout=timeout)
    log.info('Execute response: %r', resp)
    packet = None
    if block:
        log.info('Waiting for update')
        packet = q.get(timeout=timeout)
        t1 = packet.timestamp
        log.info('Update received. Update duration: %s', t1 - t0)
    return packet
