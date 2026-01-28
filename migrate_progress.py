#!/usr/bin/env python3
"""
Migration script to add progress tracking columns to run_status table
"""
import sqlite3

DB_PATH = "pipeline.db"

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Add progress columns if they don't exist
    try:
        cursor.execute("ALTER TABLE run_status ADD COLUMN progress_current INTEGER DEFAULT 0")
        print("✓ Added progress_current column")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("⚠ progress_current column already exists")
        else:
            raise
    
    try:
        cursor.execute("ALTER TABLE run_status ADD COLUMN progress_total INTEGER DEFAULT 0")
        print("✓ Added progress_total column")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("⚠ progress_total column already exists")
        else:
            raise
    
    try:
        cursor.execute("ALTER TABLE run_status ADD COLUMN progress_message TEXT")
        print("✓ Added progress_message column")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("⚠ progress_message column already exists")
        else:
            raise
    
    conn.commit()
    conn.close()
    print("\n✅ Migration complete!")

if __name__ == "__main__":
    migrate()
