"""CLI entry point of emqxlwm2m.

Run `python3 -m emqxlwm2m --help` to get the command line interface
help.
"""

# Built-in
import argparse
import collections
import logging
import pathlib
import sys
import tempfile
import time

# Package
import emqxlwm2m.core
import emqxlwm2m.loadobjects

SELECTION_ENDPOINTS_CACHE = 'emqxlwm2m.endpoints.cache'
SELECTION_PATH_CACHE = 'emqxlwm2m.path.cache'


class SelectionCache:
    """Sort selection by historical usage"""

    def __init__(self, cache_file, history=10):
        """Initialization of SelectionCache"""
        self.cache_file = cache_file
        self.history = history
        self.usage_count = collections.Counter()
        self.index = dict()
        self.ep = ''
        self.cache_dir = pathlib.Path(tempfile.gettempdir())

    def update(self, endpoint):
        self.ep = endpoint

    def sort_index(self, endpoint):
        return (self.usage_count[endpoint.split()[0]],
                self.index.get(endpoint, 0))

    def __enter__(self):
        try:
            with open(self.cache_dir / self.cache_file, 'r') as file:
                lines = [l.strip() for l in file.readlines() if l.strip()]
        except FileNotFoundError:
            lines = list()
        else:
            lines = lines[-self.history:]
        for i, line in enumerate(lines):
            self.index[line] = i
        if lines:
            self.usage_count.update(lines)
            self.usage_count[lines[-1]] = self.history
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.ep:
            with open(self.cache_dir / self.cache_file, 'a') as file:
                file.write(f'{self.ep}\n')


def ensure_iterfzf():
    try:
        import iterfzf
    except ModuleNotFoundError:
        sys.exit('iterfzf not installed: $ python3 -m pip install iterfzf')


def endpoint_selection(known_endpoints, history=10):
    """Select endpoint from predefined list in file"""
    ensure_iterfzf()
    import iterfzf
    with SelectionCache(SELECTION_ENDPOINTS_CACHE, history) as cache:
        with open(known_endpoints, 'r') as file:
            endpoints = [
                l.strip() for l in file.readlines() if l.strip()
            ]
        endpoints.sort(key=cache.sort_index, reverse=True)
        ep = iterfzf.iterfzf(endpoints, exact=True)
        if ep is None:
            return None
        ep = ep.split()[0]
        cache.update(ep)
        return ep


def load_paths(xml2obj, max_width=120, operations=None):
    """Parse XMLs of LwM2M obj. def. and return paths for selection"""
    try:
        from termcolor import colored
    except ModuleNotFoundError:
        colored = lambda x, c: x
    ops = set()
    if operations.startswith('exec'):
        ops.add('E')
    elif operations in {'read', 'observe', 'cancel-observe'}:
        ops.add('R')
        ops.add('RW')
    elif operations == 'write':
        ops.add('W')
        ops.add('RW')
    tail = ' ...'
    paths = list()
    for obj in xml2obj.values():
        obj_info = obj.mandatory_str[:3] + ' ' + obj.multiple_str[:3]
        path = f'/{obj.oid}   ' + colored(obj.name, 'magenta')
        path = f'{path:35} {obj_info}'
        path = f'{path:55}'
        obj_desc = obj.description.replace('\n', ', ')
        if len(obj.description) > max_width - len(path):
            length = slice(0, max(0, max_width - len(tail) - len(path)))
            obj_desc = obj.description[length] + tail
        path = f'{path} ' + colored(obj_desc, 'green')
        # Add object
        paths.append(path)
        # Add object instance
        paths.append(path.replace(f'/{obj.oid}   ', f'/{obj.oid}/0 '))
        # Add object instance resources
        for res in obj.resources:
            if ops and res.operations not in ops:
                continue
            res_info = res.type[:3].title() + ' ' + \
                res.mandatory_str[:3] + ' ' + \
                res.multiple_str[:3] + ' ' + \
                res.operations
            res_desc = res.description.replace('\n', ', ')
            path = f'/{obj.oid}/0/{res.rid} ' + colored(res.name, 'red')
            path = f'{path:35} {res_info}'
            path = f'{path:55}'
            if len(res_desc) > max_width - len(path):
                length = slice(0, max(0, max_width - len(tail) - len(path)))
                res_desc = res_desc[length] + tail
            path = f'{path} ' + colored(res_desc, 'blue')
            paths.append(path)
    return paths


def path_selection(paths, history=10):
    """Select path with fzf."""
    ensure_iterfzf()
    import iterfzf
    with SelectionCache(SELECTION_PATH_CACHE, history) as cache:
        paths.sort(key=cache.sort_index, reverse=True)
        # Monkey patch to get terminal colors
        from subprocess import Popen
        def monkey(cmd, **kwargs):
            return Popen(cmd + ['--ansi'], **kwargs)
        iterfzf.subprocess.Popen = monkey
        p = iterfzf.iterfzf(paths, exact=True)
        iterfzf.subprocess.Popen = Popen
        if p is None:
            return None
        p = p.split()[0]
        cache.update(p)
        return p

CMDS = frozenset({
    # Custom
    "?",
    "endpoints",
    "discoverall",
    # Shortcuts
    "reboot",
    "update",
    # Events
    "registrations",
    "updates",
    "notifications",
    # Commands
    "read",
    "discover",
    "write",
    "attr",
    "execute",
    "create",
    "delete",
    "observe",
    "cancel-observe"
})

def cmd_selection():
    ensure_iterfzf()
    import iterfzf
    return iterfzf.iterfzf(CMDS, exact=True)

parser = argparse.ArgumentParser(prog='python3 -m emqxlwm2m')
parser.add_argument(
    'command',
    type=str,
    nargs='?',
    choices=CMDS,
    help='Select a command interactively with fzf.')
parser.add_argument(
    'endpoint',
    type=str,
    nargs='?',
    help='LwM2M endpoint client name')
parser.add_argument(
    'path',
    type=str,
    nargs='?',
    help='LwM2M object/instance/resource path')
parser.add_argument(
    '--host',
    default='localhost',
    help='EMQx MQTT broker host')
parser.add_argument(
    '--port', '-p',
    type=int,
    default=1883,
    help='EMQx MQTT port')
parser.add_argument(
    '--known-endpoints',
    type=str,
    default='endpoints.txt',
    help='Path to list of known endpoints. Used for interactive selection.')
parser.add_argument(
    '--xml-path', '-x',
    action='append',
    help='Directory with xml lwm2m object definitions. '
         'Can be used multiple times to provide multiple paths.')
parser.add_argument(
    "-l", "--log-level",
    choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
    default='WARNING',
    help="Set the logging level")
parser.add_argument(
    "--echo",
    action='store_true',
    help="Print endpoint and path when selected with fzf.")
parser.add_argument(
    '--value', '-v',
    type=str,
    help='Value to use in context of command.')
parser.add_argument(
    '--interval', '-i',
    type=float,
    help='Repeat action with interval. Seconds.')
parser.add_argument(
    '--timeout', '-t',
    type=float,
    help='Timeout when waiting for response. Seconds.')

args = parser.parse_args()

FMT_STDOUT = '%(asctime)s %(threadName)s %(levelname)s '\
             '%(name)s(%(lineno)d) %(message)s'
logging.basicConfig(format=FMT_STDOUT, level=getattr(logging, args.log_level))

if args.command == '?':
    args.command = cmd_selection()

if args.command == 'reboot':
    args.path = '/3/0/4'
    args.command = 'execute'
elif args.command == 'disable':
    args.path = '/1/0/4'
    args.command = 'execute'
elif args.command == 'update':
    args.path = '/1/0/8'
    args.command = 'execute'

elif args.command == 'endpoints':
    if args.known_endpoints is None:
        sys.exit('No known endpoints provided (--known-endpoints).')
    with open(args.known_endpoints, 'r') as file:
        print('file:', args.known_endpoints)
        print(file.read())
    sys.exit(0)
no_path_actions = {'registrations', 'updates', 'notifications', 'discoverall'}
if args.endpoint is None:
    if not args.known_endpoints:
        sys.exit('No endpoint provided.')
    args.endpoint = endpoint_selection(args.known_endpoints)
    if args.endpoint is None:
        sys.exit('No endpoint selected.')
    if args.echo:
        print('endpoint:', args.endpoint)
if args.command is None:
    print('specify command pls')
    sys.exit(0)
path_needed = args.path is None and args.command not in no_path_actions
if path_needed:
    xml2obj = emqxlwm2m.loadobjects.load_objects(args.xml_path)
    lines = load_paths(xml2obj, operations=args.command)
    args.path = path_selection(lines)
    if args.path is None:
        sys.exit('No path selected.')
    if args.echo:
        print('path:', args.path)

try:
    with emqxlwm2m.core.LwM2MGateway.via_mqtt(args.host, args.port) as g:
        lwm2m: emqxlwm2m.core.LwM2MGateway = g.new_lwm2m(args.endpoint)
        if args.command == 'discover':
            value = lwm2m.discover(args.path, args.timeout)
            print(value)
        elif args.command == 'read':
            while True:
                value = lwm2m.read(args.path, args.timeout)
                print(value)
                if args.interval:
                    time.sleep(args.interval)
                else:
                    break
        elif args.command == 'write':
            if args.value is None:
                args.value = input(f'Write to {args.path}: ')
            values = args.value.split()
            for v in values:
                lwm2m.write(args.path, v, args.timeout)
                if args.interval and len(values) > 1:
                    print(v)
                    time.sleep(args.interval)
        elif args.command == 'attr':
            if args.value is None:
                args.value = input(f'Write attributes to {args.path} '
                                   '(format "[pmin,pmax]lt:st:gt" ): ')
            if args.value == '':
                print('No attributes provided. Doing a discovery instead:')
                value = lwm2m.discover(args.path, args.timeout)
                print(value)
            else:
                attr = emqxlwm2m.core.Attributes.from_string(args.value)
                lwm2m.write_attr(args.path, **attr.as_dict(), timeout=args.timeout)
        elif args.command == 'execute':
            if args.value is None:
                args.value = ''
            lwm2m.execute(args.path, args.value, timeout=args.timeout)
        elif args.command == 'create':
            if args.value is None:
                print('basePath = {args.path}')
                args.value = input(f'Resource values (format relativePath=value, e.g. /0/1=hello): ')
            parts = args.value.split()
            values = dict()
            for v in parts:
                path, value = v.split('=')
                values[path.strip()] = value.strip()
            lwm2m.create(args.path, values, args.timeout)
        elif args.command == 'delete':
            lwm2m.delete(args.path, args.timeout)
        elif args.command == 'observe':
            value = lwm2m.observe(args.path, args.timeout)
            print(value)
        elif args.command == 'cancel-observe':
            lwm2m.cancel_observe(args.path, args.timeout)
        elif args.command == 'registrations':
            for t, data in lwm2m.registrations():
                print(f'{t}  Registration: {data}')
        elif args.command == 'updates':
            for t, data in lwm2m.updates():
                print(f'{t}  Update: {data}')
        elif args.command == 'notifications':
            timetracker = dict()
            for t, req_id, seq_num, data in lwm2m.notifications():
                print(f'ReqID = {req_id}, SeqNum = {seq_num}')
                for path, value in data.items():
                    hist = timetracker.setdefault((req_id, path), collections.deque(maxlen=10))
                    hist.append(t)
                    h = list(hist)
                    diffs = [(b - a).total_seconds() for a, b in zip(h[:], h[1:])]
                    diffs = '  '.join([format(f, '.1f') for f in reversed(diffs)])
                    print(f'{t}  {str(path):15} {value:<20} [{diffs}]')
                print()
        elif args.command == 'discoverall':
            # TODO: Cleanup
            from termcolor import colored
            try:
                lwm2m.execute('/1/0/8', timeout=0)
            except emqxlwm2m.core.LwM2MTimeout:
                pass
            _, upd = next(lwm2m.updates(timeout=10))
            for path in upd['objectList']:
                print('='*40)
                try:
                    data = lwm2m.read(path)
                    disc = lwm2m.discover(path)
                except emqxlwm2m.core.LwM2MErrorResponse as error:
                    print(colored(path, attrs=['bold']))
                    print(error)
                    print()
                    continue
                attr = emqxlwm2m.core.Attributes()
                for key in attr.as_dict():
                    setattr(attr, key, disc.get(path).get(key))
                if str(attr):
                    a = colored(str(attr), 'red')
                    path = colored(f'{path} {a} ', attrs=['bold'])
                else:
                    path = colored(str(path), attrs=['bold'])
                print(path)
                for p, v in data.items():
                    attr = emqxlwm2m.core.Attributes()
                    for key in attr.as_dict():
                        setattr(attr, key, disc.get(p).get(key))
                    a = colored(str(attr), 'red')
                    v = colored(str(v), 'blue')
                    p = f'{str(p)} {str(a)}'
                    print(f'{p:15}  {v}')
                print()
except emqxlwm2m.core.LwM2MTimeout as error:
    sys.exit(f'{type(error).__name__}: {error}')
except emqxlwm2m.core.LwM2MErrorResponse as error:
    sys.exit(f'{type(error).__name__}: {error}')
except (KeyboardInterrupt, BrokenPipeError):
    print('Bye')
