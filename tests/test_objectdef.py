
# pylint: disable=maybe-no-member

# Built-in
import logging
import unittest
from unittest.mock import MagicMock

# Package
from emqxlwm2m import lwm2m
from emqxlwm2m.oma import Device
from emqxlwm2m.engines.emqx import EMQxEngine

logging.basicConfig(level=logging.DEBUG)
EP = 'my:endpoint'


class TestDevice(unittest.TestCase):

    def setUp(self):
        print()
        c = MagicMock()
        self.engine = EMQxEngine(c)
        self.engine.send = MagicMock()
        self.engine.on_connect(None, None, None, None)
        self.engine.__enter__()
        self.ep = self.engine.endpoint(EP)

    def test_attributes(self):
        self.assertEqual(Device.oid, 3)
        self.assertTrue(Device.mandatory)
        self.assertFalse(Device.multiple)

    def test_path(self):
        self.assertEqual(self.ep[Device].path, '/3')
        self.assertEqual(self.ep[Device][0].path, '/3/0')
        self.assertEqual(self.ep[Device][1].path, '/3/1')
        self.assertEqual(self.ep[Device][2].model_number.path, '/3/2/1')

    def test_read(self):
        self.ep[Device].manufacturer.read()
        req = lwm2m.ReadRequest(EP, '/3/0/0')
        self.engine.send.assert_called_once_with(req, None)

    def test_discover(self):
        self.ep[Device].model_number.discover()
        req = lwm2m.DiscoverRequest(EP, '/3/0/1')
        self.engine.send.assert_called_once_with(req, None)

    def test_write(self):
        self.ep[Device][1].current_time.write(123)
        req = lwm2m.WriteRequest(EP, {'/3/1/13': 123})
        self.engine.send.assert_called_once_with(req, None)

    def test_write_batch(self):
        self.ep[Device][0].write_batch({'13': 123, '14': '+2'})
        req = lwm2m.WriteRequest(EP, {'/3/0/13': 123, '/3/0/14': '+2'})
        self.engine.send.assert_called_once_with(req, None)

    def test_write_attr(self):
        self.ep[Device][0].battery_level.write_attr(pmin=10, gt=123)
        req = lwm2m.WriteAttrRequest(EP, '/3/0/9', pmin=10, gt=123)
        self.engine.send.assert_called_once_with(req, None)

    def test_execute(self):
        self.ep[Device].reset_error_code.execute('')
        req = lwm2m.ExecuteRequest(EP, '/3/0/12', '')
        self.engine.send.assert_called_once_with(req, None)

    def test_create(self):
        self.ep[Device][2].create({'13': 123, '14': '+2'})
        req = lwm2m.CreateRequest(EP, {'/3/2/13': 123, '/3/2/14': '+2'})
        self.engine.send.assert_called_once_with(req, None)

    def test_delete(self):
        self.ep[Device][2].delete()
        req = lwm2m.DeleteRequest(EP, '/3/2')
        self.engine.send.assert_called_once_with(req, None)

    def test_observe(self):
        self.ep[Device].timezone.observe()
        req = lwm2m.ObserveRequest(EP, '/3/0/15')
        self.engine.send.assert_called_once_with(req, None)

    def test_cancel_observe(self):
        self.ep[Device].timezone.cancel_observe()
        req = lwm2m.CancelObserveRequest(EP, '/3/0/15')
        self.engine.send.assert_called_once_with(req, None)
