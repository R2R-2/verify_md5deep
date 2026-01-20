import re
from pathlib import Path

from pathlib import Path

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

