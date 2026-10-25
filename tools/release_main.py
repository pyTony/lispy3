"""Update main from dev, leaving the developer-only files out of main.

    python tools/release_main.py            # make a release branch, don't push
    python tools/release_main.py --push     # also push it, then open a PR into main

Run it from a checkout of dev: the script itself is not on main. It leaves
you on the release branch.

dev holds the whole project. main is the release tree for people who use
Lispy without developing it: the same files minus DEV_ONLY below. This
script fetches both branches, makes release/<date> from origin/main, merges
origin/dev into it without committing, removes every DEV_ONLY path (that
also settles the expected "deleted in main, modified in dev" conflicts) and
commits. Any other conflict stops the script with a list of the files: fix
them, `git add` them and run `git commit` yourself.

Never merge main into dev: that would delete the developer files from dev.
A fix made directly on main goes to dev with `git cherry-pick`.
"""
import argparse
import datetime
import os
import re
import subprocess
import sys

# Paths on dev that main leaves out. Add a path here when you add a
# developer-only file or folder on dev.
DEV_ONLY = [
    ".github",
    "AGENTS.md",
    "CLAUDE.md",
    "TODO.md",
    "pytest.ini",
    "tests",
    "basic/reference",
    "docs/AGENT_COORDINATION.md",
    "docs/LLM.md",
    "docs/MBASIC_COMPAT.md",
    "docs/REPOSITORY_LAYOUT.md",
    "tools/release_main.py",
    "tools/run_complex_checks.py",
]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def git(*args, check=True):
    result = subprocess.run(["git", *args], cwd=ROOT, text=True,
                            capture_output=True)
    if check and result.returncode != 0:
        sys.exit(f"git {' '.join(args)} failed:\n{result.stdout}{result.stderr}")
    return result


def is_dev_only(path):
    path = path.replace("\\", "/")
    return any(path == p or path.startswith(p + "/") for p in DEV_ONLY)


def dead_links():
    """Markdown links in the release tree that point at a DEV_ONLY path."""
    found = []
    for name in git("ls-files", "*.md").stdout.splitlines():
        with open(os.path.join(ROOT, name), encoding="utf-8") as f:
            text = f.read()
        for target in re.findall(r"\]\(([^)#\s]+)", text):
            if "://" in target:
                continue
            path = os.path.normpath(os.path.join(os.path.dirname(name), target))
            if is_dev_only(os.path.relpath(path)):
                found.append(f"{name}: {target}")
    return found


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--branch", default="release/" + datetime.date.today().isoformat())
    parser.add_argument("--push", action="store_true", help="push the release branch")
    args = parser.parse_args(argv)
    main_ref, dev_ref = f"{args.remote}/main", f"{args.remote}/dev"

    if git("status", "--porcelain", "--untracked-files=no").stdout.strip():
        sys.exit("Commit or stash your changes first.")
    git("fetch", args.remote, "main", "dev")
    if git("rev-list", "--count", f"{main_ref}..{dev_ref}").stdout.strip() == "0":
        print("main already has everything from dev.")
        return 0

    git("checkout", "-B", args.branch, main_ref)
    git("merge", "--no-ff", "--no-commit", dev_ref, check=False)
    git("rm", "-r", "-q", "--force", "--ignore-unmatch", "--", *DEV_ONLY)

    conflicts = git("diff", "--name-only", "--diff-filter=U").stdout.splitlines()
    if conflicts:
        print("Merged, but these files conflict:")
        print("\n".join("  " + c for c in conflicts))
        print("Fix them, `git add` them and run `git commit`.")
        return 1

    git("commit", "-m", f"Release dev to main ({args.branch})")
    for link in dead_links():
        print("Warning: link to a dev-only file:", link)
    print(f"Release branch {args.branch} is ready.")
    if args.push:
        git("push", "-u", args.remote, args.branch)
        print(f"Open a PR from {args.branch} into main.")
    else:
        print(f"Check it, then: git push -u {args.remote} {args.branch}"
              " and open a PR into main.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
