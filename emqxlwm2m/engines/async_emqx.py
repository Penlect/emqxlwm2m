"""Async EMQx LwM2M Backend"""

# Built-in
import asyncio
import collections
import json
import logging
import re
import weakref

# PyPI
from asyncio_mqtt import Client
from subpub import AsyncSubPub
from . import emqx

# Package
from emqxlwm2m import lwm2m


class EMQxQueue(asyncio.Queue):
    async def get(self, timeout=None):
        if timeout is None:
            return await super().get()
        try:
            return await asyncio.wait_for(super().get(), timeout)
        except asyncio.TimeoutError:
            raise asyncio.QueueEmpty()

    def get_nowait(self):
        return super().get_nowait()[1]


class EMQxEngine:
    """EMQxEngine handles EMQx MQTT traffic asynchronously."""

    def __init__(
        self,
        client: Client,
        topics: emqx.EMQxTopics = None,
        ep_factory=lwm2m.AsyncEndpoint,
        timeout=None,
        max_subs=float("inf"),
        qos=0,
    ):
        """Initialization of EMQxEngine"""
        self.log = logging.getLogger(self.__class__.__name__)
        self.req_id = emqx.ReqIDSequence(locked=False)

        self.sp = AsyncSubPub()
        if topics is None:
            topics = emqx.EMQxTopics()
        self.topics = topics
        self.ep_factory = ep_factory
        self.timeout = timeout
        self.max_subs = max_subs
        self.qos = qos

        # If set, indicates that we have connected at least once to
        # EMQx.
        self.connected_once = asyncio.Event()
        # If set, indicates that we don't need to unsubscribe because
        # we have already disconnected.
        self.exit_done = asyncio.Event()

        self._subscriptions_lock = asyncio.Lock()
        # key = endpoint, value = ref count
        self._subscriptions = collections.Counter()

        # Setup MQTT client last
        self.client: Client = client
        self.client._client.enable_logger(logging.getLogger("EMQxMQTT"))

    @classmethod
    def via_mqtt(
        cls,
        topics: emqx.EMQxTopics = None,
        timeout=None,
        max_subs=float("inf"),
        qos=0,
        **conn_kwargs,
    ):
        c = Client(**conn_kwargs)
        return cls(c, topics, timeout=timeout, max_subs=max_subs, qos=qos)

    async def __aenter__(self):
        await self.client.connect(timeout=self.timeout)
        self.main = asyncio.create_task(self.start())
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        self.main.cancel()
        await self.client.__aexit__(exc_type, exc_value, traceback)
        await self.exit_done.wait()

    async def start(self):
        self.log.debug("Command loop starting")
        topic = r"request/(?P<req_id>\d+)"
        self.log.debug("Subscribing to %r", topic)
        self.q = q = await self.sp.subscribe(topic)
        cmd = asyncio.create_task(self.commands(q))
        try:
            async with self.client.unfiltered_messages() as messages:
                async for message in messages:
                    await self.on_message(None, None, message)
        finally:  # Todo
            cmd.cancel()
            self.exit_done.set()

    def stop(self):
        self.q.put((None, None))

    async def commands(self, q):
        """Translate commands between EMQx MQTT and internal subpub"""
        while True:
            try:
                match: re.Match
                match, req = await q.get()
            except asyncio.QueueEmpty:
                continue
            else:
                if match is None:
                    break
                self.log.debug("Received request: %r", req)
                endpoint = req.ep
                payload = emqx.request_to_json(req, match.groups()[0])
                self.log.debug("Publish to %r. Payload: %r", endpoint, payload)
                topic = self.topics.topic_dn.format(endpoint=endpoint)
                await self.client.publish(
                    topic, payload.encode(), qos=self.qos
                )
        self.log.debug("Command loop completed")

    async def subscribe(self, endpoint) -> int:
        """Subscribe to `endpoint` on EMQx MQTT"""
        async with self._subscriptions_lock:
            topic = self.topics.topic_all_ep.format(endpoint=endpoint)
            if topic not in self._subscriptions:
                self.log.debug("Subscribing to %r", topic)
                if len(self._subscriptions) >= self.max_subs:
                    raise Exception("Max number of subscriptions reached!")
                await self.client.subscribe(topic, qos=self.qos)
            self._subscriptions[topic] += 1
            return self._subscriptions[topic]

    async def subscribe_all(self):
        """Subscribe to all persisted topics on EMQx MQTT (onconnect)"""
        async with self._subscriptions_lock:
            for topic in self._subscriptions:
                self.log.debug("Subscribing to %r", topic)
                await self.client.subscribe(topic, qos=self.qos)

    async def unsubscribe(self, endpoint) -> int:
        """Unsubscribe to `endpoint` on EMQx MQTT"""
        async with self._subscriptions_lock:
            topic = self.topics.topic_all_ep.format(endpoint=endpoint)
            if topic in self._subscriptions:
                self._subscriptions[topic] -= 1
                if self._subscriptions[topic] <= 0:
                    del self._subscriptions[topic]
                    if not self.exit_done.is_set():
                        self.log.debug("Unsubscribing to %r", topic)
                        await self.client.unsubscribe(topic)
            return self._subscriptions[topic]

    async def unsubscribe_all(self):
        """Unsubscribe to all persisted topics on EMQx MQTT"""
        async with self._subscriptions_lock:
            for topic in self._subscriptions:
                self.log.debug("Unsubscribing to %r", topic)
                await self.client.unsubscribe(topic)
            self._subscriptions = collections.Counter()

    # def on_connect(self, client, userdata, flags, rc):
    #     """Callback when EMQx MQTT connection is established"""
    #     self.log.debug("OnConnect")
    #     await self.subscribe_all()

    async def on_message(self, client, userdata, msg: "MQTTMessage"):
        """Callback when EMQx MQTT message is received"""
        try:
            # This callback must never fail silently. Do the actual
            # work in `_on_message` and log traceback here.
            await self._on_message(client, msg)
        except Exception:
            self.log.exception("Error in on_message, %r", msg)

    async def _on_message(self, _: Client, msg: "MQTTMessage"):
        """Route EMQx MQTT payload on internal subpub topic"""
        self.log.debug(
            "Received on %r. Payload: %r", msg.topic, msg.payload.decode()
        )
        direction = "uplink" if "up" in msg.topic else "downlink"
        endpoint = self.topics.parse_endpoint(msg.topic)
        payload = json.loads(msg.payload.decode())
        message = emqx.payload_to_message(direction, endpoint, payload)
        topic = emqx.publish_topic(message, payload.get("reqID"))
        self.log.debug("Publish to %r. Message: %r", topic, message)
        await self.sp.publish(topic, message)

    async def send(self, request: lwm2m.Request, timeout=None):
        self.log.debug("Send request %r", request)
        if not isinstance(request, lwm2m.Request):
            raise TypeError(request)
        req_id = next(self.req_id)
        topic_resp = fr"{request.ep}/Uplink/Response/\w+/{req_id}"
        self.log.debug("Subscribe to %r", topic_resp)
        q = await self.sp.subscribe(topic_resp)
        if isinstance(request, lwm2m.ObserveRequest):
            # Special case, prepare queue
            t_notify = f"{request.ep}/Uplink/Event/Notification/{req_id}"
            self.log.debug("Subscribe to %r", t_notify)
            try:
                queue = request.queue
            except AttributeError:
                queue = EMQxQueue()
            q_notify = await self.sp.subscribe(t_notify, queue=queue)
        topic = f"request/{req_id}"
        self.log.debug("Publish to %r. Message: %r", topic, request)
        await self.sp.publish(topic, request)
        try:
            _, resp = await asyncio.wait_for(q.get(), timeout)
        except asyncio.TimeoutError:
            raise lwm2m.NoResponseError(request) from None
        finally:
            self.log.debug("Unsubscribe to %r", topic_resp)
            await self.sp.unsubscribe(topic_resp)
        resp.dt = resp.timestamp - request.timestamp
        if isinstance(request, lwm2m.ObserveRequest):
            # Special case, return queue as well
            resp.notifications = q_notify
        return resp

    async def recv(self, endpoint: str, message_types, queue=None):
        self.log.debug("Recv %r: %r", endpoint, message_types)
        if queue is None:
            queue = EMQxQueue()
        if message_types:
            topics = [
                endpoint + "/" + emqx.type_topic(mt) for mt in message_types
            ]
        else:
            topics = [endpoint]
        topics.sort(key=len)
        topic = "|".join(topics)
        self.log.debug("Subscribe to %r", topic)
        return await self.sp.subscribe(topic, queue=queue)

    def ep_unsubscribe(self, endpoint):
        if not self.exit_done.is_set():
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                pass
            else:
                loop.create_task(self.unsubscribe(endpoint))

    async def endpoint(self, endpoint, timeout=None, **kwargs):
        self.log.debug("Endpoint requested: %r", endpoint)
        if timeout is None:
            timeout = self.timeout
        await self.subscribe(endpoint)
        ep = self.ep_factory(endpoint, timeout=timeout, **kwargs)
        ep.engine = self
        weakref.finalize(ep, self.ep_unsubscribe, endpoint)
        return ep
