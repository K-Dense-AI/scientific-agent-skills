"""Unified CLI for the autoskill skill.

Subcommands:
  run      — detect workflows and draft proposed skills
  doctor   — verify screenpipe + LM Studio + config + skills dir
  promote  — move an approved proposal into scientific-skills/
"""

import argparse
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(prog="autoskill", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["run", "doctor", "promote"],
                        help="subcommand to run")
    parser.add_argument("rest", nargs=argparse.REMAINDER,
                        help="arguments forwarded to the subcommand")
    args = parser.parse_args(argv)

    if args.command == "run":
        import run as _run
        return _run.main(args.rest)
    if args.command == "doctor":
        import doctor as _doctor
        return _doctor.main(args.rest)
    if args.command == "promote":
        import promote as _promote
        return _promote.main(args.rest)
    raise AssertionError(f"unreachable: {args.command!r}")


if __name__ == "__main__":
    sys.exit(main())
