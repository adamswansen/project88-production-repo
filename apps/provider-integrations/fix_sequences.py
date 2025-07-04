#!/usr/bin/env python3
"""
Fix PostgreSQL sequences for RunSignUp tables
"""

import sys
import os
import psycopg2
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_connection():
    """Get database connection using environment variables"""
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        database=os.getenv('DB_NAME', 'project88_myappdb'),
        user=os.getenv('DB_USER', 'project88_admin'),
        password=os.getenv('DB_PASSWORD', 'securepassword123')
    )

def fix_sequence(table_name, id_column='id'):
    """Fix sequence for a given table"""
    logger.info(f"🔧 Fixing sequence for {table_name}...")
    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Get the maximum existing ID
        cursor.execute(f"SELECT MAX({id_column}) FROM {table_name};")
        max_id = cursor.fetchone()[0] or 0
        logger.info(f"📊 Max existing {id_column} in {table_name}: {max_id}")
        
        # Get the sequence name
        cursor.execute(f"SELECT pg_get_serial_sequence('{table_name}', '{id_column}');")
        sequence_name = cursor.fetchone()[0]
        
        if not sequence_name:
            logger.warning(f"⚠️  No sequence found for {table_name}.{id_column}")
            conn.close()
            return False
        
        logger.info(f"📋 Sequence name: {sequence_name}")
        
        # Get current sequence value
        cursor.execute(f"SELECT last_value FROM {sequence_name};")
        current_val = cursor.fetchone()[0]
        logger.info(f"📈 Current sequence value: {current_val}")
        
        # Fix sequence if needed
        if current_val <= max_id:
            new_val = max_id + 1
            logger.warning(f"🚨 PROBLEM: Sequence ({current_val}) <= Max ID ({max_id})")
            logger.info(f"🔧 Setting sequence to {new_val}...")
            
            cursor.execute(f"SELECT setval('{sequence_name}', %s);", (new_val,))
            
            # Verify the fix
            cursor.execute(f"SELECT last_value FROM {sequence_name};")
            updated_val = cursor.fetchone()[0]
            logger.info(f"✅ Sequence updated to: {updated_val}")
        else:
            logger.info(f"✅ Sequence OK: {current_val} > {max_id}")
        
        conn.commit()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to fix sequence for {table_name}: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

def main():
    """Fix sequences for all RunSignUp tables"""
    logger.info("🔧 POSTGRESQL SEQUENCE FIX")
    logger.info("=" * 40)
    
    tables_to_fix = [
        'runsignup_participants',
        'runsignup_events', 
        'runsignup_races'
    ]
    
    success_count = 0
    
    for table in tables_to_fix:
        if fix_sequence(table):
            success_count += 1
        logger.info("")  # Empty line for readability
    
    logger.info("=" * 40)
    logger.info(f"🎯 RESULTS: {success_count}/{len(tables_to_fix)} sequences fixed")
    
    if success_count == len(tables_to_fix):
        logger.info("🎉 All sequences fixed! Ready for clean backfill test.")
        return True
    else:
        logger.warning("⚠️  Some sequences could not be fixed.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 