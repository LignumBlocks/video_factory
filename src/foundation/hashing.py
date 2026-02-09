import hashlib
import os

def hash_file_sha256(filepath: str) -> str:
    """
    Generates SHA256 hash of a file for reproducibility.
    Reads in chunks to handle large files.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Cannot hash missing file: {filepath}")

    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while True:
            data = f.read(65536) # 64k chunks
            if not data:
                break
            sha256.update(data)
            
    return sha256.hexdigest()
