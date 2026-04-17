import argparse
import shutil
import sys
from pathlib import Path


class PromoteError(Exception):
    pass


_KINDS = ("new-skills", "composition-recipes")


def promote(proposed_path, skills_dir, name):
    proposed_path = Path(proposed_path)
    skills_dir = Path(skills_dir)

    source = None
    for kind in _KINDS:
        candidate = proposed_path / kind / name
        if candidate.is_dir():
            source = candidate
            break
    if source is None:
        raise PromoteError(f"proposed skill {name!r} not found under {proposed_path}")

    target = skills_dir / name
    if target.exists():
        raise PromoteError(f"target {target} already exists")

    shutil.move(str(source), str(target))
    return target


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="autoskill-promote",
        description="Move a proposed skill from _proposed/<ts>/ into scientific-skills/",
    )
    parser.add_argument("--proposed", required=True,
                        help="path to the _proposed/<ts>/ directory")
    parser.add_argument("--skills-dir", required=True,
                        help="path to scientific-skills/")
    parser.add_argument("--name", required=True, help="skill name to promote")
    args = parser.parse_args(argv)

    try:
        target = promote(args.proposed, args.skills_dir, args.name)
    except PromoteError as e:
        print(f"promote failed: {e}", file=sys.stderr)
        return 1

    print(f"promoted: {args.name} -> {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
