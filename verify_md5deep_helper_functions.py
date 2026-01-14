import re
from pathlib import Path

def are_paths_similar(path1, path2, min_matching_segments=3):
    """
    Compares paths based on directory segments rather than characters.

    Parameters:
    - path1, path2: The file paths to compare.
    - min_matching_segments: The minimum number of trailing segments
      (including filename) that must match.
    """
    # Convert to Path objects and get the parts (folders + filename)
    parts1 = Path(path1).parts
    parts2 = Path(path2).parts

    # Reverse them to compare from the filename upwards
    parts1_rev = parts1[::-1]
    parts2_rev = parts2[::-1]

    match_count = 0
    for p1, p2 in zip(parts1_rev, parts2_rev):
        if p1 == p2:
            match_count += 1
        else:
            break

    # Return True if the number of matching trailing folders
    # meets your threshold
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


def is_valid_file_path_syntax(path: str) -> bool:
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

