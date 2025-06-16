def update_folder_downloaded_by(admin_id):
    conn = sqlite3.connect(r"C:\admin-page-eyeknow\admin.db")
    cursor = conn.cursor()

    try:
        cursor.execute('''
            UPDATE Folder
            SET downloaded_by = ?
            WHERE folder_id = 1
        ''', (admin_id,))
        conn.commit()
        print("✅ Folder download record updated.")
    except sqlite3.Error as e:
        print("❌ Error updating downloaded_by:", e)
    finally:
        conn.close()