#!/usr/bin/env python3
"""
Database Migration: Add missing columns to shots table
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "pipeline.db")

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if columns exist
    cursor.execute("PRAGMA table_info(shots)")
    columns = [row[1] for row in cursor.fetchall()]
    
    print(f"Current columns in shots table: {columns}")
    
    # Add missing columns
    if 'alignment_source' not in columns:
        print("Adding alignment_source column...")
        cursor.execute("ALTER TABLE shots ADD COLUMN alignment_source TEXT")
        
    if 'alignment_confidence' not in columns:
        print("Adding alignment_confidence column...")
        cursor.execute("ALTER TABLE shots ADD COLUMN alignment_confidence REAL")
    
    conn.commit()
    conn.close()
    print("Migration complete!")

if __name__ == "__main__":
    migrate()
