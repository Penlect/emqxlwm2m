"""Argument parsers used by CLI"""

# Built-in
import os
import argparse

PKG = __package__.upper()

# =========================================================================
# Parent parsers
# =========================================================================

_endpoint = argparse.ArgumentParser(add_help=False)
_endpoint.add_argument(
    dest="endpoint", type=str, nargs="*", help="LwM2M endpoint client name"
)

_path = argparse.ArgumentParser(add_help=False)
_path.add_argument(
    dest="path",
    type=str,
    nargs="*",
    help="LwM2M object/instance/resource path",
)

_value = argparse.ArgumentParser(add_help=False)
_value.add_argument(
    "--value", "-v", type=str, help="Value to use in context of command."
)

_timeout = argparse.ArgumentParser(add_help=False)
_timeout.add_argument(
    "-T",
    dest="timeout",
    type=float,
    metavar="SEC",
    help="Timeout when waiting for response in seconds.",
)

_repeat = argparse.ArgumentParser(add_help=False)
_repeat.add_argument(
    "--repeat",
    type=float,
    metavar="SEC",
    help="Repeat action with delay in seconds.",
)
_repeat.add_argument(
    "--count",
    type=int,
    metavar="N",
    default=10 ** 10,
    help="Repeat action at most %(metavar)s times.",
)

_stop = argparse.ArgumentParser(add_help=False)
_stop.add_argument(
    "--stop-after",
    "-s",
    type=int,
    metavar="M",
    default=10 ** 10,
    help="Stop after %(metavar)s messages have been received.",
)

_wait = argparse.ArgumentParser(add_help=False)
_wait.add_argument(
    "--wait", "-w", action="store_true", help="Wait for action to complete."
)

# =========================================================================
# Interactive mode
# =========================================================================

cmd = argparse.ArgumentParser(
    prog="cmd", description="Start interactive interpreter."
)

# =========================================================================
# Basic LwM2M operations
# =========================================================================

discover = argparse.ArgumentParser(
    prog="discover",
    parents=[_endpoint, _path, _timeout, _repeat],
    description=(
        "Discover which objects/resources are instantiated and their "
        "attached attributes."
    ),
)

read = argparse.ArgumentParser(
    prog="read",
    parents=[_endpoint, _path, _timeout, _repeat],
    description=(
        "Read the value of a resource, an object instance or all the object"
        "instances of an object."
    ),
)

write = argparse.ArgumentParser(
    prog="write",
    parents=[_endpoint, _timeout, _repeat],
    description=(
        "Change the value of a resource, the values of an array of "
        "resources instances or the values of multiple resources from "
        "an object instance."
    ),
)
write.add_argument(
    metavar="path=value",
    dest="path",
    type=str,
    nargs="*",
    help="LwM2M resource path and new value",
)
write.add_argument(
    "--value",
    "-v",
    type=str,
    help='Value to use if not specified with path "path=value".',
)
write.add_argument("--batch", action="store_true", help="Make a batch write.")

write_attr = argparse.ArgumentParser(
    prog="write-attr",
    parents=[_endpoint, _timeout, _value, _repeat],
    description=(
        "Set some or all attributes {pmin, pmax, lt, st, gt} to "
        "objects, instances or resources."
    ),
)
write_attr.add_argument(
    metavar="path=[pmin,pmax]lt:st:gt",
    dest="path",
    type=str,
    nargs="*",
    help="LwM2M object instance or resource path and new attributes.",
)
write_attr.add_argument("--pmin", type=int, metavar="SEC", help="Seconds")
write_attr.add_argument("--pmax", type=int, metavar="SEC", help="Seconds")
write_attr.add_argument("--lt", type=float, help="Float")
write_attr.add_argument("--st", type=float, help="Float")
write_attr.add_argument("--gt", type=float, help="Float")

execute = argparse.ArgumentParser(
    prog="execute", parents=[_endpoint, _value, _timeout, _repeat]
)
execute.add_argument(
    metavar="path=arg",
    dest="path",
    type=str,
    nargs="*",
    help="LwM2M resource path and optional argument",
)
execute.add_argument("--arg", type=str, help="Execute arguments")

create = argparse.ArgumentParser(
    prog="create", parents=[_endpoint, _value, _timeout, _repeat]
)
create.add_argument(
    metavar="path=value",
    dest="path",
    type=str,
    nargs="*",
    help="LwM2M resource path and new value",
)

delete = argparse.ArgumentParser(
    prog="delete", parents=[_endpoint, _path, _timeout, _repeat]
)

observe = argparse.ArgumentParser(
    prog="observe",
    parents=[_endpoint, _path, _timeout, _stop, _repeat],
    description=(
        "Request notifications for changes of a specific resource, "
        "Resources within an object instance or for all the object "
        "instances of an object."
    ),
)
observe.add_argument(
    "--follow",
    "-f",
    action="store_true",
    help="Follow and print notifications.",
)

cancel_observe = argparse.ArgumentParser(
    prog="cancel-observe",
    parents=[_endpoint, _path, _timeout, _repeat],
    description=(
        "End observation relationship for object instance or resource"
    ),
)

# =========================================================================
# Listen for LwM2M messages
# =========================================================================

wiretap = argparse.ArgumentParser(prog="wiretap", parents=[_endpoint, _stop])
uplink = argparse.ArgumentParser(prog="uplink", parents=[_endpoint, _stop])
downlink = argparse.ArgumentParser(prog="downlink", parents=[_endpoint, _stop])
requests = argparse.ArgumentParser(prog="requests", parents=[_endpoint, _stop])
responses = argparse.ArgumentParser(
    prog="responses", parents=[_endpoint, _stop]
)
events = argparse.ArgumentParser(prog="events", parents=[_endpoint, _stop])
registrations = argparse.ArgumentParser(
    prog="registrations", parents=[_endpoint, _stop]
)
updates = argparse.ArgumentParser(prog="updates", parents=[_endpoint, _stop])
notifications = argparse.ArgumentParser(
    prog="notifications", parents=[_endpoint, _stop]
)
# notifications.add_argument(
#     '--changes', '-c',
#     action='store_true',
#     help='Print changes "new value (old value)".')
# notifications.add_argument(
#     '--changes-only',
#     action='store_true',
#     help='Print only changed resources.')

commands = argparse.ArgumentParser(prog="commands", parents=[_endpoint, _stop])

# =========================================================================
# High level features
# =========================================================================

discoverall = argparse.ArgumentParser(
    prog="discoverall", parents=[_endpoint, _timeout]
)
discoverall.add_argument(
    "--all", action="store_true", help="Include resources with no attributes."
)
reboot = argparse.ArgumentParser(
    prog="reboot",
    parents=[_endpoint, _timeout, _wait, _repeat],
    description="Execute the Reboot resource 3/0/4",
)
reboot.add_argument(
    "--pause",
    type=float,
    default=0,
    metavar="SEC",
    help="Extra delay between reboots of multiple endpoints.",
)
update = argparse.ArgumentParser(prog="update", parents=[_endpoint, _timeout])
firmware_update = argparse.ArgumentParser(
    prog="firmware-update",
    parents=[_endpoint, _timeout],
    description="Perform firmware update. Requires Object ID 5.",
)
firmware_update.add_argument("--package-uri", "-u", help="Package URI")
firmware_update.add_argument(
    "--retry",
    type=int,
    default=0,
    metavar="N",
    help="Retry at most %(metavar)s times if failure. Default %(default)s.",
)
firmware_update.add_argument(
    "--reboot",
    action="store_true",
    help="Reboot device after successful firmware update.",
)

# =========================================================================
# Main settings
# =========================================================================

# Build a list of all valid commands
valid_commands = list()
for key, value in globals().copy().items():
    if key.startswith("_"):
        continue
    if not isinstance(value, argparse.ArgumentParser):
        continue
    valid_commands.append(key)

main = argparse.ArgumentParser(prog="python3 -m emqxlwm2m", add_help=False)
main.add_argument(
    "command",
    type=str,
    nargs="?",
    help=(
        f'Select command: {", ".join(valid_commands)}. '
        "Use with --help to see command arguments."
    ),
)
main.add_argument(
    "--host",
    default=os.environ.get(f"{PKG}_HOST", "localhost"),
    help="EMQx MQTT broker host (default: %(default)s)",
)
main.add_argument(
    "--port",
    "-p",
    type=int,
    default=os.environ.get(f"{PKG}_PORT", 1883),
    help="EMQx MQTT port (default: %(default)s)",
)
main.add_argument(
    "-l",
    "--log-level",
    choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    default="INFO",
    help="Logging level (default: %(default)s)",
)
main.add_argument(
    "--timeout",
    "-t",
    type=float,
    metavar="SEC",
    default=60,
    help="Timeout when waiting for response in seconds (default: %(default)s)",
)
main.add_argument(
    "--xml-path",
    "-x",
    metavar="DIR",
    action="append",
    help="Directory containing LwM2M object definition XML-files. "
    "Can be used multiple times to provide multiple paths. "
    "Used when selecting a path interactively.",
)
main.add_argument(
    "--ep-active",
    type=str,
    default=os.environ.get(f"{PKG}_EP_ACTIVE", ""),
    help='Default endpoint in interactive mode (subcommand "cmd")',
)
main.add_argument(
    "--ep-known",
    type=str,
    default="endpoints.txt",
    help=(
        "Path to a text file listing known endpoints. Used for interactive "
        "selection when endpoint is not specified in command."
    ),
)
main.add_argument(
    "--ep-prefix",
    type=str,
    default=os.environ.get(f"{PKG}_EP_PREFIX", ""),
    help="Ensure endpoints starts with prefix.",
)
main.add_argument(
    "--startup-script",
    type=str,
    metavar="PATH",
    help="Execute initialization commands from a script.",
)
