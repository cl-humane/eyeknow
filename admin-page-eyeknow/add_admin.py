import sqlite3
import bcrypt

def add_admin(username, password, first_name, middle_name, last_name):
    password_bytes = password.encode('utf-8')
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    
    conn = sqlite3.connect(r"C:\admin-page-eyeknow\admin.db")
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO Admin (username, password_hash, first_name, middle_name, last_name)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, hashed, first_name, middle_name, last_name))
        
        conn.commit()
        print("Admin added successfully!")
    except sqlite3.IntegrityError as e:
        print("Error adding admin:", e)
    finally:
        conn.close()

#change this for new admin
if __name__ == '__main__':
    add_admin('humane', 'humane12', 'Ciana Humane', 'Mangadlao', 'Lejarde')