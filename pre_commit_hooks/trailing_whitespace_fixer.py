from __future__ import annotations

import argparse
import os
import re
import subprocess
from collections.abc import Sequence


def get_changed_lines(filename: str) -> set[int]:
    """Возвращает номера изменённых строк в файле согласно git diff."""
    changed_lines = set()
    try:
        result = subprocess.run(
            ['git', 'diff', '--cached', '-U0', '--', filename],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            encoding='utf-8'
        )
    except subprocess.CalledProcessError:
        return changed_lines

    hunk_re = re.compile(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@')
    for line in result.stdout.splitlines():
        match = hunk_re.match(line)
        if match:
            start = int(match.group(1))
            count = int(match.group(2) or 1)
            changed_lines.update(range(start, start + count))
    return changed_lines


def _fix_file(
    filename: str,
    is_markdown: bool,
    chars: bytes | None,
    changed_only: bool,
) -> bool:
    if changed_only:
        changed_lines = get_changed_lines(filename)
        if not changed_lines:
            return False
    else:
        changed_lines = None  # означает "все строки"

    with open(filename, 'rb') as f:
        lines = f.readlines()

    new_lines = []
    changed = False
    for i, line in enumerate(lines, start=1):
        if changed_lines is None or i in changed_lines:
            new_line = _process_line(line, is_markdown, chars)
            if new_line != line:
                changed = True
            new_lines.append(new_line)
        else:
            new_lines.append(line)

    if changed:
        with open(filename, 'wb') as f:
            f.writelines(new_lines)
        return True
    return False


def _process_line(line: bytes, is_markdown: bool, chars: bytes | None) -> bytes:
    if line.endswith(b'\r\n'):
        eol = b'\r\n'
        line = line[:-2]
    elif line.endswith(b'\n'):
        eol = b'\n'
        line = line[:-1]
    else:
        eol = b''

    if is_markdown and not line.isspace() and line.endswith(b'  '):
        return line[:-2].rstrip(chars) + b'  ' + eol
    return line.rstrip(chars) + eol


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-markdown-linebreak-ext', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--markdown-linebreak-ext', action='append', default=[], metavar='*|EXT[,EXT,...]')
    parser.add_argument('--chars', help='Characters to strip from line ends')
    parser.add_argument('--only-changed-lines', action='store_true', help='Fix only changed lines (from git diff)')
    parser.add_argument('filenames', nargs='*')
    args = parser.parse_args(argv)

    if args.no_markdown_linebreak_ext:
        print('--no-markdown-linebreak-ext now does nothing!')

    all_md = '*' in args.markdown_linebreak_ext
    md_exts = ['.' + x.lower().lstrip('.') for x in ','.join(args.markdown_linebreak_ext).split(',') if x]

    chars = None if args.chars is None else args.chars.encode()
    return_code = 0
    for filename in args.filenames:
        _, ext = os.path.splitext(filename.lower())
        is_md = all_md or ext in md_exts
        if _fix_file(filename, is_md, chars, args.only_changed_lines):
            print(f'Fixing {filename}')
            return_code = 1
    return return_code


if __name__ == '__main__':
    raise SystemExit(main())
