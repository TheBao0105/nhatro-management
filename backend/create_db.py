import pyodbc
import os
from dotenv import load_dotenv

load_dotenv()

DATABASES_TO_CREATE = [
    'nhatro_identity_db',
    'nhatro_property_db',
    'nhatro_tenant_db',
    'nhatro_contract_db',
    'nhatro_billing_db',
]

def init_databases():
    server = os.getenv('DB_SERVER', r'.\SQLEXPRESS')
    driver = os.getenv('DB_DRIVER', 'ODBC Driver 17 for SQL Server')
    trusted = os.getenv('DB_TRUSTED_CONNECTION', 'yes').lower() == 'yes'
    user = os.getenv('DB_USER', '')
    password = os.getenv('DB_PASSWORD', '')

    conn_str = f"DRIVER={{{driver}}};SERVER={server};DATABASE=master;"
    if trusted:
        conn_str += "Trusted_Connection=yes;TrustServerCertificate=yes;"
    else:
        conn_str += f"UID={user};PWD={password};TrustServerCertificate=yes;"

    try:
        conn = pyodbc.connect(conn_str, autocommit=True)
        cursor = conn.cursor()
        print(" Connected to SQL Server master database.")

        for db_name in DATABASES_TO_CREATE:
            cursor.execute(f"SELECT name FROM sys.databases WHERE name = '{db_name}'")
            if not cursor.fetchone():
                cursor.execute(f"CREATE DATABASE [{db_name}]")
                print(f" [+] Created SOA database: {db_name}")
            else:
                print(f" [ok] Database {db_name} already exists.")

        conn.close()
        print(" All SOA databases are ready.")
    except Exception as e:
        print(f"❌ Error connecting to SQL Server: {e}")
        print("💡 Note: If SQL Server is not running, the system will use SQLite multi-database fallback.")

if __name__ == '__main__':
    init_databases()
