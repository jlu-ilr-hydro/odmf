
import os
import subprocess as sp
import re


def rgrep(pattern: str, path:str, binary=False)->dict:
    """
    A wrapper for the system call grep -r (or rgrep) for full text search in files

    Returns a path / match dictionary. If binary=True, stderr is scanned for matches in binary files
    """
    proc = sp.run(['grep', '-rn', pattern, path], capture_output=True)
    matches = proc.stdout.decode().split('\n')
    matches = {
        path: match
        for path, match in
            (line.split(':', 1)
             for line in matches if ':' in line)
    }
    if binary:
        for err in proc.stderr.decode().split('\n'):
            try:
                _, path, msg = err.split(':', 2)
            except ValueError:
                continue
            if os.path.exists(path):
                matches[path] = msg
    return matches


def rglob(pattern: str, path:str) -> dict:
    """
    Searches for filenames that matches the pattern
    """
    result = {}
    for root, dirnames, filenames in os.walk(path):
        for fn in dirnames + filenames:
            path = os.path.join(root, fn)
            if re.search(pattern, fn):
                result[path] = 'Name matches'
    return result
