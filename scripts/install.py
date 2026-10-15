#!/usr/bin/env python3
"""Install the standalone skill as a symlink; never replace an existing skill."""
import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills-dir", type=Path, default=Path.home() / ".claude/skills")
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1] / "skills/claude-codex-canvas"
    target = args.skills_dir.expanduser().absolute() / source.name
    if target.is_symlink() and target.resolve() == source:
        print(f"Already installed: {target}")
        return
    if target.exists() or target.is_symlink():
        parser.exit(1, f"Refusing to replace {target}. Remove or relocate it yourself first.\n")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.symlink_to(source, target_is_directory=True)
    print(f"Installed {target} -> {source}\nStart a new Claude Code local session to load it.")


if __name__ == "__main__":
    main()
