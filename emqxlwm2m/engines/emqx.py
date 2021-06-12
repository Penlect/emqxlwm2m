"""EMQx LwM2M Backend"""

# Built-in
import collections
import contextlib
import json
import random
import threading
import logging
import queue as queuemod
import re
import enum
import weakref

# PyPI
from paho.mqtt.client import Client, MQTTMessage
from subpub import SubPub

# Package
from emqxlwm2m import lwm2m


# Should only exist one instance of this one
class ReqIDSequence:
    """Generate unique EMQx request IDs."""

    def __init__(self, req_id_min=0, req_id_max=10000, locked=True):
        """Initialization of ReqIDSequence"""
        self._lock = threading.Lock() if locked else contextlib.nullcontext()
        self._req_id = random.randint(req_id_min, req_id_max)
        self.req_id_min = req_id_min
        self.req_id_max = req_id_max

    def __iter__(self):
        return self

    def __next__(self) -> int:
        with self._lock:
            self._req_id += 1
            if self._req_id > self.req_id_max:
                self._req_id = self.req_id_min
            return self._req_id


def get_emqx_type_name(value):
    if isinstance(value, enum.Enum):
        value = value.value
    if isinstance(value, bool):
        type_ = "Boolean"
        value = str(value).lower()  # Must be lower case
    elif isinstance(value, int):
        type_ = "Integer"
    elif isinstance(value, float):
        type_ = "Float"
    elif isinstance(value, str):
        type_ = "String"
    else:
        raise ValueError(r"Don\'t know emqx type for {value!r}")
    return type_, value


def none_or_str(value):
    if value is None:
        return value
    return str(value)


def request_to_json(request: lwm2m.Message, req_id: int) -> str:
    """Convert LwM2M message to EMQx MQTT JSON payload"""
    if not isinstance(request, lwm2m.Request):
        raise TypeError(f"{request!r} is not an instance of {lwm2m.Request!r}")
    payload = dict()
    payload["reqID"] = int(req_id)
    if isinstance(request, lwm2m.DiscoverRequest):
        payload["msgType"] = "discover"
        payload["data"] = {"path": request.path}
    elif isinstance(request, lwm2m.ReadRequest):
        payload["msgType"] = "read"
        payload["data"] = {"path": request.path}
    elif isinstance(request, lwm2m.WriteRequest):
        payload["msgType"] = "write"
        if len(request) == 1:
            path, value = next(iter(request.items()))
            type_, value = get_emqx_type_name(value)
            data = dict(path=path, type=type_, value=value)
        else:
            data = dict()
            content = list()
            for path, value in request.items():
                oid, iid, rid = path.strip("/").split("/")
                data["basePath"] = f"{oid}/{iid}/"
                type_, value = get_emqx_type_name(value)
                content.append(dict(path=rid, type=type_, value=value))
            data["content"] = content
        payload["data"] = data
    elif isinstance(request, lwm2m.WriteAttrRequest):
        payload["msgType"] = "write-attr"
        payload["data"] = {
            "path": request.path,
            "pmin": none_or_str(request.pmin),
            "pmax": none_or_str(request.pmax),
            "gt": none_or_str(request.gt),
            "lt": none_or_str(request.lt),
            "st": none_or_str(request.st),
        }
    elif isinstance(request, lwm2m.ExecuteRequest):
        payload["msgType"] = "execute"
        payload["data"] = {"path": request.path, "args": request.args or ""}
    elif isinstance(request, lwm2m.CreateRequest):
        payload["msgType"] = "create"
        data = dict()
        content = list()
        for path, value in request.items():
            oid, iid, rid = path.strip("/").split("/")
            data["basePath"] = "/" + oid
            type_, value = get_emqx_type_name(value)
            cont = dict(path=f"/{iid}/{rid}", type=type_, value=value)
            content.append(cont)
        data["content"] = content
        payload["data"] = data
    elif isinstance(request, lwm2m.DeleteRequest):
        payload["msgType"] = "delete"
        payload["data"] = {"path": request.path}
    elif isinstance(request, lwm2m.ObserveRequest):
        payload["msgType"] = "observe"
        payload["data"] = {"path": request.path}
    elif isinstance(request, lwm2m.CancelObserveRequest):
        payload["msgType"] = "cancel-observe"
        payload["data"] = {"path": request.path}
    return json.dumps(payload, default=str)


def str_to_py_value(value: str):
    """Convert string to Python int/float/bool if possible"""
    if not isinstance(value, str):
        return value
    if value.lower() == "true":
        value = True
    elif value.lower() == "false":
        value = False
    try:
        value = float(value)
    except (TypeError, ValueError):
        pass
    else:
        if value.is_integer():
            value = int(value)
    return value


def payload_to_message(
    direction: str, endpoint: str, payload: dict
) -> lwm2m.Message:
    """Convert MQTT payload to lwm2m message"""
    msg_type = payload["msgType"]

    # TODO: handle ack:
    # {'reqID': 123, 'msgType': 'ack', 'data': {'path': '/3/4/0'}})

    if direction == "uplink":
        if msg_type == "register":
            return lwm2m.Registration(
                endpoint,
                payload["data"]["lt"],
                payload["data"].get("sms"),
                payload["data"]["lwm2m"],
                payload["data"].get("b"),
                payload["data"]["alternatePath"],
                payload["data"]["objectList"],
            )
        if msg_type == "update":
            return lwm2m.Update(
                endpoint,
                payload["data"]["lt"],
                payload["data"].get("sms"),
                payload["data"]["lwm2m"],
                payload["data"].get("b"),
                payload["data"]["alternatePath"],
                payload["data"]["objectList"],
            )
        if msg_type == "notify":
            data = dict()
            try:
                data = {
                    d["path"]: d["value"] for d in payload["data"]["content"]
                }
            except KeyError:
                pass
            return lwm2m.Notification(
                endpoint,
                payload["data"]["code"],
                payload["data"]["reqPath"],
                payload["seqNum"],
                data,
            )
        if msg_type == "read":
            data = dict()
            try:
                data = {
                    d["path"]: d["value"] for d in payload["data"]["content"]
                }
            except KeyError:
                pass
            return lwm2m.ReadResponse(
                endpoint,
                payload["data"]["code"],
                payload["data"]["reqPath"],
                data,
            )
        if msg_type == "discover":
            data = dict()
            try:
                for item in payload["data"]["content"]:
                    paths = item.split(",")
                    for path in paths:
                        parts = path.split(";")
                        p = parts[0].strip("<>")
                        attrs = dict()
                        for a in parts[1:]:
                            key = a.split("=")[0]
                            value = str_to_py_value(a.split("=")[1])
                            attrs[key] = value
                        data[p] = attrs
            except KeyError:
                pass
            return lwm2m.DiscoverResponse(
                endpoint,
                payload["data"]["code"],
                payload["data"]["reqPath"],
                data,
            )
        if msg_type == "write":
            return lwm2m.WriteResponse(
                endpoint, payload["data"]["code"], payload["data"]["reqPath"]
            )
        if msg_type == "write-attr":
            return lwm2m.WriteAttrResponse(
                endpoint, payload["data"]["code"], payload["data"]["reqPath"]
            )
        if msg_type == "execute":
            return lwm2m.ExecuteResponse(
                endpoint, payload["data"]["code"], payload["data"]["reqPath"]
            )
        if msg_type == "create":
            return lwm2m.CreateResponse(
                endpoint, payload["data"]["code"], payload["data"]["reqPath"]
            )
        if msg_type == "delete":
            return lwm2m.DeleteResponse(
                endpoint, payload["data"]["code"], payload["data"]["reqPath"]
            )
        if msg_type == "observe":
            data = dict()
            try:
                data = {
                    d["path"]: d["value"] for d in payload["data"]["content"]
                }
            except KeyError:
                pass
            return lwm2m.ObserveResponse(
                endpoint,
                payload["data"]["code"],
                payload["data"]["reqPath"],
                data,
            )
        if msg_type == "cancel-observe":
            data = dict()
            try:
                data = {
                    d["path"]: d["value"] for d in payload["data"]["content"]
                }
            except KeyError:
                pass
            return lwm2m.CancelObserveResponse(
                endpoint,
                payload["data"]["code"],
                payload["data"]["reqPath"],
                data,
            )
    if direction == "downlink":
        if msg_type == "read":
            return lwm2m.ReadRequest(endpoint, payload["data"]["path"])
        if msg_type == "discover":
            return lwm2m.DiscoverRequest(endpoint, payload["data"]["path"])
        if msg_type == "write":
            try:
                data = {payload["data"]["path"]: payload["data"]["value"]}
            except KeyError:
                data = {
                    payload["data"]["basePath"] + c["path"]: c["value"]
                    for c in payload["data"]["content"]
                }
            return lwm2m.WriteRequest(endpoint, data)
        if msg_type == "write-attr":
            return lwm2m.WriteAttrRequest(endpoint, **payload["data"])
        if msg_type == "execute":
            return lwm2m.ExecuteRequest(endpoint, **payload["data"])
        if msg_type == "create":
            data = {
                payload["data"]["basePath"] + c["path"]: c["value"]
                for c in payload["data"]["content"]
            }
            return lwm2m.CreateRequest(endpoint, data)
        if msg_type == "delete":
            return lwm2m.DeleteRequest(endpoint, payload["data"]["path"])
        if msg_type == "observe":
            return lwm2m.ObserveRequest(endpoint, payload["data"]["path"])
        if msg_type == "cancel-observe":
            return lwm2m.CancelObserveRequest(
                endpoint, payload["data"]["path"]
            )
    raise Exception("Failed to convert", endpoint, direction, payload)


def type_topic(cls) -> str:
    if cls is lwm2m.Message:
        return ""
    if issubclass(cls, lwm2m.Uplink):
        direction = "Uplink"
    elif issubclass(cls, lwm2m.Downlink):
        direction = "Downlink"
    else:
        raise TypeError(cls)

    if issubclass(cls, lwm2m.Request):
        type_ = "Request"
    elif issubclass(cls, lwm2m.Response):
        type_ = "Response"
    elif issubclass(cls, lwm2m.Event):
        type_ = "Event"
    else:
        return direction

    if cls is lwm2m.Request or cls is lwm2m.Response or cls is lwm2m.Event:
        return f"{direction}/{type_}"

    return f"{direction}/{type_}/{cls.__name__}"


def publish_topic(msg, req_id=None) -> str:
    topic = f"{msg.ep}/{type_topic(type(msg))}"
    if isinstance(msg, (lwm2m.Registration, lwm2m.Update)):
        return topic
    if req_id is not None:
        topic += f"/{req_id}"
    if isinstance(msg, lwm2m.Notification):
        topic += f"/{msg.seq_num}/{msg.req_path}"
    return topic


class EMQxTopics:
    """Handle EMQx MQTT topics"""

    def __init__(
        self,
        mountpoint="lwm2m",
        command="dn",
        response="up/resp",
        notify="up/notify",
        register="up/resp",
        update="up/resp",
    ):
        """Initialization of EMQxTopics"""
        self.mountpoint = mountpoint
        if command.startswith("up/"):
            raise ValueError("command not allowed to start with 'up'")
        self.command = command
        for part in (response, notify, register, update):
            if not part.startswith("up/"):
                raise ValueError(f"{part!r} does not start with 'up/'")
        self.response = response
        self.notify = notify
        self.register = register
        self.update = update

        self.topic_all = f"{mountpoint}/#"
        self.topic_all_ep = f"{mountpoint}/{{endpoint}}/#"
        self.topic_dn = f"{mountpoint}/{{endpoint}}/{command}"
        self.topic_all_dn = self.topic_dn.format(endpoint="+")
        self.topic_up = f"{mountpoint}/{{endpoint}}/up/#"
        self.topic_all_up = self.topic_up.format(endpoint="+")

        self.topic_command = f"{mountpoint}/{{endpoint}}/{command}"
        # Can't really be trusted since they can equal each other:
        self.topic_response = f"{mountpoint}/{{endpoint}}/{response}"
        self.topic_notify = f"{mountpoint}/{{endpoint}}/{notify}"
        self.topic_register = f"{mountpoint}/{{endpoint}}/{register}"
        self.topic_update = f"{mountpoint}/{{endpoint}}/{update}"

        self.regex_endpoint = re.compile(f"^{mountpoint}/([^/]+)/.*")

    def parse_endpoint(self, topic):
        match = self.regex_endpoint.match(topic)
        if match:
            return match.group(1)
        raise ValueError("Failed to parse endpoint from topic", topic)


class EMQxQueue(queuemod.SimpleQueue):
    def get(self, block=True, timeout=None):
        _, data = super().get(block, timeout)
        return data

    def get_nowait(self):
        return self.get(False)


class EMQxEngine:
    """EMQxEngine handles EMQx MQTT traffic."""

    def __init__(
        self,
        client: Client = None,
        topics: EMQxTopics = None,
        ep_factory=lwm2m.Endpoint,
        timeout=None,
        max_subs=float("inf"),
        qos=0,
    ):
        """Initialization of EMQxEngine"""
        self.log = logging.getLogger(self.__class__.__name__)
        self.req_id = ReqIDSequence()

        self.sp = SubPub()
        if topics is None:
            topics = EMQxTopics()
        self.topics = topics
        self.ep_factory = ep_factory
        self.timeout = timeout
        self.max_subs = max_subs
        self.qos = qos

        # If set, indicates that we have connected at least once to
        # EMQx.
        self.connected_once = threading.Event()
        # If set, indicates that we don't need to unsubscribe because
        # we have already disconnected.
        self.exit_done = threading.Event()

        self._subscriptions_lock = threading.Lock()
        # key = endpoint, value = ref count
        self._subscriptions = collections.Counter()

        # Setup MQTT client last
        if client is None:
            self.client = Client()
        self.client = client
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.enable_logger(logging.getLogger("EMQxMQTT"))
        if client is None:
            self.client.connect("localhost")

    @classmethod
    def via_mqtt(
        cls,
        topics: EMQxTopics = None,
        timeout=None,
        max_subs=float("inf"),
        qos=0,
        **conn_kwargs,
    ):
        c = Client()
        c.connect(**conn_kwargs)
        return cls(c, topics, timeout=timeout, max_subs=max_subs, qos=qos)

    def __enter__(self):
        self.client.loop_start()
        self.connected_once.wait(timeout=10)
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()
        self.client.loop_stop()
        self.client.disconnect()
        self.exit_done.wait()

    def start(self):
        self.log.debug("Command loop starting")
        topic = r"request/(?P<req_id>\d+)"
        self.log.debug("Subscribing to %r", topic)
        self.q = q = self.sp.subscribe(topic)
        t = threading.Thread(
            target=self.commands,
            daemon=True,
            name=self.__class__.__name__,
            args=(q,),
        )
        t.start()
        return t

    def stop(self):
        self.q.put((None, None))

    def commands(self, q):
        """Translate commands between EMQx MQTT and internal subpub"""
        while True:
            try:
                match: re.Match
                match, req = q.get()
            except queuemod.Empty:
                continue
            else:
                if match is None:
                    break
                self.log.debug("Received request: %r", req)
                endpoint = req.ep
                payload = request_to_json(req, match.groups()[0])
                self.log.debug("Publish to %r. Payload: %r", endpoint, payload)
                topic = self.topics.topic_dn.format(endpoint=endpoint)
                self.client.publish(topic, payload.encode(), qos=self.qos)
        self.log.debug("Command loop completed")
        self.exit_done.set()

    def subscribe(self, endpoint) -> int:
        """Subscribe to `endpoint` on EMQx MQTT"""
        with self._subscriptions_lock:
            topic = self.topics.topic_all_ep.format(endpoint=endpoint)
            if topic not in self._subscriptions:
                self.log.debug("Subscribing to %r", topic)
                if len(self._subscriptions) >= self.max_subs:
                    raise Exception("Max number of subscriptions reached!")
                self.client.subscribe(topic, qos=self.qos)
            self._subscriptions[topic] += 1
            return self._subscriptions[topic]

    def subscribe_all(self):
        """Subscribe to all persisted topics on EMQx MQTT (onconnect)"""
        with self._subscriptions_lock:
            for topic in self._subscriptions:
                self.log.debug("Subscribing to %r", topic)
                self.client.subscribe(topic, qos=self.qos)

    def unsubscribe(self, endpoint) -> int:
        """Unsubscribe to `endpoint` on EMQx MQTT"""
        with self._subscriptions_lock:
            topic = self.topics.topic_all_ep.format(endpoint=endpoint)
            if topic in self._subscriptions:
                self._subscriptions[topic] -= 1
                if self._subscriptions[topic] <= 0:
                    del self._subscriptions[topic]
                    if not self.exit_done.is_set():
                        self.log.debug("Unsubscribing to %r", topic)
                        self.client.unsubscribe(topic)
            return self._subscriptions[topic]

    def unsubscribe_all(self):
        """Unsubscribe to all persisted topics on EMQx MQTT"""
        with self._subscriptions_lock:
            for topic in self._subscriptions:
                self.log.debug("Unsubscribing to %r", topic)
                self.client.unsubscribe(topic)
            self._subscriptions = collections.Counter()

    def on_connect(self, client, userdata, flags, rc):
        """Callback when EMQx MQTT connection is established"""
        self.log.debug("OnConnect")
        self.subscribe_all()
        self.connected_once.set()

    def on_message(self, client, userdata, msg: MQTTMessage):
        """Callback when EMQx MQTT message is received"""
        try:
            # This callback must never fail silently. Do the actual
            # work in `_on_message` and log traceback here.
            self._on_message(client, msg)
        except Exception:
            self.log.exception("Error in on_message, %r", msg)

    def _on_message(self, _: Client, msg: MQTTMessage):
        """Route EMQx MQTT payload on internal subpub topic"""
        self.log.debug(
            "Received on %r. Payload: %r", msg.topic, msg.payload.decode()
        )
        direction = "uplink" if "up" in msg.topic else "downlink"
        endpoint = self.topics.parse_endpoint(msg.topic)
        payload = json.loads(msg.payload.decode())
        message = payload_to_message(direction, endpoint, payload)
        topic = publish_topic(message, payload.get("reqID"))
        self.log.debug("Publish to %r. Message: %r", topic, message)
        self.sp.publish(topic, message)

    def send(self, request: lwm2m.Request, timeout=None):
        self.log.debug("Send request %r", request)
        if not isinstance(request, lwm2m.Request):
            raise TypeError(request)
        req_id = next(self.req_id)
        topic_resp = fr"{request.ep}/Uplink/Response/\w+/{req_id}"
        self.log.debug("Subscribe to %r", topic_resp)
        q = self.sp.subscribe(topic_resp)
        if isinstance(request, lwm2m.ObserveRequest):
            # Special case, prepare queue
            t_notify = f"{request.ep}/Uplink/Event/Notification/{req_id}"
            self.log.debug("Subscribe to %r", t_notify)
            try:
                queue = request.queue
            except AttributeError:
                queue = EMQxQueue()
            q_notify = self.sp.subscribe(t_notify, queue=queue)
        topic = f"request/{req_id}"
        self.log.debug("Publish to %r. Message: %r", topic, request)
        self.sp.publish(topic, request)
        try:
            _, resp = q.get(timeout=timeout)
        except queuemod.Empty:
            raise lwm2m.NoResponseError(request) from None
        finally:
            self.log.debug("Unsubscribe to %r", topic_resp)
            self.sp.unsubscribe(topic_resp)
        resp.dt = resp.timestamp - request.timestamp
        if isinstance(request, lwm2m.ObserveRequest):
            # Special case, return queue as well
            resp.notifications = q_notify
        return resp

    def recv(self, endpoint: str, message_types, queue=None):
        self.log.debug("Recv %r: %r", endpoint, message_types)
        if queue is None:
            queue = EMQxQueue()
        if message_types:
            topics = [endpoint + "/" + type_topic(mt) for mt in message_types]
        else:
            topics = [endpoint]
        topics.sort(key=len)
        topic = "|".join(topics)
        self.log.debug("Subscribe to %r", topic)
        return self.sp.subscribe(topic, queue=queue)

    def endpoint(self, endpoint, timeout=None, **kwargs):
        self.log.debug("Endpoint requested: %r", endpoint)
        if timeout is None:
            timeout = self.timeout
        self.subscribe(endpoint)
        ep = self.ep_factory(endpoint, timeout=timeout, **kwargs)
        ep.engine = self
        weakref.finalize(ep, self.unsubscribe, endpoint)
        return ep
