import re
from pathlib import Path
import os
import sys

def are_paths_similar(path1, path2, min_matching_segments=3):
    """
    Compares paths based on directory segments, normalizing slashes first.
    """
    # 1. Normalize slashes: Convert all \ to / 
    # This prevents 'dir\file' being treated as a single segment on non-Windows systems
    path1_norm = path1.replace('\\', '/')
    path2_norm = path2.replace('\\', '/')

    # 2. Convert to Path objects and get the parts
    parts1 = Path(path1_norm).parts
    parts2 = Path(path2_norm).parts

    # 3. Reverse them to compare from the filename upwards
    parts1_rev = parts1[::-1]
    parts2_rev = parts2[::-1]

    match_count = 0
    for p1, p2 in zip(parts1_rev, parts2_rev):
        if p1 == p2:
            match_count += 1
        else:
            break

    return match_count >= min_matching_segments


def is_valid_file_hash(s: str) -> bool:
    """
    Return True if s looks like a valid cryptographic file hash
    (md5, sha1, sha224, sha256, sha384, sha512).
    """
    if not isinstance(s, str):
        return False

    s = s.strip().lower()

    # Valid hex characters only
    if not re.fullmatch(r"[0-9a-f]+", s):
        return False

    # Valid lengths (in hex chars)
    valid_lengths = {
        32,   # MD5
        40,   # SHA-1
        56,   # SHA-224
        64,   # SHA-256
        96,   # SHA-384
        128,  # SHA-512
    }

    return len(s) in valid_lengths


def is_valid_file_path(path: str) -> bool:
    """
    Return True if path is a syntactically valid POSIX file path.
    No filesystem checks are performed.
    """
    if not isinstance(path, str):
        return False

    path = path.strip()
    if not path:
        return False

    # POSIX paths cannot contain null bytes
    if "\x00" in path:
        return False

    # Reject control characters
    if re.search(r"[\x00-\x1f\x7f]", path):
        return False

    # Normalize redundant slashes
    normalized = re.sub(r"/+", "/", path)

    # Reject standalone dot paths
    if normalized in {".", ".."}:
        return False

    # Each path component must be non-empty and not null
    parts = normalized.split("/")
    if any(part == "" for part in parts if normalized != "/"):
        return False

    return True


def check_writable(path):
    # 1. Get the absolute path and find the parent directory
    abs_path = os.path.abspath(path)
    parent_dir = os.path.dirname(abs_path)

    # 2. Check if the parent directory exists
    if not os.path.exists(parent_dir):
        print(f"Error: The directory '{parent_dir}' does not exist.")
        sys.exit(1)

    # 3. Check if the parent directory is writable
    if not os.access(parent_dir, os.W_OK):
        print(f"Error: You do not have permission to write to '{parent_dir}'.")
        sys.exit(1)

    return abs_path


class Tee:
    def __init__(self, file_path, mode='w'):
        self.file = open(file_path, mode)
        self.stdout = sys.stdout

    def write(self, data, no_stdout=False):
        if no_stdout:
            self.file.write(data)    # Write to file
        else:
            self.stdout.write(data)  # Write to console
            self.file.write(data)    # Write to file

    def flush(self):
        self.file.flush()
        self.stdout.flush()

    def close(self):
        self.file.close()


class TerminalOnly:
    """A mock Tee class that only writes to the console."""
    def __init__(self):
        self.stdout = sys.stdout

    def write(self, data, no_stdout=False):
        if not no_stdout:
            self.stdout.write(data)

    def flush(self):
        self.stdout.flush()

    def close(self):
        pass
