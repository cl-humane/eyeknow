from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify
import sqlite3
import bcrypt
import os
from datetime import datetime
from werkzeug.utils import secure_filename
import uuid

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Use a secure random key in production

# File upload configuration
UPLOAD_FOLDER = 'uploads'  # Change this to your desired upload directory
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'svg'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    conn = sqlite3.connect('admin.db')  # Using the same database as auth system
    conn.row_factory = sqlite3.Row
    return conn

def get_file_size(file):
    """Get file size in bytes"""
    file.seek(0, 2)  # Seek to end
    size = file.tell()
    file.seek(0)  # Reset to beginning
    return size

@app.route('/', methods=['GET', 'POST'])
def login():
    if 'username' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('admin.db')
        cursor = conn.cursor()
        cursor.execute("SELECT admin_id, password_hash FROM Admin WHERE username = ?", (username,))
        result = cursor.fetchone()
        conn.close()

        if result and bcrypt.checkpw(password.encode('utf-8'), result[1]):
            session['username'] = username
            session['admin_id'] = result[0]  # Store admin_id in session
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid username or password")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('admin.db')
    cursor = conn.cursor()
    cursor.execute("SELECT folder_name, last_updated, date_created FROM Folder WHERE folder_id = 1")
    folder = cursor.fetchone()
    
    # Get objects/batches for display
    cursor.execute('''
        SELECT 
            o.object_id,
            o.object_name,
            o.date_created,
            o.date_updated,
            o.created_by,
            o.size,
            COUNT(f.file_id) as file_count
        FROM Object o
        LEFT JOIN File f ON o.object_id = f.object_id
        GROUP BY o.object_id
        ORDER BY o.date_created DESC
        LIMIT 10
    ''')
    objects = cursor.fetchall()
    conn.close()

    if folder:
        folder_name, last_updated, date_created = folder

        # Convert to datetime object then format to MM/DD/YYYY hh:mm AM/PM
        if last_updated:
            last_updated = datetime.strptime(last_updated, "%Y-%m-%d %H:%M:%S").strftime("%m/%d/%Y %I:%M %p")
        else:
            last_updated = "N/A"

        if date_created:
            date_created = datetime.strptime(date_created, "%Y-%m-%d %H:%M:%S").strftime("%m/%d/%Y %I:%M %p")
        else:
            date_created = "N/A"

    else:
        folder_name = "Not Set"
        last_updated = "N/A"
        date_created = "N/A"

    return render_template('dashboard.html',
                           folder_name=folder_name,
                           last_updated=last_updated,
                           date_created=date_created,
                           objects=objects)

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    
    try:
        # Get form data
        object_name = request.form.get('batchName')
        created_by = session.get('admin_id', 1)  # Use logged-in admin's ID
        
        if not object_name:
            return jsonify({'success': False, 'error': 'Object name is required'}), 400
        
        # Get uploaded files
        files = request.files.getlist('files')
        
        if not files or len(files) == 0:
            return jsonify({'success': False, 'error': 'No files uploaded'}), 400
        
        # Validate files
        valid_files = []
        total_size = 0
        
        for file in files:
            if file and file.filename != '':
                if not allowed_file(file.filename):
                    return jsonify({
                        'success': False, 
                        'error': f'File type not allowed: {file.filename}'
                    }), 400
                
                file_size = get_file_size(file)
                if file_size > MAX_FILE_SIZE:
                    return jsonify({
                        'success': False, 
                        'error': f'File too large: {file.filename}'
                    }), 400
                
                total_size += file_size
                valid_files.append((file, file_size))
        
        if not valid_files:
            return jsonify({'success': False, 'error': 'No valid files found'}), 400
        
        # Database operations
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Start transaction
            conn.execute('BEGIN')
            
            # Insert into Object table
            current_time = datetime.now().isoformat()
            cursor.execute('''
                INSERT INTO Object (object_name, date_created, date_updated, created_by, size)
                VALUES (?, ?, ?, ?, ?)
            ''', (object_name, current_time, current_time, created_by, total_size))
            
            object_id = cursor.lastrowid
            
            # Process and save each file
            saved_files = []
            for file, file_size in valid_files:
                # Generate unique filename to avoid conflicts
                original_filename = secure_filename(file.filename)
                file_extension = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
                unique_filename = f"{uuid.uuid4().hex}.{file_extension}" if file_extension else str(uuid.uuid4().hex)
                
                # Create object-specific directory
                object_dir = os.path.join(UPLOAD_FOLDER, f"object_{object_id}")
                os.makedirs(object_dir, exist_ok=True)
                
                # Save file
                file_path = os.path.join(object_dir, unique_filename)
                file.save(file_path)
                
                # Insert into File table
                cursor.execute('''
                    INSERT INTO File (object_id, file_name, date_created, created_by, size)
                    VALUES (?, ?, ?, ?, ?)
                ''', (object_id, original_filename, current_time, created_by, file_size))
                
                saved_files.append({
                    'file_id': cursor.lastrowid,
                    'original_name': original_filename,
                    'saved_as': unique_filename,
                    'size': file_size
                })
            
            # Update folder last_updated timestamp
            cursor.execute('''
                UPDATE Folder SET last_updated = ? WHERE folder_id = 1
            ''', (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))
            
            # Commit transaction
            conn.commit()
            
            return jsonify({
                'success': True,
                'object_id': object_id,
                'object_name': object_name,
                'total_size': total_size,
                'files': saved_files
            })
            
        except Exception as e:
            # Rollback on error
            conn.rollback()
            
            # Clean up any saved files on database error
            object_dir = os.path.join(UPLOAD_FOLDER, f"object_{object_id}")
            if os.path.exists(object_dir):
                import shutil
                shutil.rmtree(object_dir, ignore_errors=True)
            
            raise e
            
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Upload failed: {str(e)}'
        }), 500

@app.route('/objects', methods=['GET'])
def get_objects():
    """Get all objects with their file counts"""
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                o.object_id,
                o.object_name,
                o.date_created,
                o.date_updated,
                o.created_by,
                o.size,
                COUNT(f.file_id) as file_count
            FROM Object o
            LEFT JOIN File f ON o.object_id = f.object_id
            GROUP BY o.object_id
            ORDER BY o.date_created DESC
        ''')
        
        objects = []
        for row in cursor.fetchall():
            objects.append({
                'object_id': row['object_id'],
                'object_name': row['object_name'],
                'date_created': row['date_created'],
                'date_updated': row['date_updated'],
                'created_by': row['created_by'],
                'size': row['size'],
                'file_count': row['file_count']
            })
        
        conn.close()
        return jsonify({'success': True, 'objects': objects})
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to fetch objects: {str(e)}'
        }), 500

@app.route('/object/<int:object_id>/files', methods=['GET'])
def get_object_files(object_id):
    """Get all files for a specific object"""
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT file_id, file_name, date_created, created_by, size
            FROM File
            WHERE object_id = ?
            ORDER BY date_created DESC
        ''', (object_id,))
        
        files = []
        for row in cursor.fetchall():
            files.append({
                'file_id': row['file_id'],
                'file_name': row['file_name'],
                'date_created': row['date_created'],
                'created_by': row['created_by'],
                'size': row['size']
            })
        
        conn.close()
        return jsonify({'success': True, 'files': files})
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to fetch files: {str(e)}'
        }), 500

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('admin_id', None)
    return redirect(url_for('login'))

# Prevent back/forward browser caching
@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

if __name__ == '__main__':
    app.run(debug=True)