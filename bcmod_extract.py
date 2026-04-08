#!/usr/bin/env python3
"""
bcmod_extract.py — Extracts files from a BC Mod Package (.BCMod) file.

The .BCMod format was created by "BC - Mod Packager BETA v4.4" (circa 2004).
It is a custom binary format with:
  - A plain-text header block (lines starting with '#')
  - A plain-text table of contents (one Windows-style path per line)
  - A ';' separator line
  - Binary file contents separated by '\\r\\n===Next File===\\r\\n'

Protected files (Foundation.py etc.) are skipped to avoid overwriting
BC Remastered's versions with old 2004 originals.
"""

import sys
import os

# Files managed by BC Remastered that must not be overwritten by old BCMod versions.
PROTECTED = {
    os.path.join('scripts', 'Foundation.py'),
    os.path.join('scripts', 'FoundationMenu.py'),
    os.path.join('scripts', 'FoundationTriggers.py'),
    os.path.join('scripts', 'LoadTacticalSounds.py'),
}


def extract(bcmod_path, output_dir):
    with open(bcmod_path, 'rb') as f:
        data = f.read()

    lines = data.split(b'\r\n')

    # Parse file list from TOC (lines after 5-line header block, until ';')
    files = []
    for line in lines[6:]:
        if line == b';':
            break
        path = line.decode('latin-1').replace('\\', os.sep).lstrip(os.sep)
        files.append(path)

    print(f"Files in TOC: {len(files)}")

    # Locate start of binary section (immediately after ';\r\n')
    toc_end = data.index(b';\r\n') + 3

    # Files are separated by this delimiter in the binary section
    SEPARATOR = b'\r\n===Next File===\r\n'
    chunks = data[toc_end:].split(SEPARATOR)

    if len(chunks) != len(files):
        print(f"WARNING: TOC has {len(files)} entries but found {len(chunks)} chunks — last chunk may be trailing data.")

    extracted = 0
    skipped = 0
    for path, chunk in zip(files, chunks):
        if path in PROTECTED:
            print(f"  Skipping protected: {path}")
            skipped += 1
            continue
        dest = os.path.join(output_dir, path)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, 'wb') as f:
            f.write(chunk)
        extracted += 1

    print(f"Extracted {extracted} files to: {output_dir} ({skipped} protected files skipped)")


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <file.BCMod> <output_dir>")
        sys.exit(1)
    extract(sys.argv[1], sys.argv[2])
