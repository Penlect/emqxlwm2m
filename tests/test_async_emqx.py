# Built-in
import asyncio
import contextlib
import functools
import logging
import itertools
import json
import unittest
import threading
import queue
from unittest.mock import MagicMock, AsyncMock


# Package
from emqxlwm2m.engines.async_emqx import EMQxEngine
from emqxlwm2m import lwm2m

# PyPI
import asyncio_mqtt

logging.basicConfig(level=logging.DEBUG)
EP = "my:endpoint"

DATA = list()


def load_data():
    global DATA
    with open("tests/testdata/reqresp.txt", "r") as f:
        sequence = list()
        for line in f:
            if line.startswith("#"):
                continue
            line = line.strip()
            if line in {"EOF", ""}:
                if sequence:
                    DATA.append(sequence)
                    sequence = list()
                continue
            line = line.replace("__ep__", EP)
            if not sequence:
                item = json.loads(line)
                sequence.append(item)
            item = line.strip()
            sequence.append(item)


async def broker(engine: EMQxEngine, topic, payload, **kw):
    print("MQTT", topic, payload)
    key = json.loads(payload.decode())
    for seq in DATA:
        if key == seq[0]:
            for i, data in enumerate(seq[1:], start=1):
                msg = MagicMock()
                if i == 1:
                    msg.topic = f"{engine.topics.mountpoint}/{EP}/dn"
                else:
                    msg.topic = f"{engine.topics.mountpoint}/{EP}/up"
                msg.payload = data.encode()
                print("MQTT", i, msg.topic, msg.payload)
                engine.client._client.on_message(None, None, msg)
            break


class TestAsyncEMQxEngine(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(self):
        load_data()

    async def asyncSetUp(self):
        print()
        c = asyncio_mqtt.Client("testhost")
        c.subscribe = AsyncMock()
        c.unsubscribe = AsyncMock()
        c.connect = AsyncMock()
        c.disconnect = AsyncMock()
        self.engine = EMQxEngine(c)
        self.engine.req_id = itertools.count()
        c.publish = functools.partial(broker, self.engine)
        # self.engine.on_connect(None, None, None, None)
        await self.engine.__aenter__()

    async def asyncTearDown(self):
        await self.engine.__aexit__(None, None, None)

    async def test_discover_request_ok(self):
        resp = await self.engine.send(
            lwm2m.DiscoverRequest(EP, "/1/0"), timeout=2
        )
        self.assertIsInstance(resp, lwm2m.DiscoverResponse)
        self.assertEqual(resp.ep, EP)
        self.assertEqual(resp.code, lwm2m.CoAPResponseCode.Content)
        self.assertEqual(resp.req_path, "/1/0")
        self.assertIn("/1/0", resp)
        resp.check()

    async def test_discover_request_nok(self):
        resp = await self.engine.send(lwm2m.DiscoverRequest(EP, "/1/123"))
        self.assertIsInstance(resp, lwm2m.DiscoverResponse)
        self.assertEqual(resp.code, lwm2m.CoAPResponseCode.NotFound)
        self.assertEqual(resp.req_path, "/1/123")
        self.assertNotIn("/1/123", resp)
        with self.assertRaises(lwm2m.ResponseError):
            resp.check()

    async def test_read_request_ok(self):
        resp = await self.engine.send(lwm2m.ReadRequest(EP, "/1/0/1"))
        self.assertIsInstance(resp, lwm2m.ReadResponse)
        self.assertEqual(resp.ep, EP)
        self.assertEqual(resp.code, lwm2m.CoAPResponseCode.Content)
        self.assertEqual(resp.req_path, "/1/0/1")
        self.assertDictEqual(dict(resp), {"/1/0/1": 60})
        resp.check()

    async def test_read_request_nok(self):
        resp = await self.engine.send(lwm2m.ReadRequest(EP, "/1/0/123"))
        self.assertIsInstance(resp, lwm2m.ReadResponse)
        self.assertEqual(resp.code, lwm2m.CoAPResponseCode.NotFound)
        self.assertEqual(resp.req_path, "/1/0/123")
        with self.assertRaises(lwm2m.ResponseError):
            resp.check()

    async def test_write_request_ok(self):
        resp = await self.engine.send(lwm2m.WriteRequest(EP, {"/1/0/1": 123}))
        self.assertIsInstance(resp, lwm2m.WriteResponse)
        self.assertEqual(resp.ep, EP)
        self.assertEqual(resp.code, lwm2m.CoAPResponseCode.Changed)
        self.assertEqual(resp.req_path, "/1/0/1")
        resp.check()

    async def test_write_attr_request_ok(self):
        resp = await self.engine.send(
            lwm2m.WriteAttrRequest(EP, "/1/0/1", 10, 20, 0, 5, 100)
        )
        self.assertIsInstance(resp, lwm2m.WriteAttrResponse)
        self.assertEqual(resp.ep, EP)
        self.assertEqual(resp.code, lwm2m.CoAPResponseCode.Changed)
        self.assertEqual(resp.req_path, "/1/0/1")
        resp.check()

    async def test_execute_request_ok(self):
        resp = await self.engine.send(lwm2m.ExecuteRequest(EP, "/3/0/4", ""))
        self.assertIsInstance(resp, lwm2m.ExecuteResponse)
        self.assertEqual(resp.ep, EP)
        self.assertEqual(resp.code, lwm2m.CoAPResponseCode.Changed)
        self.assertEqual(resp.req_path, "/3/0/4")
        resp.check()

    async def test_create_request_ok(self):
        resp = await self.engine.send(
            lwm2m.CreateRequest(EP, {"/123/1/0": "test", "/123/1/1": 321})
        )
        self.assertIsInstance(resp, lwm2m.CreateResponse)
        self.assertEqual(resp.ep, EP)
        self.assertEqual(resp.code, lwm2m.CoAPResponseCode.Created)
        self.assertEqual(resp.req_path, "/123")
        resp.check()

    async def test_delete_request_ok(self):
        resp = await self.engine.send(lwm2m.DeleteRequest(EP, "/123"))
        self.assertIsInstance(resp, lwm2m.DeleteResponse)
        self.assertEqual(resp.ep, EP)
        self.assertEqual(resp.code, lwm2m.CoAPResponseCode.Deleted)
        self.assertEqual(resp.req_path, "/123")
        resp.check()

    async def test_observe_request_ok(self):
        resp = await self.engine.send(lwm2m.ObserveRequest(EP, "/1/0/1"))
        self.assertIsInstance(resp, lwm2m.ObserveResponse)
        self.assertEqual(resp.ep, EP)
        self.assertEqual(resp.code, lwm2m.CoAPResponseCode.Content)
        self.assertEqual(resp.req_path, "/1/0/1")
        self.assertDictEqual(dict(resp), {"/1/0/1": 123})
        resp.check()
        for seq_num in range(1, 4):
            notification = await resp.notifications.get()
            self.assertIsInstance(notification, lwm2m.Notification)
            self.assertEqual(notification.ep, EP)
            self.assertEqual(notification.code, lwm2m.CoAPResponseCode.Content)
            self.assertEqual(notification.seq_num, seq_num)
            self.assertEqual(notification.req_path, "/1/0/1")
            self.assertDictEqual(dict(notification), {"/1/0/1": 100 + seq_num})
            notification.check()

    async def test_cancel_observe_request_ok(self):
        resp = await self.engine.send(lwm2m.CancelObserveRequest(EP, "/1/0/1"))
        self.assertIsInstance(resp, lwm2m.CancelObserveResponse)
        self.assertEqual(resp.ep, EP)
        self.assertEqual(resp.code, lwm2m.CoAPResponseCode.Content)
        self.assertEqual(resp.req_path, "/1/0/1")
        self.assertDictEqual(dict(resp), {"/1/0/1": 123})

    async def test_registration(self):
        q = await self.engine.recv(EP, [lwm2m.Registration])
        await self.engine.send(lwm2m.ExecuteRequest(EP, "/304", ""))
        reg = await q.get()
        self.assertIsInstance(reg, lwm2m.Registration)
        self.assertEqual(reg.ep, EP)
        self.assertEqual(reg.lwm2m, "1.0")  #
        self.assertEqual(reg.lt, 123)
        self.assertEqual(reg.alternate_path, "/")
        self.assertListEqual(list(reg), ["/1/0", "/3/0", "/5/0"])

    async def test_update(self):
        q = await self.engine.recv(EP, [lwm2m.Update])
        await self.engine.send(lwm2m.ExecuteRequest(EP, "/1/0/8", ""))
        upd = await q.get()
        self.assertIsInstance(upd, lwm2m.Update)
        self.assertEqual(upd.ep, EP)
        self.assertEqual(upd.lwm2m, "1.0")
        self.assertEqual(upd.lt, 123)
        self.assertEqual(upd.alternate_path, "/")
        self.assertListEqual(list(upd), ["/1/0", "/3/0", "/5/0"])

    async def test_notifiction(self):
        notifications = await self.engine.recv(EP, [lwm2m.Notification])
        resp = await self.engine.send(lwm2m.ObserveRequest(EP, "/1/0/1"))
        for _ in range(1, 4):
            self.assertIs(
                await notifications.get(), await resp.notifications.get()
            )

    async def test_timeout(self):
        req = lwm2m.ExecuteRequest(EP, "/123/0/1", "timeout")
        with self.assertRaises(lwm2m.NoResponseError) as error:
            await self.engine.send(req, timeout=0.001)
        self.assertIs(error.exception.args[0], req)

    async def test_recv(self):
        q_msg = await self.engine.recv(EP, [lwm2m.Message])

        q_upl = await self.engine.recv(EP, [lwm2m.Uplink])
        q_dwn = await self.engine.recv(EP, [lwm2m.Downlink])

        q_req = await self.engine.recv(EP, [lwm2m.Request])
        q_rsp = await self.engine.recv(EP, [lwm2m.Response])
        q_evt = await self.engine.recv(EP, [lwm2m.Event])

        q_reg = await self.engine.recv(EP, [lwm2m.Registration])
        q_upd = await self.engine.recv(EP, [lwm2m.Update])
        q_not = await self.engine.recv(EP, [lwm2m.Notification])

        q_rrq = await self.engine.recv(EP, [lwm2m.ReadRequest])
        q_rre = await self.engine.recv(EP, [lwm2m.ReadResponse])

        await self.engine.send(lwm2m.ReadRequest(EP, "/1/0/31"))

        a = await q_msg.get()
        self.assertIs(a, await q_dwn.get())
        self.assertIs(a, await q_req.get())
        self.assertIs(a, await q_rrq.get())

        b = await q_msg.get()
        self.assertIs(b, await q_upl.get())
        self.assertIs(b, await q_rsp.get())
        self.assertIs(b, await q_rre.get())

        c = await q_msg.get()
        self.assertIs(c, await q_upl.get())
        self.assertIs(c, await q_evt.get())
        self.assertIs(c, await q_reg.get())

        d = await q_msg.get()
        self.assertIs(d, await q_upl.get())
        self.assertIs(d, await q_evt.get())
        self.assertIs(d, await q_upd.get())

        e = await q_msg.get()
        self.assertIs(e, await q_upl.get())
        self.assertIs(e, await q_evt.get())
        self.assertIs(e, await q_not.get())

        queues = [
            q_msg,
            q_upl,
            q_dwn,
            q_req,
            q_rsp,
            q_evt,
            q_reg,
            q_upd,
            q_not,
            q_rrq,
            q_rre,
        ]
        for q in queues:
            with self.assertRaises(asyncio.QueueEmpty):
                await q.get(timeout=0.01)

    async def test_endpoint_unsubscribe(self):
        topic = f"{self.engine.topics.mountpoint}/{EP}/#"
        ep = await self.engine.endpoint(EP)
        self.engine.client.subscribe.assert_called_once_with(
            topic, qos=self.engine.qos
        )
        ep = await self.engine.endpoint(EP)  # overwrite previous variable
        self.engine.client.subscribe.assert_called_once_with(
            topic, qos=self.engine.qos
        )
        del ep
        await asyncio.sleep(0.01)
        self.engine.client.unsubscribe.assert_called_once_with(topic)

    async def test_endpoint_unsubscribe_ref_count(self):
        topic = f"{self.engine.topics.mountpoint}/{EP}/#"
        ep1 = await self.engine.endpoint(EP)
        self.engine.client.subscribe.assert_called_once_with(
            topic, qos=self.engine.qos
        )
        ep2 = await self.engine.endpoint(EP)
        self.engine.client.subscribe.assert_called_once_with(
            topic, qos=self.engine.qos
        )
        del ep1
        await asyncio.sleep(0.01)
        self.engine.client.unsubscribe.assert_not_called()
        del ep2
        await asyncio.sleep(0.01)
        self.engine.client.unsubscribe.assert_called_once_with(topic)

    async def test_engine_exit(self):
        topic = f"{self.engine.topics.mountpoint}/{EP}/#"
        ep = await self.engine.endpoint(EP)
        self.engine.client.subscribe.assert_called_once_with(
            topic, qos=self.engine.qos
        )
        await self.engine.__aexit__(None, None, None)
        self.engine.client.disconnect.assert_called_once()

    async def test_max_subs(self):
        self.engine.max_subs = 2
        ep1 = await self.engine.endpoint(EP + "1")
        ep2 = await self.engine.endpoint(EP + "2")
        with self.assertRaises(Exception):
            ep3 = await self.engine.endpoint(EP + "3")
