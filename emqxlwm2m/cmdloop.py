"""Cmd loop"""

# Built-in
import argparse
import cmd
import contextlib
import datetime as dt
import functools
import itertools
import logging
import os
import re
import shlex
import textwrap
import time
from pprint import pprint

# PyPI
import rich
import rich.console
import rich.table
import rich.box

# Package
import emqxlwm2m.engines.emqx
import emqxlwm2m.utils
from emqxlwm2m.lwm2m import (Path, BadPath, Attributes)
from emqxlwm2m.history import *

LOG = logging.getLogger('emqxlwm2m')
CONSOLE = rich.console.Console()

# Todo
select_path = functools.partial(select_path, CONSOLE)

def create_args(text):
    output = dict()
    args = list()
    pattern = re.compile(r'(?P<path>/?(?:\d/?)+/?)=(.*)')
    for part in text.split():
        m = pattern.match(part)
        if m:
            path, arg = m.groups()
            output[path] = [arg]
            args = output[path]
        else:
            args.append(part)
    return {p: ' '.join(args) for p, args in output.items()}

# HELPER OBJECTS FOR THE INTERPRETER
# ==================================

def get_and_pprint_packet(queue):
    color = 'red'
    try:
        packet = queue.get()
    except Exception as error:
        CONSOLE.print(type(error), style='bold red', highlight=False)
        CONSOLE.print(error, style='bold red')
    else:
        color = 'black'
        msg = dict(packet)
        if packet.direction == 'downlink':
            color = 'blue'
        elif packet.msg_type in {'register', 'update'}:
            color = 'magenta'
        elif packet.msg_type != 'notify' and packet.direction == 'uplink':
            color = 'green'
        title = f'{packet.endpoint} {packet.msg_type} '\
            f'[{color}]{packet.direction}[/{color}]'
        CONSOLE.print(title, style='bold', highlight=False)
        CONSOLE.print(msg, style=color)

def valsplit(p):
    parts = p.split('=', maxsplit=1)
    if len(parts) == 1:
        return parts[0], ''
    return parts[0], '=' + parts[1]


class Epath(Path):
    """Behaves as a path with endpoint"""

    levels = ['endpoint'] + Path.levels

    def __init__(self, seq):
        """Initialization of Epath"""
        seq = str(seq)
        seq, val = valsplit(seq)
        if not seq.startswith('/'):
            raise BadPath(f'Only absolue cwd allowed: {seq!r}')
        seq = seq.strip('/')
        parts = seq.split('/')
        parts = [p for p in parts if p not in {'', '.'}]
        parts = self.__class__.resolve_dotdot(parts)
        super().__init__('/' + '/'.join(parts) + val)

    def resolve(self, path):
        if path.startswith('/'):
            raise BadPath(f'Can\'t resolve absolute path {path!r}')
        return self.__class__(self.data + '/' + path)

    @staticmethod
    def resolve_dotdot(parts):
        resolved_parts = list()
        for p in parts:
            if p == '..':
                try:
                    resolved_parts.pop()
                except IndexError:
                    pass
            else:
                resolved_parts.append(p)
        return resolved_parts

    def with_endpoint(self, ep):
        return self.__class__(f'/{ep}/' + self.path)

    @property
    def path(self):
        return '/'.join(self.parts[1:])

    @property
    def endpoint(self):
        try:
            return self.parts[self.levels.index('endpoint')]
        except IndexError as error:
            raise BadPath('No endpoint!') from error


def for_all_do_methods(decorator):
    """Apply `decorator` on all 'do_'-methods of class"""
    def decorate(cls):
        for attr in cls.__dict__:
            if attr.startswith('do_') and callable(getattr(cls, attr)):
                setattr(cls, attr, decorator(getattr(cls, attr)))
        return cls
    return decorate


def print_errors(do_method):
    """Print uncaught exceptions"""
    @functools.wraps(do_method)
    def wrapper(*args, **kwargs):
        try:
            return do_method(*args, **kwargs)
        except (emqxlwm2m.NoResponseError, BadPath) as error:
            print(f'{type(error).__name__}: {error}')
        except emqxlwm2m.ResponseError as error:
            print(f'{type(error).__name__}: {error}')
        except Exception as error:
            logging.exception(f'{type(error).__name__}: {error}')
    return wrapper


def arg_parse(do_method):
    @functools.wraps(do_method)
    def wrapper(self, line):

        # Print name of method and arguments if echo is True
        if self.echo:
            print('$', do_method.__name__, line)

        # Parse line string with argparse parser
        if isinstance(line, str):
            subparser = globals()[do_method.__name__.replace('do_', 'parser_')]
            try:
                args = subparser.parse_args(shlex.split(line))
            except SystemExit:
                # Prevent '--help' from exit process
                return
        elif isinstance(line, argparse.Namespace):
            # Already parsed, nothing to be done.
            args = line
        else:
            raise ValueError(f'Bad input: {line}')

        # Use default timeout set in interpreter if not provided
        args.timeout = getattr(args, 'timeout', self.timeout)

        # Resolve endpoints the corresponds to files. Also, ensure endpoint
        # if required (i.e. when epath does not exist).
        if isinstance(getattr(args, 'endpoints', None), list):
            args.endpoints = endpoints_from_file(args.endpoints)
            if not (args.endpoints or hasattr(args, 'epath')):
                if self.cwd != '/':
                    args.endpoints = [self.cwd.endpoint]
                else:
                    args.endpoints = self.select_ep()

        # Resolve epaths to full path (= Epath).
        if isinstance(getattr(args, 'epath', None), list):
            op = do_method.__name__.replace('do_', '')
            args.epath = self.resolve_epath(args.epath, args.endpoints, op=op)
            self.log.debug('Resolved epaths: %r', args.epath)
            # Add endpoint & path to history
            for epath in args.epath:
                add_endpoint_to_history(epath.endpoint)
                add_path_to_history(epath.path.split('=')[0])

        # Used for debugging
        if self.breakpoint:
            breakpoint()

        # Run the do-method.
        try:
            if getattr(args, 'output', None):
                # Note: Does not work with threads/subprocesses
                with open(args.output, 'w') as out:
                    print(f'Redirecting stdout to {args.output} ...')
                    with contextlib.redirect_stdout(out):
                        do_method(self, args)
            else:
                return do_method(self, args)
        except KeyboardInterrupt:
            pass
    return wrapper


@for_all_do_methods(print_errors)
class CommandInterpreter(cmd.Cmd):
    """Interpreter for interactive commands"""

    def __init__(self, engine, cwd='/', data_model=None, known_endpoints=None,
                 timeout=None, ep_prefix='', **kwargs):
        """Initialization of LwM2M CommandInterpreter"""
        super().__init__(**kwargs)
        self.log = logging.getLogger('Intrpr')
        self.engine = engine
        self.data_model = data_model
        self.known_endpoints = known_endpoints
        self.timeout = timeout  # Seconds
        self.breakpoint = False
        self.cmd_history_file = os.path.expanduser('~/.emqxlwm2m_history')
        if not cwd:
            cwd = '/'
        self.cwd = Epath(cwd)
        self.ep_prefix = ep_prefix
        self.echo = False

    def preloop(self):
        self.gw = self.engine.__enter__()

    def postloop(self):
        self.gw.__exit__(None, None, None)

    def do_echo(self, line):
        if line.lower() in {'yes', 'on', '1'}:
            self.echo = True
        else:
            self.echo = False

    def do_EOF(self, line):
        return True

    def do_q(self, line):
        return True

    def do_quit(self, line):
        return True

    def do_exit(self, line):
        return True

    def do_breakpoint(self, line):
        self.breakpoint = not self.breakpoint
        return False

    def do_sleep(self, line):
        """Sleep seconds"""
        duration = int(line)
        if duration > 10:
            print(f'Sleeping for {duration} seconds ...')
        time.sleep(duration)

    def do_x(self, line):
        """Repeat command multiple times"""
        n, line = line.split(maxsplit=1)
        self.cmdqueue.append('echo on')
        self.cmdqueue.extend([line]*int(n))
        self.cmdqueue.append('echo off')

    def do_script(self, line):
        """Run commands from file"""
        if not line:
            return
        try:
            with open(line) as f:
                self.cmdqueue.append('echo on')
                for c in f:
                    c = c.strip()
                    if c and not c.startswith('#'):
                        self.cmdqueue.append(c)
                self.cmdqueue.append('echo off')
        except FileNotFoundError as error:
            print(error)

    def do_history(self, line):
        """Fzf select and run command from command line history"""
        command = select_cmd_from_history()
        if command:
            self.cmdqueue.append('echo on')
            self.cmdqueue.append(command)
            self.cmdqueue.append('echo off')

    def do_loglevel(self, line):
        """Change loglevel: DEBUG, INFO, WARNING, ERROR"""
        log = logging.getLogger()
        if not line:
            print(logging.getLevelName(log.level))
        else:
            log.setLevel(getattr(logging, line.upper()))
        return False

    def default(self, line):
        print('*** Unknown syntax:', line)

    @functools.lru_cache(maxsize=20)
    def lwm2m(self, endpoint, timeout=None):
        """Cached Endpoint instances.

        Used to prevent unnecessary subscribe/unsubscribe calls.
        """
        return self.gw.endpoint(endpoint, timeout)

    # =========================================================================
    # Endpoint and Path operations
    # =========================================================================

    @property
    def prompt(self):
        timestamp = format(dt.datetime.now(), '%H:%M:%S')
        with CONSOLE.capture() as capture:
            CONSOLE.print(self.engine.host, style='blue', end=':')
            CONSOLE.print(self.engine.port, end=':')
            try:
                CONSOLE.print(f'/{self.cwd.endpoint}',
                              style='bold', end='', highlight=False)
                CONSOLE.print(f'/{self.cwd.oid}', end='')
                CONSOLE.print(f'/{self.cwd.iid}', end='')
                CONSOLE.print(f'/{self.cwd.rid}', end='')
            except BadPath:
                pass
            finally:
                CONSOLE.print(f'\n({timestamp})$', style='black', end=' ')
        return capture.get()

    def do_cd(self, line):
        self.cwd = self.cwd.resolve(line)

    def do_ls(self, line):
        target = self.cwd.resolve(line)
        if target.level == 'root':
            for ep in get_endpoints(self.known_endpoints):
                print(ep)
            return
        ep = self.lwm2m(target.endpoint)
        if target.level == 'endpoint':
            q = ep.updates()
            ep.execute("/1/0/8", timeout=self.timeout)
            packet = q.get(timeout=self.timeout)
            paths = packet['objectList']
            oid_iid = dict()
            for p in paths:
                parts = p.strip('/').split('/')
                if len(parts) == 1:
                    oid_iid.setdefault(int(parts[0]), list())
                else:
                    oid_iid.setdefault(int(parts[0]), list()).append(int(parts[1]))
            for oid, iid in sorted(oid_iid.items()):
                if iid:
                    ins = ', '.join(str(i) for i in iid)
                    print(f'/{oid} ({ins})')
                else:
                    print(f'/{oid}')
            return
        pathattrs = ep.discover(target.path, self.timeout)
        i = len(target.parts) - 1
        seen = dict()
        for p, attrs in pathattrs.items():
            p = p.strip('/').split('/')
            try:
                n = p[i]
            except IndexError:
                pass
            else:
                seen[int(n)] = attrs
        for p, attrs in sorted(seen.items()):
            print(p, attrs)

    def do_ep(self, line):
        """Change current endpoint client name"""
        line = line.strip()
        if line:
            if self.ep_prefix and not line.startswith(self.ep_prefix):
                line = self.ep_prefix + line
            ep = [line]
        else:
            ep = self.select_ep()
        if ep is not None:
            self.cwd = Epath('/' + ep[-1] + '/' + self.cwd.path)

    def complete_ep(self, text, line, begidx, endidx):
        if self.known_endpoints:
            ep = self.select_ep()
            if ep is not None:
                return ep
        return list()

    def select_ep(self):
        if self.known_endpoints:
            return select_endpoint(CONSOLE, self.known_endpoints)
        return input_endpoint()

    def is_absolue(self, epath):
        epath = epath.strip('/')
        if epath.startswith('.'):
            return False
        try:
            int(epath.split('/')[0])
        except (TypeError, ValueError):
            return True
        else:
            return False

    def resolve_epath(self, epaths, endpoints, op=None):
        output_epaths = list()
        epaths = frozenset(epaths)
        if endpoints is None:
            endpoints = list()
        endpoints = endpoints.copy()
        paths = list()
        for p in epaths:
            p, val = valsplit(p)
            if self.is_absolue(p):
                epath = Epath('/' + p + val)
                if epath.level == 'endpoint':
                    endpoints.append(epath)
                else:
                    output_epaths.append(epath)
            elif p == '.':
                if not self.cwd.path:
                    raise BadPath(
                        f'Path "." can\'t be used at {self.cwd.level} level')
                paths.append(p + val)
            else:
                parts = p.strip('/').split('/')
                parts = [p for p in parts if p not in {'', '.'}]
                p = '/'.join(parts)
                paths.append(p + val)
        endpoints = frozenset(endpoints)

        if not paths and not endpoints and self.cwd == '/':  # 000
            if not output_epaths:
                eps = self.select_ep()
                paths = select_path(self.data_model, operations=op)
                for ep in eps:
                    for p in paths:
                        output_epaths.append(Epath(f'/{ep}/{p}'))

        elif not paths and not endpoints and self.cwd != '/':  # 001
            if not output_epaths:
                paths = select_path(self.data_model, operations=op)
                for p in paths:
                    output_epaths.append(self.cwd.resolve(p))

        elif not paths and endpoints and self.cwd == '/':  # 010
            paths = select_path(self.data_model, operations=op)
            for ep in endpoints:
                for p in paths:
                    output_epaths.append(Epath(f'/{ep}/{p}'))

        elif not paths and endpoints and self.cwd != '/':  # 011
            # todo: If cwd is only endpoint, then select path
            # if self.cwd.path:
            #     paths = [self.cwd.path]
            # else:
            #     paths = select_path(self.data_model, operations=op)
            output_epaths.append(self.cwd)
            for ep in endpoints:
                # for p in paths:
                output_epaths.append(self.cwd.with_endpoint(ep))

        elif paths and not endpoints and self.cwd == '/':  # 100
            eps = self.select_ep()
            for ep in eps:
                for p in paths:
                    output_epaths.append(Epath(f'/{ep}/{p}'))

        elif paths and not endpoints and self.cwd != '/':  # 101
            for p in paths:
                output_epaths.append(self.cwd.resolve(p))

        elif paths and endpoints and self.cwd == '/':  # 110
            for ep in endpoints:
                for p in paths:
                    output_epaths.append(Epath(f'/{ep}/{p}'))

        elif paths and endpoints and self.cwd != '/':  # 111
            for p in paths:
                x = self.cwd.resolve(p)
                output_epaths.append(x)
                for ep in endpoints:
                    output_epaths.append(x.with_endpoint(ep))

        output_epaths.sort()
        return [Epath(p) for p in output_epaths]

    # =========================================================================
    # LWM2M - Perform basic LwM2M operation
    # =========================================================================

    @arg_parse
    def do_discover(self, args):
        """LwM2M Discover"""
        for epath in args.epath:
            ep = self.lwm2m(epath.endpoint)
            value = ep.discover(epath.path, self.timeout)
            pprint(value)
            print()

    def help_discover(self):
        parser_discover.print_help()

    def complete_discover(self, text, line, begidx, endidx):
        if not self.data_model:
            return list()
        def filter_(cand):
            return cand.lstrip('/').startswith(text.lstrip('/'))
        s = select_path(self.data_model, operations='', filter_=filter_)
        return [' '.join(s)]

    @arg_parse
    def do_read(self, args):
        """LwM2M Read"""
        while True:
            for epath in args.epath:
                ep = self.lwm2m(epath.endpoint)
                try:
                    value = ep.read(epath.path, args.timeout)
                except emqxlwm2m.ResponseError as error:
                    print(epath.endpoint, error)
                else:
                    print(epath.endpoint)
                    CONSOLE.print(dict(value))
                if len(args.epath) > 1:
                    print()
            if args.repeat:
                time.sleep(args.repeat)
            else:
                break

    def help_read(self):
        parser_read.print_help()

    def complete_read(self, text, line, begidx, endidx):
        if not self.data_model:
            return list()
        def filter_(cand):
            return cand.lstrip('/').startswith(text.lstrip('/'))
        s = select_path(self.data_model, operations='R', filter_=filter_)
        return [' '.join(s)]

    @arg_parse
    def do_write(self, args):
        """LwM2M Write"""
        epaths_values = list()
        for epath in args.epath:
            p, value = valsplit(epath)
            if not value:
                value = input(f'Write value to {epath!r}: ')
            if not value:
                print('No value provided! Aborting.')
                return
            if value.startswith('='):
                value = value[1:]
            value = emqxlwm2m.engines.emqx.str_to_py_value(value)
            epaths_values.append((Epath(p), value))
        epaths_values.sort()
        if args.batch:
            def group(epathvalue):
                epath = epathvalue[0]
                ep = epath.endpoint
                base_path = f'{epath.oid}/{epath.iid}'
                return (ep, base_path)
            groups = itertools.groupby(epaths_values, key=group)
            for (ep, base_path), chunk in groups:
                values = dict()
                for p, value in chunk:
                    values[str(p.rid)] = value
                ep = self.lwm2m(ep)
                ep.write_batch(base_path, values, args.timeout)
        else:
            for p, value in epaths_values:
                ep = self.lwm2m(p.endpoint)
                ep.write(p.path, value, args.timeout)

    def help_write(self):
        parser_write.print_help()

    def complete_write(self, text, line, begidx, endidx):
        if not self.data_model:
            return list()
        def filter_(cand):
            return cand.lstrip('/').startswith(text.lstrip('/'))
        s = select_path(self.data_model, operations='W', filter_=filter_)
        return [' '.join(s)]

    @arg_parse
    def do_write_attr(self, args):
        """LwM2M Write Attributes

        Set some or all attributes {pmin, pmax, lt, st, gt} to
        objects, instances or resources.

        A special syntax is used to specify the attributes::

            PATH=[pmin,pmax]lt:st:gt

        Attributes can be omitted.

        Example::

            3/0/9=[10,30]10:5:90 3/0/19=[10,30] 1/0/1=[,60]

        If flags are used, e.g. --pmax 123, then those will take
        higher precedence.

        **pmin**: The Minimum Period Attribute indicates the minimum
        time in seconds the LwM2M Client MUST wait between two
        notifications.  If a Resource value has to be notified during
        the specified quiet period, the notification MUST be sent as
        soon as this period expires.

        **pmax**: The Maximum Period Attribute indicates the maximum
        time in seconds the LwM2M Client MAY wait between two
        notifications.  When this “Maximum Period” expires after the
        last notification, a new notification MUST be sent.  The
        maximum period parameter MUST be not smaller than the minimum
        period parameter.

        **lt**: This “lt” Attribute defines a threshold low value.
        When this Attributes is present, the LwM2M Client MUST notify
        the Server each time the Observed Resource value crosses this
        threshold.

        **step**: This “Step” Attribute defines a minimum change value
        between two notifications.  When this Attribute is present,
        the Change Value Condition will occur when the value variation
        since the last notification of the Observed Resource, is
        greater or equal to the “Step” Attribute value.

        **gt**: This “gt” Attribute defines a threshold high value.
        When this Attributes is present, the LwM2M Client MUST notify
        the Server each time the Observed Resource value crosses this
        threshold.
        """
        flags = dict(pmin=args.pmin, pmax=args.pmax,
                     lt=args.lt, st=args.st, gt=args.gt)
        flags = {k: v for k, v in flags.items() if v is not None}
        epaths_values = list()
        for epath in args.epath:
            p, value = valsplit(epath)
            if not value and not flags:
                print('Attributes syntax: [pmin,pmax]lt:st:gt')
                value = input(f'Write attributes to {epath!r}: ')
                if not value:
                    print('No attributes provided! Aborting.')
                    return
            epaths_values.append((Epath(p), value.strip('=')))

        for p, attr in epaths_values:
            attr = Attributes.from_string(attr)
            attr = attr.as_dict()
            attr.update(**flags)
            ep = self.lwm2m(p.endpoint)
            ep.write_attr(p.path, **attr, timeout=args.timeout)

    def help_write_attr(self):
        parser_write_attr.print_help()

    def complete_write_attr(self, text, line, begidx, endidx):
        if not self.data_model:
            return list()
        def filter_(cand):
            return cand.lstrip('/').startswith(text.lstrip('/'))
        s = select_path(self.data_model, operations='R', filter_=filter_)
        return [' '.join(s)]

    @arg_parse
    def do_execute(self, args):
        """LwM2M Execute

        Example (Device reboot)::

            execute 3/0/4
        """
        for epath in args.epath:
            p, value = valsplit(epath)
            p = Epath(p)
            if args.args:
                value = args.args
            if value.startswith('='):
                value = value[1:]
            ep = self.lwm2m(p.endpoint)
            ep.execute(p.path, value, args.timeout)

    def help_execute(self):
        parser_execute.print_help()

    def complete_execute(self, text, line, begidx, endidx):
        if not self.data_model:
            return list()
        def filter_(cand):
            return cand.lstrip('/').startswith(text.lstrip('/'))
        s = select_path(self.data_model, operations='E', filter_=filter_)
        return [' '.join(s)]

    @arg_parse
    def do_create(self, args):
        """LwM2M Create"""
        epaths_values = list()
        for epath in args.epath:
            p, value = valsplit(epath)
            if not value:
                value = input(f'Write value to {epath!r}: ')
            if not value:
                print('No value provided! Aborting.')
                return
            if value.startswith('='):
                value = value[1:]
            value = emqxlwm2m.engines.emqx.str_to_py_value(value)
            epaths_values.append((Epath(p), value))
        epaths_values.sort()
        def group(epathvalue):
            epath = epathvalue[0]
            ep = epath.endpoint
            oid = str(epath.oid)
            iid = str(epath.iid)
            return (ep, oid, iid)
        groups = itertools.groupby(epaths_values, key=group)
        for (ep, oid, iid), chunk in groups:
            values = dict()
            for p, value in chunk:
                values[f'/{iid}/{p.rid}'] = value
            ep = self.lwm2m(p.endpoint)
            ep.create(oid, values, args.timeout)

    def help_create(self):
        parser_create.print_help()

    def complete_create(self, text, line, begidx, endidx):
        if not self.data_model:
            return list()
        def filter_(cand):
            return cand.lstrip('/').startswith(text.lstrip('/'))
        s = select_path(self.data_model, operations='W', filter_=filter_)
        return [' '.join(s)]

    @arg_parse
    def do_delete(self, args):
        """LwM2M Delete"""
        for epath in args.epath:
            ep = self.lwm2m(epath.endpoint)
            ep.delete(epath.path, args.timeout)

    def help_delete(self):
        parser_delete.print_help()

    def complete_delete(self, text, line, begidx, endidx):
        if not self.data_model:
            return list()
        def filter_(cand):
            return cand.lstrip('/').startswith(text.lstrip('/'))
        s = select_path(self.data_model, operations='', filter_=filter_)
        return [' '.join(s)]

    @arg_parse
    def do_observe(self, args):
        """LwM2M Observe"""
        q = None
        for epath in args.epath:
            ep = self.lwm2m(epath.endpoint)
            resp, q = ep.observe(epath.path, queue=q, timeout=self.timeout)
            print(resp)
        if args.track:
            while True:
                packet = q.get()
                pprint(packet)
                print()

    def help_observe(self):
        parser_observe.print_help()

    def complete_observe(self, text, line, begidx, endidx):
        if not self.data_model:
            return list()
        def filter_(cand):
            return cand.lstrip('/').startswith(text.lstrip('/'))
        s = select_path(self.data_model, operations='R', filter_=filter_)
        return [' '.join(s)]

    @arg_parse
    def do_cancel_observe(self, args):
        """LwM2M Cancel Observe"""
        for epath in args.epath:
            ep = self.lwm2m(epath.endpoint)
            ep.cancel_observe(epath.path, args.timeout)

    def help_cancel_observe(self):
        parser_cancel_observe.print_help()

    def complete_cancel_observe(self, text, line, begidx, endidx):
        if not self.data_model:
            return list()
        def filter_(cand):
            return cand.lstrip('/').startswith(text.lstrip('/'))
        s = select_path(self.data_model, operations='R', filter_=filter_)
        return [' '.join(s)]

    # =========================================================================
    # GET - Get data/information
    # =========================================================================

    def _same_queue_for_endpoints(self, args, method_name):
        q = None
        for ep in args.endpoints:
            ep = self.lwm2m(ep)
            q = getattr(ep, method_name)(queue=q)
        return q

    @arg_parse
    def do_wiretap(self, args):
        q = self._same_queue_for_endpoints(args, 'wiretap')
        while True:
            get_and_pprint_packet(q)
            print()

    @arg_parse
    def do_registrations(self, args):
        q = self._same_queue_for_endpoints(args, 'registrations')
        while True:
            get_and_pprint_packet(q)
            print()

    def help_registrations(self):
        parser_registrations.print_help()

    @arg_parse
    def do_updates(self, args):
        q = self._same_queue_for_endpoints(args, 'updates')
        while True:
            get_and_pprint_packet(q)
            print()

    def help_updates(self):
        parser_updates.print_help()

    @arg_parse
    def do_commands(self, args):
        q = self._same_queue_for_endpoints(args, 'commands')
        while True:
            get_and_pprint_packet(q)
            print()

    def help_commands(self):
        parser_commands.print_help()

    @arg_parse
    def do_notifications(self, args):
        q = self._same_queue_for_endpoints(args, 'notifications')
        tracker = emqxlwm2m.lwm2m.NotificationsTracker()
        while True:
            event = q.get()
            if args.req_id is not None and args.req_id != event.req_id:
                continue
            print(f'{event.timestamp}  {event.ep} '
                  f'ReqPath = {event.req_path},  SeqNum = {event.seq_num}')
            if args.intervals:
                hist = tracker.timedelta(event)
                diffs = '  '.join(format(f, '.1f') for f in hist)
                print(f'dt = [ {diffs} ]')
            for path, value in event.items():
                if args.filter and not any(re.search(r, str(path))
                                           for r in args.filter):
                    continue
                if args.changes or args.changes_only:
                    changes = tracker.changes(event)
                    diff = changes.get(path)
                    if diff:
                        value = f'{diff[1]}  ({diff[0]})'
                    elif args.changes_only:
                        continue
                print(f'{str(path):15} {value}')
            print()
            tracker.add(event)

    def help_notifications(self):
        parser_notifications.print_help()

    @arg_parse
    def do_scan(self, args):
        for endpoint in args.endpoints:
            print(endpoint)
            ep = self.lwm2m(endpoint)
            q = ep.updates()
            ep.execute('1/0/8')
            resp = q.get()
            total = dict()
            for path in sorted(resp):
                try:
                    resp = ep.discover(path)
                except emqxlwm2m.ResponseError:
                    pass
                else:
                    total.update(resp)
            for path, attr in total.items():
                print(path, attr)

    def help_scan(self):
        parser_scan.print_help()

    # =========================================================================
    # DO - Do high level actions
    # =========================================================================

    @arg_parse
    def do_reboot(self, args):
        for _ in range(args.repeat):
            for ep in args.endpoints:
                ep = self.lwm2m(ep)
                emqxlwm2m.utils.reboot(ep, args.wait, args.timeout)

    @arg_parse
    def do_update(self, args):
        for ep in args.endpoints:
            ep = self.lwm2m(ep)
            upd = emqxlwm2m.utils.trigger_update(ep, args.wait, args.timeout)
            if upd:
                print(upd)

    @arg_parse
    def do_firmware_update(self, args):
        for ep in args.endpoints:
            ep = self.lwm2m(ep)
            for _ in range(args.retry + 1):
                if emqxlwm2m.utils.firmware_update(ep, args.package_uri):
                    if args.reboot:
                        emqxlwm2m.utils.reboot(ep, True, args.timeout)
                    break

def get_description_from_doc(method_name):
    docstr = getattr(CommandInterpreter, method_name).__doc__
    if not docstr:
        return None
    return textwrap.dedent(' '*6 + docstr)

# =============================================================================
# GLOBAL SETTINGS
# =============================================================================

parser = argparse.ArgumentParser(prog='python3 -m emqxlwm2m')
parser.add_argument(
    '--host',
    default='localhost',
    help='EMQx MQTT broker host (default: %(default)s).')
parser.add_argument(
    '--port', '-p',
    type=int,
    default=1883,
    help='EMQx MQTT port (default: %(default)s).')
parser.add_argument(
    '--timeout', '-t',
    type=float,
    metavar='SEC',
    default=8,
    help=('Timeout when waiting for response in seconds '
          f'(default: %(default)s).'))
parser.add_argument(
    "--log-level", "-l",
    choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
    default='INFO',
    help="Set the logging level (default: %(default)s).")
parser.add_argument(
    '--xml-path', '-x',
    action='append',
    help='Directory with xml lwm2m object definitions. '
         'Can be used multiple times to specify multiple paths.')
parser.add_argument(
    '--known-endpoints',
    type=str,
    default='endpoints.txt',
    help=(
        'Path to a file containing a list of endpoints - one per line. '
        'This option is only used for interactive selection (with fzf) '
        'when no endpoint has been provided explicitly.'))
parser.add_argument(
    "--ep-prefix",
    help="Add prefix to endpoint if missing when using the 'ep' command")
parser.add_argument(
    "--echo",
    action='store_true',
    help="Print endpoint and path when selected with fzf.")

top_subparsers = parser.add_subparsers(
    dest='command',
    title='Subcommands',
    description=(
        'All actions are grouped into the subcommands below. '
        'Use --help on each subcommand to learn more, e.g. '
        '"python3 -m emqxlwm2m lwm2m --help". If no subcommand '
        'is specified, an interactive session will start instead.'),
    required=False
)

# =============================================================================
# REUSABLE PARSERS
# =============================================================================

HELP_ENDPOINTS = """\
LwM2M Endpoint client names (e.g. urn:imei:123456789012345).
If a file is specified, the file will be read and each line
will be used as an endpoint. Use "-" for stdin.
"""

out_parser = argparse.ArgumentParser(add_help=False)
out_parser.add_argument(
    '--output', '-o',
    type=str,
    metavar='FILE',
    help='Send output to FILE instead of stdout.')

ep_parser = argparse.ArgumentParser(add_help=False)
ep_parser.add_argument(
    'endpoints',
    type=str,
    nargs='*',
    help=HELP_ENDPOINTS)

epath_parser = argparse.ArgumentParser(add_help=False)
epath_parser.add_argument(
    'epath',
    type=str,
    metavar='PATH',
    nargs='*',
    help=(
        'Path to LwM2M object, instance or resource. Syntax: oid/iid/rid. '
        'Optionally prepended by endpoint client name to select specific '
        'endpoint: endpoint/oid/iid/rid. Else, the endpoint will be taken '
        'from the --endpoints option.'))
epath_parser.add_argument(
    '--endpoints', '-e',
    type=str,
    nargs='+',
    help=HELP_ENDPOINTS)
# TODO: --debug for specific command only

# =============================================================================
# BASIC LWM2M OPERATIONS
# =============================================================================

parser_lwm2m = top_subparsers.add_parser(
    'lwm2m',
    help=(
        'Execute one of the elementary lwm2m operations: discover, read, '
        'write, write-attr, execute, create, delete, observe or cancel-observe'
    )
)
subparsers = parser_lwm2m.add_subparsers(
    dest='command',
    title='Basic lwm2m operation',
    required=False
)

# DISCOVER
parser_discover = subparsers.add_parser(
    'discover',
    parents=[epath_parser],
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description=get_description_from_doc('do_discover'),
    help=(
        'Discover which objects/resources are instantiated and their '
        'attached attributes.'))

# READ
parser_read = subparsers.add_parser(
    'read',
    parents=[epath_parser, out_parser],
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description=get_description_from_doc('do_read'),
    help=(
        'Read the value of a resource, an object instance or all the object'
        'instances of an object.'))
parser_read.add_argument(
    '--repeat', '-r',
    type=float,
    nargs='?',
    metavar='SEC',
    const=1,
    help='Repeat action every SEC seconds. Defaults to 1.')
parser_read.add_argument(
    '--format',
    type=str,
    metavar='FMT',
    default='dict',
    help='Format output')

# WRITE
parser_write = subparsers.add_parser(
    'write',
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description=get_description_from_doc('do_write'),
    help=(
        'Change the value of a resource, the values of an array of '
        'resources instances or the values of multiple resources from '
        'an object instance.'))
parser_write.add_argument(
    'epath',
    type=str,
    metavar='PATH=VALUE',
    nargs='*',
    help='asdf')
parser_write.add_argument(
    '--endpoints', '-e',
    type=str,
    nargs='+',
    help=HELP_ENDPOINTS)
parser_write.add_argument(
    '--batch',
    action='store_true',
    help=(
        'If u asdf    anges to rid=value.'))

# WRITE-ATTRIBUTES
parser_write_attr = subparsers.add_parser(
    'write-attr',
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description=get_description_from_doc('do_write_attr'),
    help=(
        'Write attributes {pmin, pmax, lt, st, gt} to resource, object or '
        'object instance.'))
parser_write_attr.add_argument(
    'epath',
    type=str,
    nargs='*',
    metavar='PATH=ATTRIBUTES',
    help='Syntax: /oid/iid/rid=[pmin,pmax]lt:st:gt')
parser_write_attr.add_argument(
    '--endpoints', '-e',
    type=str,
    nargs='+',
    help=HELP_ENDPOINTS)
parser_write_attr.add_argument(
    '--pmin',
    type=int,
    metavar='SEC',
    help='Seconds'
)
parser_write_attr.add_argument(
    '--pmax',
    type=int,
    metavar='SEC',
    help='Seconds'
)
parser_write_attr.add_argument(
    '--lt',
    type=float,
    help='Float'
)
parser_write_attr.add_argument(
    '--st',
    type=float,
    help='Float'
)
parser_write_attr.add_argument(
    '--gt',
    type=float,
    help='Float'
)

# EXECUTE
parser_execute = subparsers.add_parser(
    'execute',
    parents=[epath_parser],
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description=get_description_from_doc('do_execute'),
    help='Execute a resource.')
parser_execute.add_argument(
    '--args',
    type=str,
    help='Execute arguments')

# CREATE
parser_create = subparsers.add_parser(
    'create',
    parents=[epath_parser],
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description=get_description_from_doc('do_create'),
    help='Create object instance(s).')

# DELETE
parser_delete = subparsers.add_parser(
    'delete',
    parents=[epath_parser],
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description=get_description_from_doc('do_delete'),
    help='Delete an object instance.')

# OBSERVE
parser_observe = subparsers.add_parser(
    'observe',
    parents=[epath_parser],
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description=get_description_from_doc('do_observe'),
    help=(
        'Request notifications for changes of a specific resource, '
        'Resources within an object instance or for all the object '
        'instances of an object.'))
parser_observe.add_argument(
    '--track',
    action='store_true',
    help='Follow and print notifications')

# CANCEL OBSERVE
parser_cancel_observe = subparsers.add_parser(
    'cancel-observe',
    parents=[epath_parser],
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description=get_description_from_doc('do_cancel_observe'),
    help='End observation relationship for object instance or resource')


# =============================================================================
# GET DATA
# =============================================================================

parser_get = top_subparsers.add_parser(
    'get',
    help='Get notification, updates or registrations continuously.'
)
subparsers = parser_get.add_subparsers(
    dest='command',
    title='Basic lwm2m operation',
    required=False
)

q_parser = argparse.ArgumentParser(add_help=False)
q_parser.add_argument(
    '--intervals', '--dt',
    action='store_true',
    help='Print seconds since last time notification was received.')
q_parser.add_argument(
    '--changes', '-c',
    action='store_true',
    help='Print changes "new value (old value)".')
q_parser.add_argument(
    '--changes-only',
    action='store_true',
    help='Print only changed resources.')

# WIRETAP
parser_wiretap = subparsers.add_parser(
    'wiretap',
    parents=[ep_parser, q_parser],
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description=get_description_from_doc('do_wiretap'),
    help='Print everything downlink/uplink.')

# REGISTRATIONS
parser_registrations = subparsers.add_parser(
    'registrations',
    parents=[ep_parser, q_parser],
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description=get_description_from_doc('do_registrations'),
    help='Print registrations when received.')

# UPDATES
parser_updates = subparsers.add_parser(
    'updates',
    parents=[ep_parser, q_parser],
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description=get_description_from_doc('do_updates'),
    help='Print updates when received.')

# COMMAND
parser_commands = subparsers.add_parser(
    'commands',
    parents=[ep_parser, q_parser],
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description=get_description_from_doc('do_commands'),
    help='Print downlink/uplink commands when received.')

# NOTIFICATIONS
parser_notifications = subparsers.add_parser(
    'notifications',
    parents=[ep_parser, q_parser],
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description=get_description_from_doc('do_notifications'),
    help='Print notifications when received.')
parser_notifications.add_argument(
    '--filter',
    nargs='+',
    metavar='REGEX',
    help='Print any matching paths.')
parser_notifications.add_argument(
    '--req-id',
    type=int,
    help='Print matching req id.')


# =============================================================================
# DO STUFF
# =============================================================================

parser_do = top_subparsers.add_parser(
    'do',
    formatter_class=argparse.RawDescriptionHelpFormatter,
    help=(
        'Do actions specific to the LwM2M Objects defined by OMA '
        'For instance, firmware-update.')
)
subparsers = parser_do.add_subparsers(
    dest='command',
    title='Do actions on the LwM2M Objects defined by OMA',
    description='<table of objects>',
    required=False
)

# REBOOT
parser_reboot = subparsers.add_parser(
    'reboot',
    parents=[ep_parser],
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description=get_description_from_doc('do_reboot'),
    help='Execute the Reboot resource 3/0/4')
parser_reboot.add_argument(
    '--wait', '-w',
    action='store_true',
    help=(
        'Block and wait until registration is received. '
        'Print registration and duration spent waiting.'))
parser_reboot.add_argument(
    '--repeat',
    type=int,
    default=1,
    metavar='N',
    help='Repeat reboot N times.')

# UPDATE
parser_update = subparsers.add_parser(
    'update',
    parents=[ep_parser],
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description=get_description_from_doc('do_update'),
    help='Execute the Registration Update trigger resource 1/0/8')
parser_update.add_argument(
    '--wait', '-w',
    action='store_true',
    help=(
        'Block and wait until update is received. '
        'Print update and duration spent waiting.'))

# FOTA
parser_firmware_update = subparsers.add_parser(
    'firmware-update',
    parents=[ep_parser],
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description=get_description_from_doc('do_firmware_update'),
    help='Perform firmware update. Requires Object ID 5.')
parser_firmware_update.add_argument(
    '--package-uri', '-u',
    help='Package URI'
)
parser_firmware_update.add_argument(
    '--retry',
    type=int,
    default=0,
    metavar='N',
    help='Retry at most N times if failure.'
)
parser_firmware_update.add_argument(
    '--reboot',
    action='store_true',
    help='Reboot device after successful firmware update.')

# SCAN
parser_scan = subparsers.add_parser(
    'update',
    parents=[ep_parser],
    formatter_class=argparse.RawDescriptionHelpFormatter,
    description=get_description_from_doc('do_scan'),
    help='Discover everything')
