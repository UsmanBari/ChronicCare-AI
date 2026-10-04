"""
MySQL Connection Health Check Script.

Connects to MySQL database configured via environment variables and reports
connection status, server version, and database name.
Prints ONLY the server version and database name.
NEVER prints or logs database credentials, hostnames, passwords, or connection URLs.
"""

import os
import sys
from dotenv import load_dotenv

# Ensure backend root is on sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_root = os.path.abspath(os.path.join(script_dir, ".."))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

# Load environment variables from backend-poc-technical/.env
env_file = os.path.join(backend_root, ".env")
if os.path.exists(env_file):
    load_dotenv(env_file)

import pymysql
from data_sources.db_config import get_mysql_connection_params


def check_connection() -> bool:
    try:
        params = get_mysql_connection_params()
        
        conn = pymysql.connect(
            host=params["host"],
            port=params["port"],
            user=params["user"],
            password=params["password"],
            database=params["database"],
            charset=params["charset"],
            ssl=params.get("ssl"),
            connect_timeout=10,
        )
        
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT VERSION(), DATABASE();")
                version, db_name = cursor.fetchone()
                print("[SUCCESS] MySQL Connected successfully!")
                print(f"  - Server Version: {version}")
                print(f"  - Database Name: {db_name}")
            return True
        finally:
            conn.close()
            
    except Exception as e:
        print(f"[ERROR] MySQL connection failed: {type(e).__name__}")
        return False


if __name__ == "__main__":
    success = check_connection()
    sys.exit(0 if success else 1)
