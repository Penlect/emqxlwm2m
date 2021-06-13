# pylint: disable=maybe-no-member

# Built-in
import logging
import unittest
from unittest.mock import MagicMock, AsyncMock

# Package
from emqxlwm2m import lwm2m
from emqxlwm2m.oma import Device
from emqxlwm2m.engines.emqx import EMQxEngine
from emqxlwm2m.engines.async_emqx import EMQxEngine as AsyncEMQxEngine

logging.basicConfig(level=logging.DEBUG)
EP = "my:endpoint"


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
        self.assertEqual(self.ep[Device].path, "/3")
        self.assertEqual(self.ep[Device][0].path, "/3/0")
        self.assertEqual(self.ep[Device][1].path, "/3/1")
        self.assertEqual(self.ep[Device][2].model_number.path, "/3/2/1")

    def test_read_obj(self):
        self.ep[Device].read()
        req = lwm2m.ReadRequest(EP, "/3")
        self.engine.send.assert_called_once_with(req, None)

    def test_read_instance(self):
        self.ep[Device][0].read()
        req = lwm2m.ReadRequest(EP, "/3/0")
        self.engine.send.assert_called_once_with(req, None)

    def test_read(self):
        self.ep[Device].manufacturer.read()
        req = lwm2m.ReadRequest(EP, "/3/0/0")
        self.engine.send.assert_called_once_with(req, None)

    def test_discover(self):
        self.ep[Device].model_number.discover()
        req = lwm2m.DiscoverRequest(EP, "/3/0/1")
        self.engine.send.assert_called_once_with(req, None)

    def test_write(self):
        self.ep[Device][1].current_time.write(123)
        req = lwm2m.WriteRequest(EP, {"/3/1/13": 123})
        self.engine.send.assert_called_once_with(req, None)

    def test_write_batch(self):
        self.ep[Device][0].write({"13": 123, "14": "+2"})
        req = lwm2m.WriteRequest(EP, {"/3/0/13": 123, "/3/0/14": "+2"})
        self.engine.send.assert_called_once_with(req, None)

    def test_write_attr(self):
        self.ep[Device][0].battery_level.write_attr(pmin=10, gt=123)
        req = lwm2m.WriteAttrRequest(EP, "/3/0/9", pmin=10, gt=123)
        self.engine.send.assert_called_once_with(req, None)

    def test_execute(self):
        self.ep[Device].reset_error_code.execute("")
        req = lwm2m.ExecuteRequest(EP, "/3/0/12", "")
        self.engine.send.assert_called_once_with(req, None)

    def test_create(self):
        self.ep[Device][2].create({"13": 123, "14": "+2"})
        req = lwm2m.CreateRequest(EP, {"/3/2/13": 123, "/3/2/14": "+2"})
        self.engine.send.assert_called_once_with(req, None)

    def test_delete(self):
        self.ep[Device][2].delete()
        req = lwm2m.DeleteRequest(EP, "/3/2")
        self.engine.send.assert_called_once_with(req, None)

    def test_observe(self):
        self.ep[Device].timezone.observe()
        req = lwm2m.ObserveRequest(EP, "/3/0/15")
        self.engine.send.assert_called_once_with(req, None)

    def test_cancel_observe(self):
        self.ep[Device].timezone.cancel_observe()
        req = lwm2m.CancelObserveRequest(EP, "/3/0/15")
        self.engine.send.assert_called_once_with(req, None)

    def test_temporary_observe(self):
        req1 = lwm2m.ObserveRequest(EP, "/3/0/15")
        with self.ep[Device].timezone.temporary_observe() as resp:
            self.assertTrue(hasattr(resp, "notifications"))
            self.engine.send.assert_called_once_with(req1, None)
        req2 = lwm2m.CancelObserveRequest(EP, "/3/0/15")
        self.engine.send.assert_called_with(req2, None)


class TestAsyncDevice(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        print()
        c = AsyncMock()
        c._client = MagicMock()
        self.engine = AsyncEMQxEngine(c)
        self.engine.send = AsyncMock()
        self.engine.send.side_effect = MagicMock()
        self.ep = await self.engine.endpoint(EP)

    async def asyncTearDown(self):
        del self.ep  # Make sure weakref callback is called before loop close

    async def test_path(self):
        self.assertEqual(self.ep[Device].path, "/3")
        self.assertEqual(self.ep[Device][0].path, "/3/0")
        self.assertEqual(self.ep[Device][1].path, "/3/1")
        self.assertEqual(self.ep[Device][2].model_number.path, "/3/2/1")

    async def test_read_obj(self):
        await self.ep[Device].read()
        req = lwm2m.ReadRequest(EP, "/3")
        self.engine.send.assert_awaited_once_with(req, None)

    async def test_read_instance(self):
        await self.ep[Device][0].read()
        req = lwm2m.ReadRequest(EP, "/3/0")
        self.engine.send.assert_awaited_once_with(req, None)

    async def test_read(self):
        await self.ep[Device].manufacturer.read()
        req = lwm2m.ReadRequest(EP, "/3/0/0")
        self.engine.send.assert_awaited_once_with(req, None)

    async def test_discover(self):
        await self.ep[Device].model_number.discover()
        req = lwm2m.DiscoverRequest(EP, "/3/0/1")
        self.engine.send.assert_awaited_once_with(req, None)

    async def test_write(self):
        await self.ep[Device][1].current_time.write(123)
        req = lwm2m.WriteRequest(EP, {"/3/1/13": 123})
        self.engine.send.assert_awaited_once_with(req, None)

    async def test_write_batch(self):
        await self.ep[Device][0].write({"13": 123, "14": "+2"})
        req = lwm2m.WriteRequest(EP, {"/3/0/13": 123, "/3/0/14": "+2"})
        self.engine.send.assert_awaited_once_with(req, None)

    async def test_write_attr(self):
        await self.ep[Device][0].battery_level.write_attr(pmin=10, gt=123)
        req = lwm2m.WriteAttrRequest(EP, "/3/0/9", pmin=10, gt=123)
        self.engine.send.assert_awaited_once_with(req, None)

    async def test_execute(self):
        await self.ep[Device].reset_error_code.execute("")
        req = lwm2m.ExecuteRequest(EP, "/3/0/12", "")
        self.engine.send.assert_awaited_once_with(req, None)

    async def test_create(self):
        await self.ep[Device][2].create({"13": 123, "14": "+2"})
        req = lwm2m.CreateRequest(EP, {"/3/2/13": 123, "/3/2/14": "+2"})
        self.engine.send.assert_awaited_once_with(req, None)

    async def test_delete(self):
        await self.ep[Device][2].delete()
        req = lwm2m.DeleteRequest(EP, "/3/2")
        self.engine.send.assert_awaited_once_with(req, None)

    async def test_observe(self):
        await self.ep[Device].timezone.observe()
        req = lwm2m.ObserveRequest(EP, "/3/0/15")
        self.engine.send.assert_awaited_once_with(req, None)

    async def test_cancel_observe(self):
        await self.ep[Device].timezone.cancel_observe()
        req = lwm2m.CancelObserveRequest(EP, "/3/0/15")
        self.engine.send.assert_awaited_once_with(req, None)

    async def test_temporary_observe(self):
        req1 = lwm2m.ObserveRequest(EP, "/3/0/15")
        async with self.ep[Device].timezone.temporary_observe() as resp:
            self.assertTrue(hasattr(resp, "notifications"))
            self.engine.send.assert_awaited_once_with(req1, None)
        req2 = lwm2m.CancelObserveRequest(EP, "/3/0/15")
        self.engine.send.assert_awaited_with(req2, None)
