"""Filename completion for quoted Lisp loader and BASIC LOAD/SAVE arguments."""
import os
import re
from pathlib import Path


def filename_completion(text, *, basic=False, cwd=None):
    pattern = (r'^\s*(?:LOAD|SAVE)\s+"([^"\n]*)$' if basic else
               r'\((?:load|save|slurp|bbc-load)\s+"((?:\\.|[^"\\\n])*)$')
    match = re.search(pattern, text, re.IGNORECASE if basic else 0)
    if match is None:
        return None
    raw = match[1]
    prefix = raw if basic else raw.replace('\\\\', '\\')
    prefix = prefix.replace('\\', '/') if os.name == 'nt' else prefix
    _, _, stem = prefix.rpartition('/')
    folder = prefix[:-len(stem)] if stem else prefix
    directory = Path(os.path.expanduser(folder or '.'))
    if not directory.is_absolute(): directory = Path(cwd or os.getcwd()) / directory
    try:
        entries = sorted(directory.iterdir(), key=lambda p: p.name)
    except OSError:
        return match.start(1), []
    results = []
    for entry in entries:
        if not entry.name.startswith(stem) or (not stem and entry.name.startswith('.')):
            continue
        name = folder + entry.name + ('/' if entry.is_dir() else '')
        # Quoted names follow the source language's escape convention.
        name = name.replace('"', '""') if basic else name.replace('\\', '\\\\').replace('"', '\\"')
        results.append(name)
    return match.start(1), results
