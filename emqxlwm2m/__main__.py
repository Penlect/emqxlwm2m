"""CLI entry point of emqxlwm2m.

Run `python3 -m emqxlwm2m --help` to get the command line interface
help.
"""

# Built-in
import logging
import sys

# PyPI
import rich.logging

# Package
import emqxlwm2m.cmd2loop
import emqxlwm2m.engines.emqx
import emqxlwm2m.history
import emqxlwm2m.loadobjects
import emqxlwm2m.parsers as parser

FMT_STDOUT = "%(asctime)s %(name)s %(levelname)s %(message)s"


def backcomp(arglist):
    """Modify arglist for backwards compatibility"""
    for i in range(len(arglist)):
        if arglist[i] == "attr":
            arglist[i] = "write-attr"
        elif arglist[i] == "--known-endpoints":
            arglist[i] = "--ep-known"
    try:
        arglist.remove("--echo")
    except ValueError:
        pass
    return arglist


def main(arglist):
    """CLI main function"""

    # Parse main command line arguments
    arglist = backcomp(arglist)
    args, unknown_args = parser.main.parse_known_args(args=arglist)
    if args.command is None:
        parser.main.print_help()
        return
    args.command = args.command.replace("-", "_")

    # Parse the command specific arguments
    try:
        p = getattr(parser, args.command)
    except AttributeError:
        sys.exit(f"Unknown command: {args.command!r}")
    else:
        p.parse_args(unknown_args, args)

    # Setup logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format=FMT_STDOUT,
        datefmt="[%X]",
        handlers=[rich.logging.RichHandler(rich_tracebacks=True)],
    )

    # Create Engine instance and CommandInterpreter
    eng = emqxlwm2m.engines.emqx.EMQxEngine.via_mqtt(
        host=args.host, port=args.port, max_subs=100, timeout=args.timeout
    )
    eng.host = args.host
    eng.port = args.port
    xml2obj = emqxlwm2m.loadobjects.load_objects(
        args.xml_path, load_builtin=True
    )
    intrpr = emqxlwm2m.cmd2loop.CommandInterpreter(
        eng,
        timeout=args.timeout,
        data_model=xml2obj,
        ep_active=args.ep_active if args.command == "cmd" else None,
        ep_known=args.ep_known,
        ep_prefix=args.ep_prefix,
        allow_cli_args=False,
        persistent_history_file=emqxlwm2m.history.HISTORY_CMD,
        startup_script=args.startup_script,
    )

    # Run interactive mode or singe shot command
    if args.command == "cmd":
        intrpr.cmdloop()
        return
    intrpr.preloop()
    try:
        intrpr.runcmds_plus_hooks(
            [args.command + " " + " ".join(unknown_args)]
        )
    finally:
        intrpr.postloop()


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except (KeyboardInterrupt, BrokenPipeError):
        print("Bye")
    except Exception as error:
        sys.exit(f"{type(error).__name__}: {error}")
