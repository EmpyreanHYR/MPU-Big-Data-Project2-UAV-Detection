#!/usr/bin/env python3
"""Check public repository documents and tests without private local fixtures."""
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]


def main():
    for script in ('check_repository.py', 'check_references.py'):
        subprocess.run([sys.executable, str(ROOT / 'scripts' / script)],
                       cwd=ROOT, check=True)
    paths = subprocess.check_output(
        ['git', 'ls-files', '-z', '--', 'tests/test_*.py'], cwd=ROOT
    ).decode().split('\0')
    suite = unittest.TestSuite()
    for name in sorted(set(paths)):
        path = ROOT / name
        if name and path.is_file():
            suite.addTests(unittest.defaultTestLoader.discover(
                str(ROOT / 'tests'), pattern=path.name))
    if suite.countTestCases() == 0:
        raise RuntimeError('No Git-tracked public tests found')
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())
