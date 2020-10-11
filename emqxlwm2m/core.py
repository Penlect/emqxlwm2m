"""Core Python objects"""

# Built-in
import collections
import json
import logging
import queue
import random
import threading
import re
import weakref
import datetime as dt

# PyPI
import paho.mqtt.client as mqtt

DEFAULT_TIMEOUT = 60  # Seconds

class LwM2MErrorResponse(Exception):
    pass

class LwM2MTimeout(Exception):
    pass

class LwM2MParseEndpointError(Exception):
    pass

# Should only exist one instance of this one
class UplinkResponseInbox:

    def __init__(self, req_id_min=0, req_id_max=10000):
        """Initialization of UplinkResponseInbox"""

        self._lock = threading.Lock()
        self._inbox = dict()
        self._req_id = random.randint(req_id_min, req_id_max)
        self.req_id_min = req_id_min
        self.req_id_max = req_id_max

    def make_entry(self) -> (int, queue.SimpleQueue):
        with self._lock:
            self._req_id += 1
            if self._req_id > self.req_id_max:
                self._req_id = self.req_id_min
            q = queue.SimpleQueue()
            self._inbox[self._req_id] = q
            return self._req_id, q

    def put_entry(self, payload: dict) -> bool:
        req_id = int(payload['reqID'])
        with self._lock:
            try:
                q = self._inbox[req_id]
            except KeyError:
                return False
            else:
                q.put(payload)
            finally:
                self._inbox.pop(req_id, None)
        return True


class EndpointInbox:

    def __init__(self):
        """Initialization of UplinkResponseInbox"""

        self._lock = threading.Lock()
        self._inbox = dict()

    def make_entry(self, endpoint):
        with self._lock:
            q = queue.SimpleQueue()
            self._inbox[endpoint] = q
            return q

    def put_entry(self, endpoint: str, payload: dict):
        with self._lock:
            self._inbox[endpoint].put(payload)

    def get_queue(self, endpoint: str) -> queue.SimpleQueue:
        with self._lock:
            return self._inbox[endpoint]


class DownlinkCommand:

    def __init__(
            self, endpoint: str,
            outbox: queue.SimpleQueue,
            inbox: UplinkResponseInbox,
            timeout=DEFAULT_TIMEOUT):
        """Initialization of DownlinkCommand"""
        self.endpoint = endpoint
        self.inbox = inbox
        self.outbox = outbox
        self.timeout = timeout

    def put(self, msgtype, data, timeout=None) -> dict:
        """Put a msg to be sent to broker and wait for response.

        This method is thread-safe since it operates on queues.

        :param msgtype: One of 'read', 'write', etc
        :param data: emqx-lwm2m specific payload.
        :param timeout: Time to wait for response in seconds.
        :return: Response data
        """
        # Prepare entry for response
        req_id, qu = self.inbox.make_entry()

        # Build request and put it in outbox
        payload_req = dict(
            reqID=req_id,
            msgType=msgtype,
            data=data)
        self.outbox.put((self.endpoint, json.dumps(payload_req)))

        # Wait for response
        timeout = timeout or self.timeout
        try:
            return qu.get(timeout=timeout)
        except queue.Empty as empty:
            raise LwM2MTimeout(timeout, self.endpoint, payload_req) from empty


class Path(collections.UserString):

    def __init__(self, *args, **kwargs):
        """Initialization of Path"""
        super().__init__(*args, **kwargs)

    @property
    def object_id(self):
        try:
            return self.data.lstrip('/').split('/')[0]
        except IndexError:
            return ''

    @property
    def object_instance_id(self):
        try:
            return self.data.lstrip('/').split('/')[1]
        except IndexError:
            return ''

    @property
    def resource_id(self):
        try:
            return self.data.lstrip('/').split('/')[2]
        except IndexError:
            return ''

    @property
    def resource_instance_id(self):
        try:
            return self.data.lstrip('/').split('/')[3]
        except IndexError:
            return ''

    @property
    def type(self):
        n = len(self.data.lstrip('/').split('/'))
        if n == 1:
            return 'object'
        if n == 2:
            return 'object_instance'
        if n == 3:
            return 'resource'
        if n == 4:
            return 'resource_instance'
        return 'unknown'


class Attributes:
    """Container for LwM2M attributes"""

    regex = re.compile(
        r'(\[(?P<pmin>\d*),\s*(?P<pmax>\d*)\])?'\
        r'(\s*(?P<lt>[^:]*?):(?P<st>[^:]*?):(?P<gt>[^:]*))?')

    def __init__(self, pmin=None, pmax=None, lt=None, st=None, gt=None):
        """Initialization of Attributes"""
        self.pmin = pmin
        self.pmax = pmax
        self.lt = lt
        self.st = st
        self.gt = gt

    @classmethod
    def from_string(cls, string):
        """Format: [pmin,pmax]lt:st:gt"""
        match = cls.regex.match(string)
        if not match:
            raise ValueError(f'Bad format: {string!r}')
        # Replace empyt string with None
        d = match.groupdict()
        for k, v in d.items():
            if v == '':
                d[k] = None
        return cls(**d)

    def as_dict(self):
        return dict(
            pmin=self.pmin,
            pmax=self.pmax,
            lt=self.lt,
            st=self.st,
            gt=self.gt
        )

    def __repr__(self):
        args = ', '.join(self.as_dict().values)
        return f'{self.__class__.__name__}({args})'


    def __str__(self):
        output = ''
        pmin = self.pmin or ''
        pmax = self.pmax or ''
        lt = self.lt or ''
        st = self.st or ''
        gt = self.gt or ''
        if any((pmin, pmax)):
            output += f'[{pmin},{pmax}]'
        if any((lt, st, gt)):
            output += f'{lt}:{st}:{gt}'
        return output

    def __len__(self):
        """Return number of attributes not None"""
        return len([a for a in self.as_dict().values() if a is not None])


def get_type_name_and_value(value):
    type_ = 'String'
    if isinstance(value, str):
        if value.lower() == 'true':
            value = True
        elif value.lower() == 'false':
            value = False
        elif re.match(r'-?\d+$', value):
            value = int(value)
        else:
            try:
                value = float(value)
            except (TypeError, ValueError):
                pass

    if isinstance(value, bool):
        type_ = 'Boolean'
        value = str(value).lower()  # Must be lower case
    elif isinstance(value, int):
        type_ = 'Integer'
    elif isinstance(value, float):
        type_ = 'Float'
    elif isinstance(value, str):
        type_ = 'String'

    return type_, value


class LwM2M:

    def __init__(self,
                 downlink_command: DownlinkCommand,
                 registrations: queue.SimpleQueue,
                 updates: queue.SimpleQueue,
                 notifications: queue.SimpleQueue):
        """Initialization of LwM2M"""
        self.downlink_command = downlink_command
        self.queue_registraitons = registrations
        self.queue_updates = updates
        self.queue_notifications = notifications

    # LwM2M Device Management & Service Enablement Interface
    # ------------------------------------------------------

    def discover(self, path, timeout=None):
        req_data = dict(path=path)
        resp = self.downlink_command.put('discover', req_data, timeout)
        output = dict()
        try:
            c = resp['data']['content']
        except KeyError as error:
            raise LwM2MErrorResponse(resp) from error
        else:
            for item in c:
                paths = item.split(',')
                for path in paths:
                    parts = path.split(';')
                    p = parts[0].strip('<>')
                    attrs = {p.split('=')[0]: p.split('=')[1] for p in parts[1:]}
                    output[p] = attrs
        return output

    def read(self, path, timeout=None):
        req_data = dict(path=path)
        resp = self.downlink_command.put('read', req_data, timeout)
        try:
            c = resp['data']['content']
        except KeyError as error:
            raise LwM2MErrorResponse(resp) from error
        else:
            return {Path(d['path']):d['value'] for d in c}

    def write(self, path, value, timeout=None):
        type_, value = get_type_name_and_value(value)
        req_data = dict(path=path, type=type_, value=value)
        resp = self.downlink_command.put('write', req_data, timeout)
        if resp['data'].get('codeMsg') != 'changed':
            raise LwM2MErrorResponse(resp)

    def write_batch(self, path_values: dict, timeout=None):
        raise NotImplementedError()

    def write_attr(self, path, pmin=None, pmax=None,
                   lt=None, st=None, gt=None, timeout=None):
        req_data = dict(path=path, pmin=pmin, pmax=pmax, lt=lt, st=st, gt=gt)
        resp = self.downlink_command.put('write-attr', req_data, timeout)
        if resp['data'].get('codeMsg') != 'changed':
            raise LwM2MErrorResponse(resp)

    def execute(self, path, args='', timeout=None):
        req_data = dict(path=path, args=args)
        resp = self.downlink_command.put('execute', req_data, timeout)
        if resp['data'].get('codeMsg') != 'changed':
            raise LwM2MErrorResponse(resp)

    def create(self, basePath, values, timeout=None):
        """Create object instance

        Content needed for all mandatory resources. E.g:

        values = [{'/1/0': 'test'}, {'/1/1': 3.1415}]

        Note: The resource paths are relative to `basePath`.
        """
        content = list()
        for path, value in values.items():
            type_, value = get_type_name_and_value(value)
            content.append(dict(path=path, type=type_, value=value))
        req_data = dict(basePath=basePath, content=content)
        resp = self.downlink_command.put('create', req_data, timeout)
        if resp['data'].get('codeMsg') != 'created':
            raise LwM2MErrorResponse(resp)

    def delete(self, path, timeout=None):
        req_data = dict(path=path)
        resp = self.downlink_command.put('delete', req_data, timeout)
        if resp['data'].get('codeMsg') != 'deleted':
            raise LwM2MErrorResponse(resp)

    # LwM2M Information Reporting Interface
    # -------------------------------------

    def observe(self, path, timeout=None):
        req_data = dict(path=path)
        resp = self.downlink_command.put('observe', req_data, timeout)
        try:
            c = resp['data']['content']
        except KeyError as error:
            raise LwM2MErrorResponse(resp) from error
        else:
            return resp['reqID'], {Path(d['path']):d['value'] for d in c}

    def cancel_observe(self, path, timeout=None):
        req_data = dict(path=path)
        resp = self.downlink_command.put(
            'cancel-observe', req_data, timeout)
        if resp['data'].get('codeMsg') != 'content':
            raise LwM2MErrorResponse(resp)

    def registrations(self, timeout=None):
        stop = False
        while not stop:
            try:
                resp = self.queue_registraitons.get(timeout=timeout)
                stop = yield resp['timestamp'], resp['data']
            except queue.Empty:
                return

    def updates(self, timeout=None):
        stop = False
        while not stop:
            try:
                resp = self.queue_updates.get(timeout=timeout)
                stop = yield resp['timestamp'], resp['data']
            except queue.Empty:
                return

    def notifications(self, timeout=None):
        stop = False
        while not stop:
            try:
                resp = self.queue_notifications.get(timeout=timeout)
            except queue.Empty:
                return
            try:
                c = resp['data']['content']
            except KeyError as error:
                raise LwM2MErrorResponse(resp) from error
            else:
                stop = yield resp['timestamp'], resp['reqID'], resp['seqNum'],\
                    {Path(d['path']):d['value'] for d in c}


class EMQxTopics:
    """Handle MQTT topics"""

    def __init__(self, mountpoint='lwm2m', command='dn', response='up/resp',
                 notify='up/notify', register='up/resp', update='up/resp'):
        """Initialization of EMQxTopics"""
        self.mountpoint = mountpoint
        self.command = command
        self.response = response
        self.notify = notify
        self.register = register
        self.update = update

        for part in (response, notify, register, update):
            if not part.startswith('up/'):
                raise ValueError(f'{part!r} does not start with \'up/\'')

        self.topic_dn = f'{mountpoint}/{{endpoint}}/{command}'
        self.topic_up = f'{mountpoint}/{{endpoint}}/up/#'

        self.topic_command = f'{mountpoint}/{{endpoint}}/{command}'
        self.topic_response = f'{mountpoint}/{{endpoint}}/{response}'
        self.topic_notify = f'{mountpoint}/{{endpoint}}/{notify}'
        self.topic_register = f'{mountpoint}/{{endpoint}}/{register}'
        self.topic_update = f'{mountpoint}/{{endpoint}}/{update}'

        self.regex_endpoint = re.compile(f'^{mountpoint}/([^/]+)/.*')

    def parse_endpoint(self, topic):
        match = self.regex_endpoint.match(topic)
        if match:
            return match.group(1)
        raise LwM2MParseEndpointError(topic)


class LwM2MGateway:

    def __init__(self, client: mqtt.Client, topics: EMQxTopics = None,
                 **kwargs):
        """Initialization of MQTTDriver"""
        self.log = logging.getLogger(self.__class__.__name__)
        client.enable_logger(logging.getLogger('MQTT'))
        self.client = client
        # self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        if topics is None:
            topics = EMQxTopics()
        self.topics = topics
        self.outbox_commands = queue.SimpleQueue()
        self.inbox_commands = UplinkResponseInbox()
        self.inbox_registrations = EndpointInbox()
        self.inbox_updates = EndpointInbox()
        self.inbox_notifications = EndpointInbox()
        self._stop = threading.Event()

    @classmethod
    def via_mqtt(cls, *args, **kwargs):
        c = mqtt.Client()
        conn_kw = kwargs.copy()
        conn_kw.pop('topics', None)
        c.connect(*args, **conn_kw)
        return cls(c, **kwargs)

    def run(self):
        while not self._stop.is_set():
            try:
                endpoint, payload = self.outbox_commands.get(timeout=0.1)
            except queue.Empty:
                continue
            else:
                self.log.debug('Publish to %r. Payload: %r', endpoint, payload)
                topic = self.topics.topic_dn.format(endpoint=endpoint)
                self.client.publish(topic, payload.encode(), qos=0)

    def start(self):
        t = threading.Thread(target=self.run, daemon=True, name='CmdOutbox')
        t.start()
        return t

    def stop(self):
        self._stop.set()

    def on_message(self, client, userdata, msg: mqtt.MQTTMessage):
        payload = msg.payload.decode()
        self.log.debug('Received on %r. Payload: %r', msg.topic, payload)
        try:
            self._on_message(msg.topic, payload)
        except Exception:
            self.log.exception('Error in on_message')

    def _on_message(self, topic: str, payload: str):
        try:
            endpoint = self.topics.parse_endpoint(topic)
        except LwM2MParseEndpointError:
            self.log.error('Failed to parse endpoint from %r', topic)
            return
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            self.log.exception('Failed to decode payload from %r', topic)
            return
        data['timestamp'] = dt.datetime.now()

        if 'reqID' not in data:
            if data['msgType'] == 'register':
                self.inbox_registrations.put_entry(endpoint, data)
            elif data['msgType'] == 'update':
                self.inbox_updates.put_entry(endpoint, data)
            return
        if 'seqNum' in data:
            self.inbox_notifications.put_entry(endpoint, data)
            if data['seqNum'] != 1:
                return
        self.inbox_commands.put_entry(data)

    def new_lwm2m(self, endpoint):
        topic_up = self.topics.topic_up.format(endpoint=endpoint)
        self.client.subscribe(topic_up, qos=2)
        dc = DownlinkCommand(
            endpoint, self.outbox_commands, self.inbox_commands)
        reg_q = self.inbox_registrations.make_entry(endpoint)
        upd_q = self.inbox_updates.make_entry(endpoint)
        not_q = self.inbox_notifications.make_entry(endpoint)
        lwm2m = LwM2M(dc, reg_q, upd_q, not_q)
        weakref.finalize(lwm2m, self.client.unsubscribe, topic_up)
        return lwm2m

    def __enter__(self):
        self.client.loop_start()
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()
        self.client.loop_stop()
        self.client.disconnect()
