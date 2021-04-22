"""CommandInterpreter based on cmd2"""

# Built-in
import logging
import datetime as dt
import itertools
import functools
import shlex
import time

# PyPI
import cmd2
import rich
import iterfzf

# Package
import emqxlwm2m
import emqxlwm2m.engines.emqx
import emqxlwm2m.utils
import emqxlwm2m.parsers as parser
from emqxlwm2m.lwm2m import Path
from emqxlwm2m.history import *

# Monkey patch cmd2 to get posix=True. Without this patch, the cli
# argument 1/2/3="abc def" will be split into two arguments:
# '1/2/3="abc' and 'def"'.
cmd2.parsing.shlex_split = functools.partial(
    shlex.split, comments=False, posix=True
)


def extract_paste(text):
    for line in text.splitlines():
        if line.startswith("#"):
            continue
        yield line.split()[0].lstrip()


def ispath(text: str):
    """Return True if text starts with a LwM2M Path"""
    text = text.strip()
    path = text.split("=")[0]
    path = path.strip()
    if "//" in path:
        return False
    parts = path.split("/")
    digits = "".join(parts)
    return digits.isdigit()


def fix_paths(args):
    # Fix paths mistaken as endpoints
    if not hasattr(args, "endpoint"):
        return
    for ep in args.endpoint[:]:
        if ispath(ep):
            args.endpoint.remove(ep)
            try:
                args.path.append(ep)
            except AttributeError:
                continue


def endpoint_pathval(meth):
    """Fix & ensure endpoints and paths decorator"""

    @functools.wraps(meth)
    def wrapper(self, args):
        fix_paths(args)
        self.ensure_endpoints(args)
        self.ensure_path(args)
        return meth(self, args)

    return wrapper


def endpoint(meth):
    """Ensure endpoint decorator"""

    @functools.wraps(meth)
    def wrapper(self, args):
        self.ensure_endpoints(args)
        return meth(self, args)

    return wrapper


def valsplit(p: str):
    """Split value from path"""
    parts = p.split("=", maxsplit=1)
    if len(parts) == 1:
        return parts[0], None
    return parts[0], parts[1]


class CommandInterpreter(cmd2.Cmd):  # Todo: plugins
    """Interpreter for interactive commands"""

    def __init__(
        self,
        engine: emqxlwm2m.engines.emqx.EMQxEngine,
        timeout: float = None,
        data_model: dict = None,
        ep_active: str = "",
        ep_known: str = None,
        ep_prefix: str = "",
        **kwargs,
    ):
        """Initialization of LwM2M CommandInterpreter"""
        shortcuts = dict(cmd2.DEFAULT_SHORTCUTS)
        shortcuts.update({"fota": "firmware_update", "attr": "write_attr"})
        super().__init__(shortcuts=shortcuts, **kwargs)
        self.console = rich.console.Console()
        self.log = logging.getLogger("Intrpr")
        self.engine = engine
        self.timeout = timeout  # Seconds
        self.data_model = data_model  # XML object definitions
        self.ep_active = ep_active  # Endpoint active
        self.ep_known = ep_known
        self.ep_prefix = ep_prefix

    def poutput(self, msg="", *, end: str = "\n", **kwargs) -> None:
        # Override and use rich console
        with self.console.capture() as capture:
            self.console.print(msg, end="", **kwargs)
        super().poutput(capture.get().rstrip("\n"), end=end)

    @functools.lru_cache(maxsize=20)
    def cache(self, endpoint: str) -> emqxlwm2m.lwm2m.Endpoint:
        """Cached Endpoint instances.

        Used to prevent unnecessary subscribe/unsubscribe calls.
        """
        return self.engine.endpoint(endpoint, self.timeout)

    def preloop(self):
        self.gw = self.engine.__enter__()

    def postloop(self):
        self.gw.__exit__(None, None, None)

    def do_q(self, line):
        """quit interpreter"""
        return True

    def do_exit(self, line):
        """exit interpreter"""
        return True

    def do_sleep(self, line):
        """Sleep seconds"""
        t = float(line.strip())
        self.poutput(f"Sleeping for {t} seconds ...")
        time.sleep(t)

    def do_hist(self, line):
        """Fzf select command from history and run it"""
        seen = {"q", "hist"}
        candidates = list()
        for h in reversed(self.history):
            cmd = h.statement.raw.strip()
            if cmd in seen:
                continue
            seen.add(cmd)
            candidates.append(cmd)
        cmd = iterfzf.iterfzf(candidates, exact=True)
        if cmd:
            self.poutput(cmd)
            self.runcmds_plus_hooks([cmd])

    def do_paste(self, line):
        text = cmd2.clipboard.get_paste_buffer()
        for ep in extract_paste(text):
            self.poutput(ep)

    @property
    def prompt(self):
        timestamp = format(dt.datetime.now(), "%H:%M:%S")
        with self.console.capture() as capture:
            self.console.print(end="\n")
            self.console.print(f"[{timestamp}]", end=" ")
            self.console.print(self.engine.host, style="red", end=":")
            self.console.print(f"[black]{self.engine.port}", end="")
            self.console.print(f"\n{self.ep_active}$", style="black", end=" ")
        return capture.get()

    def do_ep(self, line):
        """Set active endpoint"""
        line = line.strip()
        if line == "clear":
            self.ep_active = ""
            return
        if line:
            if self.ep_prefix and not line.startswith(self.ep_prefix):
                line = self.ep_prefix + line
            ep = [line]
        else:
            ep = self.select_ep()
        if ep is not None:
            if self.ep_active != ep[-1]:
                # Draw horizontal line when active endpoint changes
                self.console.rule()
                self.ep_active = ep[-1]
                add_endpoint_to_history(self.ep_active)

    def select_ep(self):
        """Select endpoint interactively with fzf"""
        return select_endpoint(self.console, self.ep_known)

    def complete_ep(self, text, line, begidx, endidx):
        if self.ep_known:
            ep = self.select_ep()
            if ep is not None:
                return ep
        return list()

    def ensure_endpoints(self, args):
        if not args.endpoint:
            # No endpoint provided, use active or select
            if self.ep_active:
                args.endpoint = [self.ep_active]
            else:
                args.endpoint = self.select_ep()
        if not args.endpoint:
            raise Exception("Endpoint argument missing")

        # Find files containing endpoints and extend args.endpoint
        args.endpoint = endpoints_from_file(args.endpoint)

        # If special word "paste", take endpoints from clipboard
        try:
            args.endpoint.remove("paste")
        except ValueError:
            pass
        else:
            text = cmd2.clipboard.get_paste_buffer()
            for ep in extract_paste(text):
                args.endpoint.append(ep)

        # Make sure endpoint starts with ep_prefix
        for i in range(len(args.endpoint)):
            ep = args.endpoint[i]
            if not ep.startswith(self.ep_prefix):
                args.endpoint[i] = f"{self.ep_prefix}{ep}"

        # Add endpoints to history file
        for ep in args.endpoint:
            add_endpoint_to_history(ep)

    def select_path(self):
        """Select path interactively with fzf"""
        return select_path(self.console, self.data_model)

    def _complete_path(self, text, line, begidx, endidx):
        if not self.data_model:
            return list()

        def filter_(cand):
            return cand.lstrip("/").startswith(text.lstrip("/"))

        s = select_path(self.console, self.data_model, filter_=filter_)
        return [" ".join(s)]

    def ensure_path(self, args):
        if not args.path:
            # No paths provided, select paths interactively
            args.path = self.select_path()
        if not args.path:
            raise Exception("Path argument missing")
        for p in args.path:
            add_path_to_history(p.split("=")[0])

    def print_message(self, msg: emqxlwm2m.lwm2m.Message):
        """Print a LwM2M message in a pretty way"""

        # Figure out if timeout or error occurred
        timeout = False
        error = False
        if isinstance(msg, emqxlwm2m.NoResponseError):
            msg = msg.args[0]
            timeout = True
        elif isinstance(msg, emqxlwm2m.ResponseError):
            msg = msg.args[0]
            error = True
        elif isinstance(
            msg, (emqxlwm2m.lwm2m.Response, emqxlwm2m.lwm2m.Notification)
        ):
            try:
                msg.check()
            except emqxlwm2m.ResponseError:
                error = True

        # Print endpoint name
        if isinstance(msg, emqxlwm2m.lwm2m.Downlink):
            self.poutput(msg.ep, end=" < ")
        else:  # Uplink
            self.poutput(msg.ep, end=" > ")

        # Print message type
        name = type(msg).__name__
        if isinstance(
            msg, (emqxlwm2m.lwm2m.Registration, emqxlwm2m.lwm2m.Update)
        ):
            self.poutput(f"[bold black]{name}", end=" ")
        elif isinstance(msg, emqxlwm2m.lwm2m.Notification):
            self.poutput(f"[italic black]{name}", end=" ")
        else:
            self.poutput(name, end=" ")

        # Print registration or update
        if isinstance(
            msg, (emqxlwm2m.lwm2m.Registration, emqxlwm2m.lwm2m.Update)
        ):
            self.poutput(f"lt={msg.lt}", end=" ")
            self.poutput(f"sms={msg.sms}", end=" ")
            self.poutput(f"lwm2m={msg.lwm2m}", end=" ")
            self.poutput(f"b={msg.b}", end=" ")
            self.poutput(f"alternate_path={msg.alternate_path}", end=" ")
            self.poutput(msg.data)
            return

        # Print requests
        if isinstance(msg, emqxlwm2m.lwm2m.Request):
            if timeout:
                self.poutput("[bold red]TIMEOUT", end=" ")
        if isinstance(msg, emqxlwm2m.lwm2m.WriteAttrRequest):
            self.poutput(f"path={msg.path}", end=" ")
            self.poutput(f"pmin={msg.pmin}", end=" ")
            self.poutput(f"pmax={msg.pmax}", end=" ")
            self.poutput(f"lt={msg.lt}", end=" ")
            self.poutput(f"st={msg.st}", end=" ")
            self.poutput(f"gt={msg.gt}")
            return
        if isinstance(msg, emqxlwm2m.lwm2m.ExecuteRequest):
            self.poutput(f"path={msg.path}", end=" ")
            self.poutput(f"args={msg.args!r}")
            return
        if isinstance(
            msg, (emqxlwm2m.lwm2m.WriteRequest, emqxlwm2m.lwm2m.CreateRequest)
        ):
            self.poutput(msg.data)
            return
        if isinstance(msg, emqxlwm2m.lwm2m.Request):
            self.poutput(f"path={msg.path}")
            return

        # Handle responses
        if error:
            color = "[bold red]"
        else:
            color = "[green]"
        self.poutput(f"{color}{msg.code.name} {msg.code.value}[/]", end=" ")
        if isinstance(msg, emqxlwm2m.lwm2m.Notification):
            self.poutput(f"Seq={msg.seq_num}", end=" ")
        if hasattr(msg, "data"):
            self.poutput(msg.data)
        else:
            self.poutput(f"{color}ReqPath {msg.req_path}[/]")

    def print_notifications(self, notify_queue, stop_after=10 ** 10):
        tracker = emqxlwm2m.lwm2m.NotificationsTracker()
        for _ in range(stop_after):
            msg = notify_queue.get()
            hist = tracker.timedelta(msg)
            diffs = "  ".join(format(f, ".1f") for f in hist)
            self.poutput(f"\ndt = [ {diffs} ]")
            self.print_message(msg)
            tracker.add(msg)

    # =========================================================================
    # Basic LwM2M operations
    # =========================================================================

    @cmd2.with_argparser(parser.discover)
    @endpoint_pathval
    def do_discover(self, args):
        for _ in range(args.count):
            for ep in args.endpoint:
                ep = self.cache(ep)
                for path in args.path:
                    path, _ = valsplit(path)
                    try:
                        resp = ep.discover(path, timeout=args.timeout)
                        self.print_message(resp)
                    except emqxlwm2m.ResponseError as error:
                        self.print_message(error)
            if args.repeat is None:
                break
            time.sleep(args.repeat)

    def complete_discover(self, text, line, begidx, endidx):
        return self._complete_path(text, line, begidx, endidx)

    # -------------------------------------------------------------------------

    @cmd2.with_argparser(parser.read)
    @endpoint_pathval
    def do_read(self, args):
        for _ in range(args.count):
            for ep in args.endpoint:
                ep = self.cache(ep)
                for path in args.path:
                    path, _ = valsplit(path)
                    try:
                        resp = ep.read(path, timeout=args.timeout)
                        self.print_message(resp)
                    except emqxlwm2m.ResponseError as error:
                        self.print_message(error)
            if args.repeat is None:
                break
            time.sleep(args.repeat)

    def complete_read(self, text, line, begidx, endidx):
        return self._complete_path(text, line, begidx, endidx)

    # -------------------------------------------------------------------------

    @cmd2.with_argparser(parser.write)
    @endpoint_pathval
    def do_write(self, args):
        # Make sure each path has a value
        pathvals = list()
        for path in args.path:
            p, value = valsplit(path)
            if value is None:
                if args.value is not None:
                    value = args.value
                else:
                    value = input(f"Write value to {p}: ")
            value = emqxlwm2m.engines.emqx.str_to_py_value(value)
            pathvals.append((Path(p), value))
        pathvals.sort()

        for _ in range(args.count):
            # Make writes for each endpoint
            for ep in args.endpoint:
                ep = self.cache(ep)
                if args.batch:
                    # Batch write, group by oid/iid
                    def group(pval):
                        p, _ = pval
                        base_path = f"{p.oid}/{p.iid}"
                        return base_path

                    groups = itertools.groupby(pathvals, key=group)
                    for _, chunk in groups:
                        try:
                            resp = ep.write(
                                "", dict(chunk), timeout=args.timeout
                            )
                            self.print_message(resp)
                        except emqxlwm2m.ResponseError as error:
                            self.print_message(error)
                else:
                    # Write in sequence
                    for p, value in pathvals:
                        try:
                            resp = ep.write(p, value, timeout=args.timeout)
                            self.print_message(resp)
                        except emqxlwm2m.ResponseError as error:
                            self.print_message(error)
            if args.repeat is None:
                break
            time.sleep(args.repeat)

    def complete_write(self, text, line, begidx, endidx):
        return self._complete_path(text, line, begidx, endidx)

    # -------------------------------------------------------------------------

    @cmd2.with_argparser(parser.write_attr)
    @endpoint_pathval
    def do_write_attr(self, args):

        # Default attributes
        flags = dict(
            pmin=args.pmin, pmax=args.pmax, lt=args.lt, st=args.st, gt=args.gt
        )
        flags = {k: v for k, v in flags.items() if v is not None}
        if args.value is not None:
            attrdict = emqxlwm2m.lwm2m.Attributes.from_string(args.value)
            flags.update(attrdict)

        # Make sure each path has at least one attribute
        pathattrs = list()
        for path in args.path:
            p, attr = valsplit(path)
            if not attr and not flags:
                attr = input(
                    f"Write attributes to {p} "
                    '(format "[pmin,pmax]lt:st:gt" ): '
                )
                if not attr:
                    print("No attributes provided! Aborting.")
                    return
            if attr:
                attrdict = emqxlwm2m.lwm2m.Attributes.from_string(attr)
            else:
                attrdict = flags
            pathattrs.append((Path(p), attrdict))

        for _ in range(args.count):
            # Write attributes for each endpoint
            for ep in args.endpoint:
                ep = self.cache(ep)
                for p, attr in pathattrs:
                    try:
                        resp = ep.write_attr(
                            path=p, **dict(attr), timeout=args.timeout
                        )
                        self.print_message(resp)
                    except emqxlwm2m.ResponseError as error:
                        self.print_message(error)
            if args.repeat is None:
                break
            time.sleep(args.repeat)

    def complete_write_attr(self, text, line, begidx, endidx):
        return self._complete_path(text, line, begidx, endidx)

    # -------------------------------------------------------------------------

    @cmd2.with_argparser(parser.execute)
    @endpoint_pathval
    def do_execute(self, args):

        # Use default arg if provided
        pathargs = list()
        for path in args.path:
            p, arg = valsplit(path)
            if arg is None:
                if args.arg is not None:
                    arg = args.arg
                else:
                    arg = ""
            pathargs.append((Path(p), arg))

        for _ in range(args.count):
            # Execute path for each endpoint
            for ep in args.endpoint:
                ep = self.cache(ep)
                for p, arg in pathargs:
                    try:
                        resp = ep.execute(p, arg, timeout=args.timeout)
                        self.print_message(resp)
                    except emqxlwm2m.ResponseError as error:
                        self.print_message(error)
            if args.repeat is None:
                break
            time.sleep(args.repeat)

    def complete_execute(self, text, line, begidx, endidx):
        return self._complete_path(text, line, begidx, endidx)

    # -------------------------------------------------------------------------

    @cmd2.with_argparser(parser.create)
    @endpoint_pathval
    def do_create(self, args):
        # Make sure each path has a value
        pathvals = list()
        for path in args.path:
            p, value = valsplit(path)
            if value is None:
                if args.value is not None:
                    value = args.value
                else:
                    value = input(f"Write value to {p}: ")
                if not value:
                    print("No value provided! Aborting.")
                    return
            value = emqxlwm2m.engines.emqx.str_to_py_value(value)
            pathvals.append((Path(p), value))
        pathvals.sort()

        for _ in range(args.count):
            # Make create for each endpoint
            for ep in args.endpoint:
                ep = self.cache(ep)

                def group(pval):
                    return pval[0].oid  # base_path

                groups = itertools.groupby(pathvals, key=group)
                for _, chunk in groups:
                    try:
                        resp = ep.create("", dict(chunk), timeout=args.timeout)
                        self.print_message(resp)
                    except emqxlwm2m.ResponseError as error:
                        self.print_message(error)
            if args.repeat is None:
                break
            time.sleep(args.repeat)

    def complete_create(self, text, line, begidx, endidx):
        return self._complete_path(text, line, begidx, endidx)

    # -------------------------------------------------------------------------

    @cmd2.with_argparser(parser.delete)
    @endpoint_pathval
    def do_delete(self, args):
        for _ in range(args.count):
            for ep in args.endpoint:
                ep = self.cache(ep)
                for path in args.path:
                    path, _ = valsplit(path)
                    try:
                        resp = ep.delete(path, timeout=args.timeout)
                        self.print_message(resp)
                    except emqxlwm2m.ResponseError as error:
                        self.print_message(error)
            if args.repeat is None:
                break
            time.sleep(args.repeat)

    def complete_delete(self, text, line, begidx, endidx):
        return self._complete_path(text, line, begidx, endidx)

    # -------------------------------------------------------------------------

    @cmd2.with_argparser(parser.observe)
    @endpoint_pathval
    def do_observe(self, args):
        for _ in range(args.count):
            q = None
            for ep in args.endpoint:
                ep = self.cache(ep)
                for path in args.path:
                    path, _ = valsplit(path)
                    try:
                        resp = ep.observe(
                            path,
                            timeout=args.timeout,
                            queue=q,
                        )
                        q = resp.notifications
                        self.print_message(resp)
                    except emqxlwm2m.ResponseError as error:
                        self.print_message(error)
            if args.follow:
                self.print_notifications(q, args.stop_after)
            if args.repeat is None:
                break
            time.sleep(args.repeat)

    def complete_observe(self, text, line, begidx, endidx):
        return self._complete_path(text, line, begidx, endidx)

    # -------------------------------------------------------------------------

    @cmd2.with_argparser(parser.cancel_observe)
    @endpoint_pathval
    def do_cancel_observe(self, args):
        for _ in range(args.count):
            for ep in args.endpoint:
                ep = self.cache(ep)
                for path in args.path:
                    path, _ = valsplit(path)
                    try:
                        resp = ep.cancel_observe(path, timeout=args.timeout)
                        self.print_message(resp)
                    except emqxlwm2m.ResponseError as error:
                        self.print_message(error)
            if args.repeat is None:
                break
            time.sleep(args.repeat)

    def complete_cancel_observe(self, text, line, begidx, endidx):
        return self._complete_path(text, line, begidx, endidx)

    # =========================================================================
    # Listen for LwM2M messages
    # =========================================================================

    @cmd2.with_argparser(parser.wiretap)
    @endpoint
    def do_wiretap(self, args):
        q = None
        for ep in args.endpoint:
            ep = self.cache(ep)
            q = ep.wiretap(queue=q)
        for _ in range(args.stop_after):
            self.print_message(q.get())

    @cmd2.with_argparser(parser.uplink)
    @endpoint
    def do_uplink(self, args):
        q = None
        for ep in args.endpoint:
            ep = self.cache(ep)
            q = ep.uplink(queue=q)
        for _ in range(args.stop_after):
            self.print_message(q.get())

    @cmd2.with_argparser(parser.downlink)
    @endpoint
    def do_downlink(self, args):
        q = None
        for ep in args.endpoint:
            ep = self.cache(ep)
            q = ep.downlink(queue=q)
        for _ in range(args.stop_after):
            self.print_message(q.get())

    @cmd2.with_argparser(parser.commands)
    @endpoint
    def do_commands(self, args):
        q = None
        for ep in args.endpoint:
            ep = self.cache(ep)
            q = ep.commands(queue=q)
        for _ in range(args.stop_after):
            self.print_message(q.get())

    @cmd2.with_argparser(parser.requests)
    @endpoint
    def do_requests(self, args):
        q = None
        for ep in args.endpoint:
            ep = self.cache(ep)
            q = ep.requests(queue=q)
        for _ in range(args.stop_after):
            self.print_message(q.get())

    @cmd2.with_argparser(parser.responses)
    @endpoint
    def do_responses(self, args):
        q = None
        for ep in args.endpoint:
            ep = self.cache(ep)
            q = ep.responses(queue=q)
        for _ in range(args.stop_after):
            self.print_message(q.get())

    @cmd2.with_argparser(parser.events)
    @endpoint
    def do_events(self, args):
        q = None
        for ep in args.endpoint:
            ep = self.cache(ep)
            q = ep.events(queue=q)
        for _ in range(args.stop_after):
            self.print_message(q.get())

    @cmd2.with_argparser(parser.updates)
    @endpoint
    def do_updates(self, args):
        q = None
        for ep in args.endpoint:
            ep = self.cache(ep)
            q = ep.updates(queue=q)
        for _ in range(args.stop_after):
            self.print_message(q.get())

    @cmd2.with_argparser(parser.registrations)
    @endpoint
    def do_registrations(self, args):
        q = None
        for ep in args.endpoint:
            ep = self.cache(ep)
            q = ep.registrations(queue=q)
        for _ in range(args.stop_after):
            self.print_message(q.get())

    @cmd2.with_argparser(parser.notifications)
    @endpoint
    def do_notifications(self, args):
        q = None
        for ep in args.endpoint:
            ep = self.cache(ep)
            q = ep.notifications(queue=q)
        self.print_notifications(q, args.stop_after)

    # =========================================================================
    # High level features
    # =========================================================================

    @cmd2.with_argparser(parser.reboot)
    @endpoint
    def do_reboot(self, args):
        for _ in range(args.count):
            for ep in args.endpoint:
                ep = self.cache(ep)
                t0 = dt.datetime.now()
                if args.wait:
                    q = ep.registrations()
                self.poutput(f"{ep.endpoint}: Rebooting")
                try:
                    resp = ep.execute("3/0/4", timeout=args.timeout)
                    self.print_message(resp)
                except emqxlwm2m.ResponseError as error:
                    self.print_message(error)
                else:
                    if args.wait:
                        self.poutput(
                            f"{ep.endpoint}: Waiting for registration"
                        )
                        reg = q.get()
                        self.print_message(reg)
                        t1 = reg.timestamp
                        self.poutput(
                            f"{ep.endpoint}: Reboot duration {t1 - t0}",
                        )
                if len(args.endpoint):
                    time.sleep(args.pause)
            if args.repeat is None:
                break
            time.sleep(args.repeat)

    # -------------------------------------------------------------------------

    @cmd2.with_argparser(parser.update)
    @endpoint
    def do_update(self, args):
        for ep in args.endpoint:
            ep = self.cache(ep)
            upd = emqxlwm2m.utils.trigger_update(ep, args.timeout)
            self.poutput(upd)

    # -------------------------------------------------------------------------

    @cmd2.with_argparser(parser.discoverall)
    @endpoint
    def do_discoverall(self, args):
        for ep in args.endpoint:
            ep = self.cache(ep)
            upd = emqxlwm2m.utils.trigger_update(ep, args.timeout)
            attrs = dict()
            for path in sorted(upd):
                try:
                    resp = ep.discover(path)
                except emqxlwm2m.ResponseError:
                    pass
                else:
                    data = resp.data
                    if not args.all:
                        data = {k: v for k, v in data.items() if v}
                    attrs.update(data)
            self.poutput(attrs)

    # -------------------------------------------------------------------------

    @cmd2.with_argparser(parser.firmware_update)
    @endpoint
    def do_firmware_update(self, args):
        for ep in args.endpoint:
            ep = self.cache(ep)
            for _ in range(args.retry + 1):
                try:
                    if emqxlwm2m.utils.firmware_update(
                        ep, args.package_uri, reg_timeout=1_000
                    ):
                        if args.reboot:
                            emqxlwm2m.utils.reboot(ep, True, args.timeout)
                        break
                except emqxlwm2m.ResponseError as error:
                    self.print_message(error)
                except emqxlwm2m.utils.FirmwareUpdateError as error:
                    ep.log.error("%s: %s", type(error).__name__, error)
