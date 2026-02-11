import hashlib
import os

def hash_file_sha256(filepath: str = None, data: bytes = None) -> str:
    """
    Generates SHA256 hash of a file OR raw bytes for reproducibility.
    Reads in chunks to handle large files.
    """
    sha256 = hashlib.sha256()

    if data is not None:
        sha256.update(data)
    elif filepath:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Cannot hash missing file: {filepath}")
        with open(filepath, 'rb') as f:
            while True:
                data_chunk = f.read(65536) # 64k chunks
                if not data_chunk:
                    break
                sha256.update(data_chunk)
    else:
        raise ValueError("Either filepath or data must be provided")
            
    return sha256.hexdigest()
