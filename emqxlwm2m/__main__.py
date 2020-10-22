"""CLI entry point of emqxlwm2m.

Run `python3 -m emqxlwm2m --help` to get the command line interface
help.
"""

# Built-in
import argparse
import logging
import sys
import time
import os

# PyPI
import rich.logging

# Package
import emqxlwm2m
import emqxlwm2m.loadobjects
import emqxlwm2m.history
from emqxlwm2m.engines.emqx import EMQxEngine, str_to_py_value
from emqxlwm2m.cmdloop import CommandInterpreter


def print_notifications(notify_queue):
    tracker = emqxlwm2m.lwm2m.NotificationsTracker()
    while True:
        event = notify_queue.get()
        CONSOLE.print(f'{event.timestamp}  {event.ep} '
                      f'ReqPath = {event.req_path},  '
                      f'SeqNum = {event.seq_num}')
        hist = tracker.timedelta(event)
        diffs = '  '.join(format(f, '.1f') for f in hist)
        CONSOLE.print(f'dt = [ {diffs} ]')
        for res_path, res_value in event.items():
            CONSOLE.print(f'{str(res_path):15} {res_value}')
        try:
            event.check()
        except emqxlwm2m.ResponseError:
            CONSOLE.print(event.code)
        print()
        tracker.add(event)


CMDS = frozenset({
    # Custom
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

parser = argparse.ArgumentParser(prog='python3 -m emqxlwm2m')
parser.add_argument(
    'command',
    type=str,
    nargs='?',
    choices=CMDS,
    help='Select a command.')
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
FMT_STDOUT = '%(asctime)s %(name)s %(levelname)s %(message)s'
logging.basicConfig(
    level=getattr(logging, args.log_level),
    format=FMT_STDOUT,
    datefmt="[%X]",
    handlers=[rich.logging.RichHandler(rich_tracebacks=True)]
)
CONSOLE = rich.console.Console()

if args.command is None:
    # If no command is provided, the interactive cmd loop will start.
    print('WARN: The interactive interface is not supported yet.')
    print('Enter "q" to quit.')
    try:
        eng = EMQxEngine.via_mqtt(
            host=args.host,
            port=args.port,
            max_subs=100,
            timeout=args.timeout)
        eng.host = args.host
        eng.port = args.port
        xml2obj = emqxlwm2m.loadobjects.load_objects(
            args.xml_path, load_builtin=True)
        cwd = '/' + os.environ.get('ENDPOINT', '')
        intrpr = CommandInterpreter(
            eng, cwd, data_model=xml2obj,
            known_endpoints=args.known_endpoints, timeout=args.timeout)
        emqxlwm2m.history.load_cmd_history()
        try:
            # Blocking, run loop until user quits
            intrpr.cmdloop()
        finally:
            emqxlwm2m.history.save_cmd_history()
    except emqxlwm2m.ResponseError as error:
        sys.exit(f'{type(error).__name__}: {error}')
    except (KeyboardInterrupt, BrokenPipeError):
        print('Bye')
    sys.exit(0)

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
    with open(args.known_endpoints, 'r', encoding='utf-8') as file:
        print('file:', args.known_endpoints)
        print(file.read())
    sys.exit(0)
no_path_actions = {'registrations', 'updates', 'notifications', 'discoverall'}
if args.endpoint is None:
    if not args.known_endpoints:
        sys.exit('No endpoint provided.')
    args.endpoint = emqxlwm2m.history.select_endpoint(
        CONSOLE, args.known_endpoints)
    if not args.endpoint:
        sys.exit('No endpoint selected.')
    args.endpoint = args.endpoint[0]
    emqxlwm2m.history.add_endpoint_to_history(args.endpoint)
    if args.echo:
        print('endpoint:', args.endpoint)
if args.command is None:
    print('specify command pls')
    sys.exit(0)
path_needed = args.path is None and args.command not in no_path_actions
if path_needed:
    xml2obj = emqxlwm2m.loadobjects.load_objects(
        args.xml_path, load_builtin=True)
    args.path = emqxlwm2m.history.select_path(
        CONSOLE, xml2obj, operations=args.command)
    if not args.path:
        sys.exit('No path selected.')
    args.path = args.path[0]
    emqxlwm2m.history.add_path_to_history(args.path)
    if args.echo:
        print('path:', args.path)

try:
    eng = EMQxEngine.via_mqtt(
        host=args.host,
        port=args.port,
        max_subs=100,
        timeout=args.timeout)
    with eng as g:
        lwm2m: emqxlwm2m.lwm2m.Endpoint = g.endpoint(args.endpoint)
        if args.command == 'discover':
            resp = lwm2m.discover(args.path)
            resp.check()
            CONSOLE.print(resp.data)
        elif args.command == 'read':
            while True:
                resp = lwm2m.read(args.path)
                resp.check()
                CONSOLE.print(resp.data)
                if args.interval:
                    time.sleep(args.interval)
                else:
                    break
        elif args.command == 'write':
            if args.value is None:
                args.value = input(f'Write to {args.path}: ')
            values = args.value.split()
            for v in values:
                v = str_to_py_value(v)
                resp = lwm2m.write(args.path, v)
                resp.check()
                CONSOLE.print(resp)
                if args.interval and len(values) > 1:
                    CONSOLE.print(v)
                    time.sleep(args.interval)
        elif args.command == 'attr':
            if args.value is None:
                args.value = input(f'Write attributes to {args.path} '
                                   '(format "[pmin,pmax]lt:st:gt" ): ')
            attr = emqxlwm2m.lwm2m.Attributes.from_string(args.value)
            resp = lwm2m.write_attr(path=args.path, **dict(attr))
            resp.check()
            CONSOLE.print(resp)
        elif args.command == 'execute':
            if args.value is None:
                args.value = ''
            resp = lwm2m.execute(args.path, args.value)
            resp.check()
            CONSOLE.print(resp)
        elif args.command == 'create':
            if args.value is None:
                print('basePath = {args.path}')
                args.value = input(
                    f'Resource values '
                    f'(format relativePath=value, e.g. /0/1=hello): ')
            parts = args.value.split()
            values = dict()
            for v in parts:
                path, value = v.split('=')
                value = str_to_py_value(value.replace('_', ' '))
                values[path.strip()] = value
            resp = lwm2m.create(args.path, values)
            resp.check()
            CONSOLE.print(resp)
        elif args.command == 'delete':
            resp = lwm2m.delete(args.path)
            resp.check()
            CONSOLE.print(resp)
        elif args.command == 'observe':
            resp, q = lwm2m.observe(args.path)
            resp.check()
            CONSOLE.print(resp.data)
            print('Waiting for notifications ...')
            print_notifications(q)
        elif args.command == 'cancel-observe':
            resp = lwm2m.cancel_observe(args.path)
            resp.check()
            CONSOLE.print(resp.data)
        elif args.command == 'registrations':
            q = lwm2m.registrations()
            while True:
                CONSOLE.print(q.get())
                print()
        elif args.command == 'updates':
            q = lwm2m.updates()
            while True:
                CONSOLE.print(q.get())
                print()
        elif args.command == 'notifications':
            q = lwm2m.notifications()
            print_notifications(q)
        elif args.command == 'discoverall':
            q = lwm2m.updates()
            resp = lwm2m.execute('1/0/8')
            resp.check()
            total = dict()
            upd = q.get()
            for path in sorted(upd):
                try:
                    resp = lwm2m.discover(path)
                except emqxlwm2m.ResponseError:
                    pass
                else:
                    total.update(resp.data)
            CONSOLE.print(total)
except emqxlwm2m.ResponseError as error:
    sys.exit(f'{type(error).__name__}: {error}')
except (KeyboardInterrupt, BrokenPipeError):
    print('Bye')
