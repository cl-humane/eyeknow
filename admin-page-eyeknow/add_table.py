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

# Create Folder table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS Folder (
        folder_id INTEGER PRIMARY KEY CHECK (folder_id = 1),
        folder_name TEXT NOT NULL,
        last_updated DATETIME,
        date_created DATETIME,
        downloaded_by INTEGER,
        FOREIGN KEY (downloaded_by) REFERENCES Admin(admin_id)
    )
''')

# Create Object table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS Object (
        object_id INTEGER PRIMARY KEY AUTOINCREMENT,
        object_name TEXT NOT NULL UNIQUE,
        date_created DATETIME,
        date_updated DATETIME,
        created_by INTEGER,
        size REAL,
        FOREIGN KEY (created_by) REFERENCES Admin(admin_id)
    )
''')

# Create Images table
cursor.execute('''
    CREATE TABLE IF NOT EXISTS File (
        file_id INTEGER PRIMARY KEY AUTOINCREMENT,
        object_id INTEGER,
        file_name TEXT NOT NULL,
        date_created DATETIME,
        created_by INTEGER,
        size REAL,
        FOREIGN KEY (object_id) REFERENCES Object(object_id),
        FOREIGN KEY (created_by) REFERENCES Admin(admin_id)
    )
''')    

conn.commit()
conn.close()

print("✅ Tables created successfully.")