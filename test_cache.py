import sys
import os
import sqlite3
sys.path.append(os.getcwd())

from src.cache.cache_manager import CacheManager
from src.database_manager import DatabaseManager

def test_cache():
    # 1. Test Key Determinism
    payload_a = {"prompt": "foo", "seed": 123}
    payload_b = {"prompt": "foo", "seed": 123}
    payload_c = {"prompt": "bar", "seed": 123}
    
    key_a = CacheManager.compute_key(payload_a)
    key_b = CacheManager.compute_key(payload_b)
    key_c = CacheManager.compute_key(payload_c)
    
    print(f"Key A: {key_a}")
    print(f"Key B: {key_b}")
    
    assert key_a == key_b, "Hash should be deterministic"
    assert key_a != key_c, "Different inputs should produce different hashes"
    print("✅ CacheManager Determinism Passed")
    
    # 2. Test DB Schema
    db = DatabaseManager('pipeline.db')
    db._init_db() # Run migration
    
    conn = sqlite3.connect('pipeline.db')
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(assets)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if "cache_key" in columns:
        print("✅ DB Schema Migration Passed (cache_key exists)")
    else:
        print("❌ DB Schema Migration Failed")
        
    conn.close()

if __name__ == "__main__":
    test_cache()
