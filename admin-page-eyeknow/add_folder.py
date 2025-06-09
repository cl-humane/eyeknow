import sqlite3
from datetime import datetime

def create_folder(folder_name):
    conn = sqlite3.connect(r"C:\admin-page-eyeknow\admin.db")
    cursor = conn.cursor()

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    try:
        # Check if folder_id = 1 already exists
        cursor.execute("SELECT folder_id FROM Folder WHERE folder_id = 1")
        existing = cursor.fetchone()

        if existing:
            # Update folder name and timestamp, do NOT touch downloaded_by
            cursor.execute('''
                UPDATE Folder
                SET folder_name = ?, last_updated = ?
                WHERE folder_id = 1
            ''', (folder_name, now))
            print("✅ Folder updated (name or timestamp).")
        else:
            # Insert folder with NULL downloaded_by
            cursor.execute('''
                INSERT INTO Folder (folder_id, folder_name, last_updated, date_created, downloaded_by)
                VALUES (1, ?, ?, ?, NULL)
            ''', (folder_name, now, now))
            print("✅ Folder created successfully.")

        conn.commit()
    except sqlite3.Error as e:
        print("❌ Database error:", e)
    finally:
        conn.close()

if __name__ == '__main__':
    create_folder("EyeKnow_Database")