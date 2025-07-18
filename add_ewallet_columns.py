#!/usr/bin/env python3
"""
Add ewallet columns to the database
"""

import sqlite3
import os

def add_ewallet_columns():
    """Add ewallet_number_1 and ewallet_number_2 columns to the user table"""
    
    # Database path
    db_path = 'instance/al-7esa.db'
    
    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        return False
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(user)")
        columns = [column[1] for column in cursor.fetchall()]
        
        print(f"📋 Current user table columns: {columns}")
        
        # Add ewallet_number_1 if it doesn't exist
        if 'ewallet_number_1' not in columns:
            print("➕ Adding ewallet_number_1 column...")
            cursor.execute("ALTER TABLE user ADD COLUMN ewallet_number_1 VARCHAR(50)")
            print("✅ ewallet_number_1 column added successfully")
        else:
            print("ℹ️  ewallet_number_1 column already exists")
        
        # Add ewallet_number_2 if it doesn't exist
        if 'ewallet_number_2' not in columns:
            print("➕ Adding ewallet_number_2 column...")
            cursor.execute("ALTER TABLE user ADD COLUMN ewallet_number_2 VARCHAR(50)")
            print("✅ ewallet_number_2 column added successfully")
        else:
            print("ℹ️  ewallet_number_2 column already exists")
        
        # Commit changes
        conn.commit()
        
        # Verify columns were added
        cursor.execute("PRAGMA table_info(user)")
        new_columns = [column[1] for column in cursor.fetchall()]
        print(f"📋 Updated user table columns: {new_columns}")
        
        # Close connection
        conn.close()
        
        print("\n🎉 Database migration completed successfully!")
        print("✨ Teachers can now add ewallet numbers in their profile")
        print("✨ Paid classroom creation will require ewallet numbers")
        
        return True
        
    except Exception as e:
        print(f"❌ Error adding ewallet columns: {e}")
        return False

if __name__ == "__main__":
    add_ewallet_columns()
