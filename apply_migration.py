#!/usr/bin/env python3
"""
Apply database migration for profile images and password field changes
"""

import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def apply_migration():
    """Apply database migration"""
    try:
        # Database connection
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            database=os.getenv('DB_NAME', 'sayan_db'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD', '')
        )
        
        if connection.is_connected():
            cursor = connection.cursor()
            print("✅ Connected to MySQL database")
            
            # Migration SQL commands
            migration_commands = [
                # Update students table
                "ALTER TABLE students CHANGE COLUMN password hashed_password VARCHAR(255) NOT NULL;",
                "ALTER TABLE students CHANGE COLUMN avatar profile_image VARCHAR(255) NULL;",
                
                # Update academy_users table
                "ALTER TABLE academy_users CHANGE COLUMN password hashed_password VARCHAR(255) NOT NULL;",
                "ALTER TABLE academy_users ADD COLUMN profile_image VARCHAR(255) NULL AFTER hashed_password;",
                
                # Update admins table
                "ALTER TABLE admins CHANGE COLUMN password hashed_password VARCHAR(255) NOT NULL;",
                "ALTER TABLE admins ADD COLUMN profile_image VARCHAR(255) NULL AFTER hashed_password;",
            ]
            
            print("🔄 Applying migration...")
            
            for command in migration_commands:
                try:
                    cursor.execute(command)
                    print(f"✅ Executed: {command[:50]}...")
                except Error as e:
                    if "Duplicate column name" in str(e) or "Unknown column" in str(e):
                        print(f"⚠️  Skipped (already exists): {command[:50]}...")
                    else:
                        print(f"❌ Error: {command[:50]}... - {e}")
            
            connection.commit()
            print("✅ Migration completed successfully!")
            
            # Verify changes
            cursor.execute("DESCRIBE students;")
            students_cols = cursor.fetchall()
            print("\n📋 Students table structure:")
            for col in students_cols:
                if 'password' in col[0] or 'profile' in col[0]:
                    print(f"   {col[0]} - {col[1]}")
            
            cursor.execute("DESCRIBE academy_users;")
            academy_cols = cursor.fetchall()
            print("\n📋 Academy_users table structure:")
            for col in academy_cols:
                if 'password' in col[0] or 'profile' in col[0]:
                    print(f"   {col[0]} - {col[1]}")
                    
    except Error as e:
        print(f"❌ Database error: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
            print("🔌 Database connection closed")

if __name__ == "__main__":
    print("🚀 Starting database migration...")
    apply_migration()
    print("🎯 Migration process completed!") 