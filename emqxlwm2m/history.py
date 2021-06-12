"""Command, endpoint and path history"""

# Built-in
import collections
import functools
import os
import pathlib
import tempfile

# PyPI
import iterfzf
import rich
import rich.console
import rich.table
import rich.box

_tmp_dir = pathlib.Path(tempfile.gettempdir())
HISTORY_ENDPOINTS = str(_tmp_dir / "emqxlwm2m.history.endpoints")
HISTORY_PATHS = str(_tmp_dir / "emqxlwm2m.history.paths")
HISTORY_CMD = os.path.expanduser("~/.emqxlwm2m_history")

# ENDPOINT HISTORY AND SELECTION
# ==============================


def endpoints_from_file(endpoints: str):
    """Load endpoints from file if possible

    Filenames must contain a ".".
    """
    output = list()
    for ep in endpoints:
        if "." in ep and os.path.isfile(os.path.expanduser(ep)):
            with open(ep, encoding="utf-8") as f:
                for line in f:
                    if line.startswith("#"):
                        continue
                    line = line.strip()
                    if line:
                        output.append(line)
        else:
            output.append(ep)
    return output


def load_lines(filename):
    if filename is None:
        return
    try:
        with open(filename, encoding="utf-8") as file:
            lines = file.readlines()
    except FileNotFoundError:
        return
    for line in lines:
        line = line.strip()
        if line and not line.startswith("#"):
            yield line


def with_history(history_file, history=10):
    def decorator(func):
        @functools.wraps(func)
        def loader(*args, **kwargs):
            # Process history
            lines = list(load_lines(history_file))
            if lines:
                lines = lines[-history:]
                keys = [l.split()[0] for l in lines]
                index = {l: i for i, l in enumerate(keys)}
                usage = collections.Counter(keys)
                usage[keys[-1]] = history

                def sorter(line):
                    key = line.split()[0]
                    return (usage[key], index.get(key, 0))

            else:

                def sorter(line):
                    return line

            history_lines = lines
            lines = list(func(*args, **kwargs))
            keys = {l.split()[0] for l in lines}
            for line in history_lines:
                if line.split()[0] not in keys and line not in lines:
                    lines.append(line)
            lines.sort(key=sorter)
            return lines

        return loader

    return decorator


@with_history(HISTORY_ENDPOINTS, history=100)
def get_endpoints(filename):
    yield from load_lines(filename)


def add_endpoint_to_history(line):
    with open(HISTORY_ENDPOINTS, "a") as file:
        file.write(f"{line}\n")


def select_endpoint(console, filename):
    candidates = list(get_endpoints(filename))
    selections = iterfzf.iterfzf(reversed(candidates), exact=True, multi=True)
    if selections is None:
        return None
    if isinstance(selections, str):
        selections = [selections]
    return [ep.split()[0] for ep in selections]


def input_endpoint():
    p = input("Input endpoint: ").strip()
    if not p:
        return list()
    return p.split()


# LWM2M PATH HISTORY AND SELECTION
# ================================


@with_history(HISTORY_PATHS, history=100)
def get_paths(console, xml2obj, operations=""):
    """Parse XMLs of LwM2M obj. def. and return paths for selection"""
    ops = set()
    if operations.startswith("exec"):
        ops.add("E")
    elif operations in {"read", "observe", "cancel-observe"}:
        ops.add("R")
        ops.add("RW")
    elif operations == "write":
        ops.add("W")
        ops.add("RW")

    table = rich.table.Table(
        box=rich.box.SIMPLE, show_header=False, show_edge=False, pad_edge=False
    )
    table.add_column("Path", min_width=12, no_wrap=True)
    table.add_column(
        "Name", style="red", min_width=10, max_width=20, no_wrap=True
    )
    table.add_column("Mandatory", min_width=3)
    table.add_column("Multiple", min_width=3)
    table.add_column("Type", min_width=3)
    table.add_column("Operations", min_width=2)
    table.add_column("Description", style="blue", no_wrap=True)

    for obj in xml2obj.values():
        row = list()
        row.append(f"/{obj.oid}")
        row.append(obj.name)
        row.append(obj.mandatory_str[:3])
        row.append(obj.multiple_str[:3])
        row.append("")
        row.append("")
        obj_desc = obj.description.replace("\n", ", ")
        obj_desc = obj_desc[:80]
        row.append(obj_desc)
        table.add_row(*row, style="bold")  # Add object
        row[0] = row[0] + "/0"
        table.add_row(*row, style="bold")  # Add object instance

        # Add object instance resources
        for res in obj.resources:
            if ops and res.operations not in ops:
                continue
            row = list()
            row.append(f"/{obj.oid}/0/{res.rid}")
            row.append(res.name)
            row.append(res.mandatory_str[:3])
            row.append(res.multiple_str[:3])
            row.append(res.type[:3].title())
            row.append(res.operations)
            res_desc = res.description.replace("\n", ", ")
            res_desc = res_desc[:80]
            row.append(res_desc)
            table.add_row(*row)

    with console.capture() as capture:
        console.print(table)
    return capture.get().splitlines()


def add_path_to_history(line):
    if not line.startswith("/"):
        line = "/" + line
    with open(HISTORY_PATHS, "a") as file:
        file.write(f"{line}\n")


def select_path(console, xml2obj, operations="", filter_=None):
    """Select path with fzf."""
    candidates = list(get_paths(console, xml2obj, operations))
    if filter_ is not None:
        candidates = [c for c in candidates if filter_(c)]
    # Monkey patch to get terminal colors
    from subprocess import Popen

    def monkey(cmd, **kwargs):
        return Popen(cmd + ["--ansi"], **kwargs)

    iterfzf.subprocess.Popen = monkey
    selections = iterfzf.iterfzf(reversed(candidates), exact=True, multi=True)
    iterfzf.subprocess.Popen = Popen
    if selections is None:
        return list()
    if isinstance(selections, str):
        selections = [selections]
    return [s.split()[0].strip("/") for s in selections]


def input_path():
    p = input("Input path(s): ").strip()
    if not p:
        return list()
    return p.split()
