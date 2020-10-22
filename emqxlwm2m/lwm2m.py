
# Built-in
import collections
import dataclasses
import datetime as dt
import enum
import functools
import re
import typing


class ResponseError(Exception):
    pass


class NoResponseError(ResponseError):
    pass


class CoAPResponseCode(enum.Enum):
    Created = '2.01'
    Deleted = '2.02'
    Valid = '2.03'
    Changed = '2.04'
    Content = '2.05'
    BadRequest = '4.00'
    Unauthorized = '4.01'
    BadOption = '4.02'
    Forbidden = '4.03'
    NotFound = '4.04'
    MethodNotAllowed = '4.05'
    NotAcceptable = '4.06'
    PreconditionFailed = '4.12'
    RequestEntityTooLarge = '4.13'
    UnsupportedContentFormat = '4.15'
    InternalServerError = '5.00'
    NotImplemented_ = '5.01'
    BadGateway = '5.02'
    ServiceUnavailable = '5.03'
    GatewayTimeout = '5.04'
    ProxyingNotSupported = '5.05'


class BadPath(Exception):
    pass


class Path(collections.UserString):

    levels = [
        'object',
        'object_instance',
        'resource',
        'resource_instance'
    ]

    def __init__(self, seq):
        """Initialization of Path"""
        seq = re.sub('/+', '/', str(seq))
        super().__init__(seq)

    @classmethod
    def dict(cls, data):
        return {cls(p): v for p, v in data.items()}

    @property
    def parts(self):
        return [p for p in self.data.lstrip('/').split('/') if p]

    @property
    def level(self):
        n = len(self.parts) - 1
        if n < 0:
            return 'root'
        return self.levels[n]

    @property
    def oid(self):
        try:
            return int(self.parts[self.levels.index('object')])
        except IndexError as error:
            raise BadPath('No object id!') from error
        except (ValueError, TypeError) as error:
            raise BadPath('Object id is not an integer') from error

    @property
    def iid(self):
        try:
            return int(self.parts[self.levels.index('object_instance')])
        except IndexError as error:
            raise BadPath('No object instance id!') from error
        except (ValueError, TypeError) as error:
            raise BadPath('Instance id is not an integer') from error

    @property
    def rid(self):
        try:
            return int(self.parts[self.levels.index('resource')])
        except IndexError as error:
            raise BadPath('No resource id!') from error
        except (ValueError, TypeError) as error:
            raise BadPath('Resource id is not an integer') from error

    @property
    def riid(self):
        try:
            return int(self.parts[self.levels.index('resource_instance')])
        except IndexError as error:
            raise BadPath('No resource instance id!') from error
        except (ValueError, TypeError) as error:
            raise BadPath('Resource instance id is not an integer') from error


class NotificationsTracker:
    """Queue used to hold LwM2MPacket instances."""

    def __init__(self, history=10):
        """Initialization of NotificationsTracker"""
        # Keep track of previous notifications
        factory = functools.partial(collections.deque, maxlen=history)
        self._history = collections.defaultdict(factory)

    def add(self, packet):
        self._history[packet.ep, packet.req_path].append(packet)

    def changes(self, packet):
        """Return changes between packet and previous packet"""
        history = list(self._history[packet.ep, packet.req_path])
        changes = dict()
        if not history:
            return changes
        previous_packet = history[-1]
        if packet is previous_packet:
            return changes
        for key, value in packet.items():
            old_value = previous_packet.get(key)
            if old_value != value:
                changes[key] = (old_value, value)
        return changes

    def timedelta(self, packet):
        """Return list of duration between packets"""
        history = list(self._history[packet.ep, packet.req_path])
        if not history:
            return [float('inf')]
        try:
            history.remove(packet)
        except ValueError:
            pass
        history.append(packet)
        output = list()
        for p1, p2 in zip(history, history[1:]):
            output.append((p2.timestamp - p1.timestamp).total_seconds())
        return output

@dataclasses.dataclass
class Attributes:
    """Container for LwM2M attributes"""
    pmin: int = None
    pmax: int = None
    lt: float = None
    st: float = None
    gt: float = None

    regex = re.compile(
        r'(\[(?P<pmin>\d*),\s*(?P<pmax>\d*)\])?'\
        r'(\s*(?P<lt>[^:]*?):(?P<st>[^:]*?):(?P<gt>[^:]*))?')

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
        for attr in ('pmin', 'pmax'):
            if d.get(attr) is not None:
                d[attr] = int(d[attr])
        for attr in ('lt', 'st', 'gt'):
            if d.get(attr) is not None:
                d[attr] = float(d[attr])
        return cls(**d)

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

    def __iter__(self):
        return iter(dataclasses.asdict(self).items())

    def __len__(self):
        """Return number of attributes not None"""
        return len([a for a in dataclasses.asdict(self).values() if a is not None])

# ========
# PAYLOADS
# ========
from dataclasses import dataclass, field


@dataclass
class Message:
    ep: str
    timestamp: dt.datetime = field(
        init=False, repr=False, default_factory=dt.datetime.now, compare=False)


class Downlink(Message):
    pass


class Request(Downlink):

    def __post_init__(self):
        try:
            self.path = Path(self.path)
        except AttributeError:
            pass
        try:
            self.data = Path.dict(self.data)
        except AttributeError:
            pass


@dataclass
class DiscoverRequest(Request):
    ep: str
    path: Path


@dataclass
class ReadRequest(Request):
    ep: str
    path: Path


@dataclass
class WriteRequest(Request, collections.UserDict):
    ep: str
    data: dict


@dataclass
class WriteAttrRequest(Request):
    ep: str
    path: Path
    pmin: int = None
    pmax: int = None
    lt: float = None
    st: float = None
    gt: float = None


@dataclass
class ExecuteRequest(Request):
    ep: str
    path: Path
    args: str = ""


@dataclass
class CreateRequest(Request, collections.UserDict):
    ep: str
    data: dict


@dataclass
class DeleteRequest(Request):
    ep: str
    path: Path


@dataclass
class ObserveRequest(Request):
    ep: str
    path: Path


@dataclass
class CancelObserveRequest(Request):
    ep: str
    path: Path


class Uplink(Message):
    pass


@dataclass
class Response(Uplink):
    ep: str
    code: CoAPResponseCode
    req_path: Path

    def __post_init__(self):
        self.code = CoAPResponseCode(self.code)
        self.req_path = Path(self.req_path)
        try:
            self.data = Path.dict(self.data)
        except AttributeError:
            pass

    def check(self):
        if not self.code.value.startswith('2.'):
            raise ResponseError(self)

    @property
    def value(self):
        try:
            self.check()
            return self.data[self.req_path]
        except AttributeError:
            raise AttributeError(
                f'Responses of type {type(self)} has no value') \
                from None
        except KeyError:
            self.check()
            return self.data


@dataclass
class DiscoverResponse(Response, collections.UserDict):
    ep: str
    code: CoAPResponseCode
    req_path: Path
    data: dict


@dataclass
class ReadResponse(Response, collections.UserDict):
    ep: str
    code: CoAPResponseCode
    req_path: Path
    data: dict


@dataclass
class WriteResponse(Response):
    ep: str
    code: CoAPResponseCode
    req_path: Path


@dataclass
class WriteAttrResponse(Response):
    ep: str
    code: CoAPResponseCode
    req_path: Path


@dataclass
class ExecuteResponse(Response):
    ep: str
    code: CoAPResponseCode
    req_path: Path


@dataclass
class CreateResponse(Response):
    ep: str
    code: CoAPResponseCode
    req_path: Path


@dataclass
class DeleteResponse(Response):
    ep: str
    code: CoAPResponseCode
    req_path: Path


@dataclass
class ObserveResponse(Response, collections.UserDict):
    ep: str
    code: CoAPResponseCode
    req_path: Path
    data: dict


@dataclass
class CancelObserveResponse(Response, collections.UserDict):
    ep: str
    code: CoAPResponseCode
    req_path: Path
    data: dict


class Event(Uplink):
    pass


@dataclass
class Registration(Event, collections.UserList):
    ep: str
    lt: int
    sms: str
    lwm2m: str
    b: str
    alternate_path: str
    data: list

    @property
    def object_list(self):
        return self.data


@dataclass
class Update(Event, collections.UserList):
    ep: str
    lt: int
    sms: str
    lwm2m: str
    b: str
    alternate_path: str
    data: list

    @property
    def object_list(self):
        return self.data


@dataclass
class Notification(Event, collections.UserDict):
    ep: str
    code: CoAPResponseCode
    req_path: Path
    seq_num: int
    data: dict

    def __post_init__(self):
        self.code = CoAPResponseCode(self.code)
        self.req_path = Path(self.req_path)
        self.seq_num = int(self.seq_num)
        self.data = Path.dict(self.data)

    def check(self):
        if not self.code.value.startswith('2.'):
            raise ResponseError(self)

# ==============
# LWM2M ENDPOINT
# ==============

class Endpoint:
    """LwM2M for specific endpoint"""

    def __init__(self, endpoint, timeout=None):
        self.endpoint = endpoint
        self.timeout = timeout
        self.engine = None

    def __repr__(self):
        return f'{self.__class__}({self.endpoint})'

    def __str__(self):
        return self.endpoint

    def wiretap(self, *, queue=None):
        return self.engine.recv(self.endpoint, [Message], queue=queue)

    def uplink(self, *, queue=None):
        return self.engine.recv(self.endpoint, [Uplink], queue=queue)

    def downlink(self, *, queue=None):
        return self.engine.recv(self.endpoint, [Downlink], queue=queue)

    def requests(self, *, queue=None):
        return self.engine.recv(self.endpoint, [Request], queue=queue)

    def response(self, *, queue=None):
        return self.engine.recv(self.endpoint, [Response], queue=queue)

    def events(self, *, queue=None):
        return self.engine.recv(self.endpoint, [Event], queue=queue)

    # LwM2M Client Registration Interface
    # -----------------------------------

    def registrations(self, *, include_updates=False, queue=None):
        msgs = [Registration]
        if include_updates:
            msgs.append(Update)
        return self.engine.recv(self.endpoint, msgs, queue=queue)

    def updates(self, *, queue=None):
        msgs = [Update]
        return self.engine.recv(self.endpoint, msgs, queue=queue)

    # LwM2M Device Management & Service Enablement Interface
    # ------------------------------------------------------

    def commands(self, *, queue=None):
        msgs = [Request, Response]
        return self.engine.recv(self.endpoint, msgs, queue=queue)

    def discover(self, path, timeout=None) -> DiscoverResponse:
        if timeout is None:
            timeout = self.timeout
        msg = DiscoverRequest(self.endpoint, path)
        return self.engine.send(msg, timeout)

    def read(self, path, timeout=None) -> ReadResponse:
        if timeout is None:
            timeout = self.timeout
        msg = ReadRequest(self.endpoint, path)
        return self.engine.send(msg, timeout)

    def write(self, path, value, timeout=None) -> WriteResponse:
        if timeout is None:
            timeout = self.timeout
        msg = WriteRequest(self.endpoint, {path: value})
        return self.engine.send(msg, timeout)

    def write_batch(self, base_path, values, timeout=None) -> WriteResponse:
        if timeout is None:
            timeout = self.timeout
        msg = WriteRequest(self.endpoint, {f'{base_path}/{p}': v
                                           for p, v in values.items()})
        return self.engine.send(msg, timeout)

    def write_attr(self, path, pmin=None, pmax=None,
                   lt=None, st=None, gt=None,
                   timeout=None) -> WriteAttrResponse:
        if timeout is None:
            timeout = self.timeout
        msg = WriteAttrRequest(self.endpoint, path, pmin, pmax, lt, st, gt)
        return self.engine.send(msg, timeout)

    def execute(self, path, args="", timeout=None) -> ExecuteResponse:
        if timeout is None:
            timeout = self.timeout
        msg = ExecuteRequest(self.endpoint, path, args)
        return self.engine.send(msg, timeout)

    def create(self, base_path, values, timeout=None) -> CreateResponse:
        """Create object instance

        Content needed for all mandatory resources. E.g:

        values = [{'/1/0': 'test'}, {'/1/1': 3.1415}]

        Note: The resource paths are relative to `base_path`.
        """
        if timeout is None:
            timeout = self.timeout
        msg = CreateRequest(self.endpoint, {f'/{base_path}/{p}': v
                                            for p, v in values.items()})
        return self.engine.send(msg, timeout)

    def delete(self, path, timeout=None) -> DeleteResponse:
        if timeout is None:
            timeout = self.timeout
        msg = DeleteRequest(self.endpoint, path)
        return self.engine.send(msg, timeout)

    # LwM2M Information Reporting Interface
    # -------------------------------------

    def observe(self, path, timeout=None, *, queue=None) -> ObserveResponse:
        if timeout is None:
            timeout = self.timeout
        msg = ObserveRequest(self.endpoint, path)
        return self.engine.send(msg, timeout)

    def cancel_observe(self, path, timeout=None) -> CancelObserveResponse:
        if timeout is None:
            timeout = self.timeout
        msg = CancelObserveRequest(self.endpoint, path)
        return self.engine.send(msg, timeout)

    def notifications(self, *, queue=None):
        return self.engine.recv(self.endpoint, [Notification], queue=queue)

    # LwM2M Object generated paths
    # ----------------------------

    def __getitem__(self, object_def):
        """
        Examples::

            >>> ep = Endpoint(lwm2m)

            >>> ep[Device][0].reboot.execute()

            >>> res = ep[Server][0].lifetime.read()

            >>> ep.timeout = 32

            >>> dev = ep[Device][0]
            >>> dev.reboot.execute()
        """
        if issubclass(object_def, ObjectDef):
            return object_def(self)
        raise TypeError('Key must be subclass of ObjectDef')


def use_enums(method):
    """Replace values with enums when possible"""
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        resp = method(self, *args, **kwargs)
        for p, v in resp.items():
            try:
                rid = p.rid
            except BadPath:
                continue
            else:
                if isinstance(self, Operation):
                    r = self.resource
                else:
                    r = self.resource_by_id(rid)
                    if r is None:
                        continue
                try:
                    if issubclass(r.type, enum.Enum):
                        resp[p] = r.type(v)
                except TypeError:
                    continue
        return resp
    return wrapper


class LwM2MPath:

    def __init__(self, endpoint: Endpoint):
        self.ep = endpoint

    @property
    def path(self) -> Path:
        raise NotImplementedError

    def discover(self, timeout=None):
        return self.ep.discover(self.path, timeout)

    @use_enums
    def read(self, timeout=None):
        return self.ep.read(self.path, timeout)

    def write(self, value, timeout=None):
        return self.ep.write(self.path, value, timeout)

    def write_batch(self, values, timeout=None):
        base_path = f'/{self.path.oid}/{self.path.iid}'
        return self.ep.write_batch(base_path, values, timeout)

    def write_attr(self, pmin=None, pmax=None,
                   lt=None, st=None, gt=None, timeout=None):
        return self.ep.write_attr(self.path, pmin, pmax,
                                  lt, st, gt, timeout)

    def execute(self, args="", timeout=None):
        return self.ep.execute(self.path, args, timeout)

    def create(self, values, timeout=None):
        vals = {f'/{self.path.iid}/{p}': v for p, v in values.items()}
        return self.ep.create(self.path.oid, vals, timeout)

    def delete(self, timeout=None):
        return self.ep.delete(self.path, timeout)

    # LwM2M Information Reporting Interface
    # -------------------------------------

    @use_enums
    def observe(self, timeout=None, *, queue=None):
        return self.ep.observe(self.path, timeout=timeout, queue=queue)

    @use_enums
    def cancel_observe(self, timeout=None):
        return self.ep.cancel_observe(self.path, timeout)


class Operation:
    """Resource level operation"""

    def __init__(self, resource, obj):
        self.resource = resource
        self.obj = obj
        self.timeout = None

    def __repr__(self):
        r = self.resource
        return f'<{self.__class__.__name__}-Resource {r.name!r} ID={r.rid}, '\
            f'type={r.type}, range={r.range!r}, unit={r.unit!r}, ' \
            f'mandatory={r.mandatory}, multiple={r.multiple}>'

    @property
    def ep(self):
        return self.obj.ep

    @property
    def path(self):
        oid = self.obj.oid
        if oid is None:
            raise BadPath('Missing object ID', self.obj)
        iid = self.obj.iid
        if iid is None:
            iid = 0
        rid = self.resource.rid
        if rid is None:
            raise BadPath('Missing resouce ID', self)
        return Path(f'/{oid}/{iid}/{rid}')


class R(Operation, LwM2MPath):
    pass


class W(Operation, LwM2MPath):
    pass


class RW(R, W):
    pass


class E(Operation, LwM2MPath):
    pass


class BS_RW(Operation, LwM2MPath):
    pass


class Resource:

    rid: int = None
    operations: typing.Union[R, RW, W, E, BS_RW] = None
    type = None
    range = None
    unit = None
    mandatory: bool = None
    multiple: bool = None

    def __init__(self):
        """Initialization of Resource"""
        self.name = ''

    def __set_name__(self, object_def, name):
        self.name = name

    def __repr__(self):
        return f'{self.name}<{self.rid}>'

    def __get__(self, object_instance, object_def=None):
        if object_instance is not None:
            return self.operations(self, object_instance)
        return self

    def __set__(self, object_instance, value):
        raise AttributeError(f'Set attribute {self.name!r} not allowed')


class ObjectDef(LwM2MPath):

    oid = None
    mandatory = True
    multiple = False

    def __init__(self, endpoint: Endpoint, iid=None):
        super().__init__(endpoint)
        self.iid = iid

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._rid = dict()
        for res in vars(cls).values():
            if isinstance(res, Resource):
                cls._rid[res.rid] = res

    def __repr__(self):
        output = f'<{self.__class__.__name__} ID={self.oid}, '\
            f'mandatory={self.mandatory}, multiple={self.multiple}>'
        if self.iid is not None:
            return output + f'[{self.iid}]'
        return output

    @property
    def path(self) -> Path:
        oid = self.oid
        if oid is None:
            raise BadPath('Missing object ID', self)
        iid = self.iid
        if iid is None:
            return Path(f'/{oid}')
        return Path(f'/{oid}/{iid}')

    def __getitem__(self, key) -> 'ObjectDef':
        return self.__class__(self.ep, iid=int(key))

    def resource_by_id(self, rid: int):
        return self._rid.get(rid)
