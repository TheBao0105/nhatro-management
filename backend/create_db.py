import pyodbc

def init_db():
    conn_str = 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=.\\SQLEXPRESS;DATABASE=master;Trusted_Connection=yes;'
    conn = pyodbc.connect(conn_str, autocommit=True)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sys.databases WHERE name = 'nhatro_db'")
    if not cursor.fetchone():
        cursor.execute("CREATE DATABASE nhatro_db")
        print("Created database nhatro_db successfully!")
    else:
        print("Database nhatro_db already exists.")
    conn.close()

if __name__ == '__main__':
    init_db()

