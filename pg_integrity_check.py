#!/usr/bin/env python3
"""
PostgreSQL Database Integrity Checker

This script checks the integrity of all tables in a PostgreSQL database
and logs the operations and results.
"""

import os
import sys
import time
import logging
import datetime
import psycopg2
from psycopg2 import sql
import configparser
from tabulate import tabulate

# Configure logging
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = os.path.join(log_dir, f"pg_integrity_check_{timestamp}.log")

# Set up logging to file and console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Create a table for detailed logging
class IntegrityCheckLogger:
    def __init__(self, log_file_path):
        self.log_file_path = log_file_path.replace('.log', '.csv')
        self.headers = ["Timestamp", "Table", "Operation", "Duration (s)", "Status", "Details", "Recommendation"]
        self.rows = []
        
        # Create CSV header
        with open(self.log_file_path, 'w') as f:
            f.write(','.join(self.headers) + '\n')
    
    def log(self, table, operation, duration, status, details="", recommendation=""):
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row = [timestamp, table, operation, f"{duration:.2f}", status, details, recommendation]
        self.rows.append(row)
        
        # Append to CSV
        with open(self.log_file_path, 'a') as f:
            f.write(','.join([f'"{str(item)}"' for item in row]) + '\n')
        
        # Print to console in a nice format
        if status == "ERROR":
            logger.error(f"{table} - {operation}: {details}")
        else:
            logger.info(f"{table} - {operation}: {status}")
    
    def print_summary(self):
        print("\n" + "="*80)
        print("INTEGRITY CHECK SUMMARY")
        print("="*80)
        print(tabulate(self.rows, headers=self.headers, tablefmt="grid"))
        print(f"\nDetailed log saved to: {self.log_file_path}")
        print(f"Full log saved to: {log_file}")


def load_config():
    """Load database configuration."""
    try:
        config = {}
        # Try to load from config file
        config_parser = configparser.ConfigParser()
        if os.path.exists('config.ini'):
            config_parser.read('config.ini')
            if 'DATABASE' in config_parser:
                db_config = config_parser['DATABASE']
                config = {
                    "PG_USER": db_config.get('PG_USER', ''),
                    "PG_PASSWORD": db_config.get('PG_PASSWORD', ''),
                    "PG_HOST_LOCAL": db_config.get('PG_HOST_LOCAL', ''),
                    "PG_HOST": db_config.get('PG_HOST', ''),
                    "PG_PORT": db_config.get('PG_PORT', '5432'),
                    "PG_DBNAME": db_config.get('PG_DBNAME', '')
                }
        
        # If config is empty or missing required fields, try environment variables
        required_fields = ["PG_USER", "PG_PASSWORD", "PG_HOST_LOCAL", "PG_PORT", "PG_DBNAME"]
        if not all(field in config and config[field] for field in required_fields):
            for field in required_fields:
                if field not in config or not config[field]:
                    config[field] = os.environ.get(field, '')
        
        # Try to load from .env file
        if os.path.exists('.env'):
            with open('.env', 'r') as f:
                for line in f:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        if key in required_fields and (key not in config or not config[key]):
                            config[key] = value
        
        print(f"Configuration loaded: {config}")
        return config
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        sys.exit(1)


def get_connection(config):
    """Create a database connection."""
    try:
        print(f"Connecting to database with: user={config['PG_USER']}, host={config['PG_HOST_LOCAL']}, port={config['PG_PORT']}, dbname={config['PG_DBNAME']}")
        conn = psycopg2.connect(
            user=config["PG_USER"],
            password=config["PG_PASSWORD"],
            host=config["PG_HOST_LOCAL"],  # Using local host as specified
            port=config["PG_PORT"],
            dbname=config["PG_DBNAME"]
        )
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        print(f"Database connection error: {e}")
        sys.exit(1)


def get_all_tables(conn):
    """Get a list of all tables in the database."""
    tables = []
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT table_schema, table_name 
                FROM information_schema.tables 
                WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                AND table_type = 'BASE TABLE'
                ORDER BY table_schema, table_name
            """)
            tables = [(row[0], row[1]) for row in cursor.fetchall()]
        return tables
    except Exception as e:
        logger.error(f"Error getting table list: {e}")
        print(f"Error getting table list: {e}")
        return []


def check_table_integrity(conn, schema, table, check_logger):
    """Perform integrity checks on a specific table."""
    full_table_name = f"{schema}.{table}"
    
    # List of checks to perform
    checks = [
        {
            "name": "VACUUM ANALYZE",
            "query": sql.SQL("VACUUM ANALYZE {table}").format(
                table=sql.Identifier(schema, table)
            ),
            "description": "Updating statistics and reclaiming storage",
            "recommendation": "If this fails, try running VACUUM FULL to rebuild the table"
        },
        {
            "name": "Check Primary Key",
            "query": sql.SQL("""
                SELECT count(*) FROM (
                    SELECT a.*, count(*) OVER (PARTITION BY {pk_cols}) as cnt
                    FROM {table} a
                ) t WHERE cnt > 1
            """),
            "dynamic": True,  # This query needs to be built dynamically based on PK columns
            "description": "Checking for duplicate primary keys",
            "recommendation": "Remove duplicate records or fix the primary key constraint"
        },
        {
            "name": "Check for NULL values in NOT NULL columns",
            "query": sql.SQL("""
                SELECT column_name FROM information_schema.columns
                WHERE table_schema = %s AND table_name = %s
                AND is_nullable = 'NO' AND column_default IS NULL
            """),
            "params": [schema, table],
            "dynamic": True,
            "description": "Checking for NULL values in NOT NULL columns",
            "recommendation": "Update NULL values or modify the column constraint"
        },
        {
            "name": "Check Foreign Keys",
            "query": sql.SQL("""
                SELECT
                    tc.constraint_name,
                    kcu.column_name,
                    ccu.table_schema AS foreign_table_schema,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM
                    information_schema.table_constraints AS tc
                    JOIN information_schema.key_column_usage AS kcu
                      ON tc.constraint_name = kcu.constraint_name
                      AND tc.table_schema = kcu.table_schema
                    JOIN information_schema.constraint_column_usage AS ccu
                      ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_schema = %s
                AND tc.table_name = %s
            """),
            "params": [schema, table],
            "dynamic": True,
            "description": "Checking foreign key constraints",
            "recommendation": "Fix inconsistent foreign key references"
        },
        {
            "name": "Check Indexes",
            "query": sql.SQL("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE schemaname = %s AND tablename = %s
            """),
            "params": [schema, table],
            "dynamic": True,
            "description": "Checking table indexes",
            "recommendation": "Rebuild corrupt indexes with REINDEX"
        },
        {
            "name": "Table Size",
            "query": sql.SQL("""
                SELECT
                    pg_size_pretty(pg_total_relation_size({table})) as total_size,
                    pg_size_pretty(pg_relation_size({table})) as table_size,
                    pg_size_pretty(pg_total_relation_size({table}) - pg_relation_size({table})) as index_size
            """).format(
                table=sql.Identifier(schema, table)
            ),
            "description": "Getting table size information",
            "recommendation": "Consider partitioning large tables"
        }
    ]
    
    # Run each check
    for check in checks:
        start_time = time.time()
        try:
            with conn.cursor() as cursor:
                if check["name"] == "Check Primary Key":
                    # First get primary key columns
                    cursor.execute("""
                        SELECT a.attname
                        FROM   pg_index i
                        JOIN   pg_attribute a ON a.attrelid = i.indrelid
                                             AND a.attnum = ANY(i.indkey)
                        WHERE  i.indrelid = %s::regclass
                        AND    i.indisprimary
                    """, (f"{schema}.{table}",))
                    
                    pk_columns = cursor.fetchall()
                    if pk_columns:
                        pk_cols = sql.SQL(', ').join(sql.Identifier(col[0]) for col in pk_columns)
                        query = check["query"].format(
                            pk_cols=pk_cols,
                            table=sql.Identifier(schema, table)
                        )
                        cursor.execute(query)
                        result = cursor.fetchone()
                        
                        if result and result[0] > 0:
                            check_logger.log(
                                full_table_name, 
                                check["name"], 
                                time.time() - start_time,
                                "WARNING", 
                                f"Found {result[0]} duplicate primary key values", 
                                check["recommendation"]
                            )
                        else:
                            check_logger.log(
                                full_table_name, 
                                check["name"], 
                                time.time() - start_time,
                                "OK", 
                                "No duplicate primary keys found"
                            )
                    else:
                        check_logger.log(
                            full_table_name, 
                            check["name"], 
                            time.time() - start_time,
                            "INFO", 
                            "No primary key defined for this table"
                        )
                
                elif check["name"] == "Check for NULL values in NOT NULL columns":
                    cursor.execute(check["query"], check["params"])
                    not_null_columns = [col[0] for col in cursor.fetchall()]
                    
                    if not_null_columns:
                        for column in not_null_columns:
                            null_check_query = sql.SQL("""
                                SELECT COUNT(*) FROM {table} WHERE {column} IS NULL
                            """).format(
                                table=sql.Identifier(schema, table),
                                column=sql.Identifier(column)
                            )
                            
                            cursor.execute(null_check_query)
                            null_count = cursor.fetchone()[0]
                            
                            if null_count > 0:
                                check_logger.log(
                                    full_table_name, 
                                    f"{check['name']} ({column})", 
                                    time.time() - start_time,
                                    "ERROR", 
                                    f"Found {null_count} NULL values in NOT NULL column {column}", 
                                    check["recommendation"]
                                )
                            else:
                                check_logger.log(
                                    full_table_name, 
                                    f"{check['name']} ({column})", 
                                    time.time() - start_time,
                                    "OK", 
                                    f"No NULL values in NOT NULL column {column}"
                                )
                    else:
                        check_logger.log(
                            full_table_name, 
                            check["name"], 
                            time.time() - start_time,
                            "INFO", 
                            "No NOT NULL columns without defaults found"
                        )
                
                elif check["name"] == "Check Foreign Keys":
                    cursor.execute(check["query"], check["params"])
                    fk_constraints = cursor.fetchall()
                    
                    if fk_constraints:
                        for fk in fk_constraints:
                            constraint_name, column, f_schema, f_table, f_column = fk
                            
                            # Check for orphaned foreign keys
                            fk_check_query = sql.SQL("""
                                SELECT COUNT(*) FROM {table} t
                                LEFT JOIN {f_table} f ON t.{column} = f.{f_column}
                                WHERE t.{column} IS NOT NULL AND f.{f_column} IS NULL
                            """).format(
                                table=sql.Identifier(schema, table),
                                f_table=sql.Identifier(f_schema, f_table),
                                column=sql.Identifier(column),
                                f_column=sql.Identifier(f_column)
                            )
                            
                            cursor.execute(fk_check_query)
                            orphaned_count = cursor.fetchone()[0]
                            
                            if orphaned_count > 0:
                                check_logger.log(
                                    full_table_name, 
                                    f"{check['name']} ({constraint_name})", 
                                    time.time() - start_time,
                                    "ERROR", 
                                    f"Found {orphaned_count} orphaned foreign keys in constraint {constraint_name}", 
                                    f"Fix references to {f_schema}.{f_table}.{f_column}"
                                )
                            else:
                                check_logger.log(
                                    full_table_name, 
                                    f"{check['name']} ({constraint_name})", 
                                    time.time() - start_time,
                                    "OK", 
                                    f"Foreign key constraint {constraint_name} is valid"
                                )
                    else:
                        check_logger.log(
                            full_table_name, 
                            check["name"], 
                            time.time() - start_time,
                            "INFO", 
                            "No foreign key constraints found"
                        )
                
                elif check["name"] == "Check Indexes":
                    cursor.execute(check["query"], check["params"])
                    indexes = cursor.fetchall()
                    
                    if indexes:
                        for idx in indexes:
                            idx_name, idx_def = idx
                            
                            # Check if index is valid
                            cursor.execute("""
                                SELECT pg_index.indisvalid
                                FROM pg_index
                                JOIN pg_class ON pg_class.oid = pg_index.indexrelid
                                JOIN pg_namespace ON pg_namespace.oid = pg_class.relnamespace
                                WHERE pg_namespace.nspname = %s
                                AND pg_class.relname = %s
                            """, (schema, idx_name))
                            
                            is_valid = cursor.fetchone()
                            
                            if is_valid and not is_valid[0]:
                                check_logger.log(
                                    full_table_name, 
                                    f"{check['name']} ({idx_name})", 
                                    time.time() - start_time,
                                    "ERROR", 
                                    f"Index {idx_name} is invalid", 
                                    f"Rebuild index with: REINDEX INDEX {schema}.{idx_name}"
                                )
                            else:
                                check_logger.log(
                                    full_table_name, 
                                    f"{check['name']} ({idx_name})", 
                                    time.time() - start_time,
                                    "OK", 
                                    f"Index {idx_name} is valid"
                                )
                    else:
                        check_logger.log(
                            full_table_name, 
                            check["name"], 
                            time.time() - start_time,
                            "INFO", 
                            "No indexes found"
                        )
                
                elif "dynamic" in check and check["dynamic"]:
                    cursor.execute(check["query"], check.get("params", []))
                    result = cursor.fetchall()
                    check_logger.log(
                        full_table_name, 
                        check["name"], 
                        time.time() - start_time,
                        "INFO", 
                        f"Results: {result}"
                    )
                
                else:
                    cursor.execute(check["query"])
                    result = cursor.fetchone()
                    check_logger.log(
                        full_table_name, 
                        check["name"], 
                        time.time() - start_time,
                        "INFO", 
                        f"Results: {result}"
                    )
                    
        except Exception as e:
            conn.rollback()  # Rollback in case of error
            check_logger.log(
                full_table_name, 
                check["name"], 
                time.time() - start_time,
                "ERROR", 
                f"Error: {str(e)}", 
                check.get("recommendation", "Check database logs for details")
            )
            print(f"Error checking {full_table_name} - {check['name']}: {str(e)}")


def main():
    """Main function to check database integrity."""
    print("Starting PostgreSQL database integrity check")
    logger.info("Starting PostgreSQL database integrity check")
    
    # Load configuration
    config = load_config()
    print(f"Connecting to database {config['PG_DBNAME']} on {config['PG_HOST_LOCAL']}:{config['PG_PORT']}")
    logger.info(f"Connecting to database {config['PG_DBNAME']} on {config['PG_HOST_LOCAL']}:{config['PG_PORT']}")
    
    # Initialize detailed logger
    check_logger = IntegrityCheckLogger(log_file)
    
    try:
        # Connect to the database
        conn = get_connection(config)
        print("Successfully connected to the database")
        logger.info("Successfully connected to the database")
        
        # Get all tables
        tables = get_all_tables(conn)
        print(f"Found {len(tables)} tables to check")
        logger.info(f"Found {len(tables)} tables to check")
        
        # Check each table
        for schema, table in tables:
            full_table_name = f"{schema}.{table}"
            print(f"Checking table: {full_table_name}")
            logger.info(f"Checking table: {full_table_name}")
            check_table_integrity(conn, schema, table, check_logger)
        
        # Close connection
        conn.close()
        print("Database connection closed")
        logger.info("Database connection closed")
        
        # Print summary
        check_logger.print_summary()
        
    except Exception as e:
        logger.error(f"Error during integrity check: {e}")
        print(f"Error during integrity check: {e}")
        sys.exit(1)
    
    print(f"Integrity check completed. Log saved to {log_file}")
    logger.info(f"Integrity check completed. Log saved to {log_file}")


if __name__ == "__main__":
    main()
