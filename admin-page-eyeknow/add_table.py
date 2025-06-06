import sqlite3

conn = sqlite3.connect('admin.db')
cursor = conn.cursor()

# Create Admin table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS Admin (
        admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        first_name TEXT NOT NULL,
        middle_name TEXT,
        last_name TEXT NOT NULL
    )
''')

# Create Object table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS Object (
        object_id INTEGER PRIMARY KEY AUTOINCREMENT,
        object_name TEXT NOT NULL,
        file_name TEXT NOT NULL,
        created_by INTEGER,
        created_at DATETIME,
        updated_at DATETIME,
        FOREIGN KEY (created_by) REFERENCES Admin(admin_id)
    )
''')

# Create Download_Log table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS Download_Log (
        download_id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_name TEXT NOT NULL,
        admin_id INTEGER,
        download_at DATETIME,
        FOREIGN KEY (admin_id) REFERENCES Admin(admin_id)
    )
''')

conn.commit()
conn.close()

print("✅ Tables created successfully.")
