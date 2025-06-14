from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify
import sqlite3
import bcrypt
import os
from datetime import datetime
from werkzeug.utils import secure_filename
import uuid

app = Flask(__name__)
app.secret_key = 'your-secret-key'

# File Upload
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'svg'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB max file size

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    conn = sqlite3.connect('admin.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_file_size(file):
    """Get file size in bytes"""
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
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
            session['admin_id'] = result[0]
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
    
    cursor.execute('''
        SELECT 
            o.object_id,
            o.object_name,
            o.date_created,
            o.date_updated,
            o.created_by,
            o.size,
            COUNT(f.file_id) as file_count,
            a.first_name,
            a.last_name
        FROM Object o
        LEFT JOIN File f ON o.object_id = f.object_id
        LEFT JOIN Admin a ON o.created_by = a.admin_id
        GROUP BY o.object_id
        ORDER BY o.date_created DESC
    ''')
    objects_data = cursor.fetchall()
    conn.close()

    objects = []
    for obj in objects_data:
        print(f"Raw date_created: {obj[2]} (type: {type(obj[2])})")
        print(f"Raw date_updated: {obj[3]} (type: {type(obj[3])})")
        
        date_created_formatted = format_date_flexible(obj[2])
        date_updated_formatted = format_date_flexible(obj[3])
 
        size_formatted = format_file_size(obj[5]) if obj[5] else "0 Bytes"

        created_by_name = "Unknown"
        if obj[7] and obj[8]:
            created_by_name = f"{obj[7]} {obj[8]}"
        elif obj[7]:
            created_by_name = obj[7]
        
        objects.append({
            'object_id': obj[0],
            'object_name': obj[1],
            'date_created': obj[2],
            'date_updated': obj[3],
            'created_by': obj[4],
            'size': obj[5],
            'file_count': obj[6],
            'date_created_formatted': date_created_formatted,
            'date_updated_formatted': date_updated_formatted,
            'size_formatted': size_formatted,
            'created_by_name': created_by_name
        })

    if folder:
        folder_name, last_updated, date_created = folder
        if last_updated:
            last_updated = format_date_flexible(last_updated)
        else:
            last_updated = "N/A"

        if date_created:
            date_created = format_date_flexible(date_created)
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

def format_date_flexible(date_input):
    """Format date with multiple fallback attempts"""
    if not date_input:
        return "N/A"
    if isinstance(date_input, str) and "/" in date_input:
        return date_input
    date_formats = [
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%m/%d/%Y %I:%M %p",
        "%m/%d/%Y"
    ]
    date_str = str(date_input)
    
    for fmt in date_formats:
        try:
            parsed_date = datetime.strptime(date_str, fmt)
            return parsed_date.strftime("%m/%d/%Y %I:%M %p")
        except ValueError:
            continue
    print(f"Warning: Could not parse date format: {date_input}")
    return str(date_input)

def format_file_size(bytes_size):
    """Format file size in bytes to human readable format"""
    if not bytes_size or bytes_size == 0:
        return '0 Bytes'
    k = 1024
    sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']
    i = 0
    size = float(bytes_size)
    while size >= k and i < len(sizes) - 1:
        size /= k
        i += 1
    return f"{size:.2f} {sizes[i]}"

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    try:
        object_name = request.form.get('batchName')
        is_merge = request.form.get('merge') == 'true'
        created_by = session.get('admin_id', 1)

        if not object_name:
            return jsonify({'success': False, 'error': 'Object name is required'}), 400
  
        files = request.files.getlist('files')
        
        if not files or len(files) == 0:
            return jsonify({'success': False, 'error': 'No files uploaded'}), 400
 
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

        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            conn.execute('BEGIN')

            cursor.execute('SELECT object_id, size FROM Object WHERE object_name = ?', (object_name,))
            existing_object = cursor.fetchone()
            
            if existing_object and not is_merge:
                conn.close()
                return jsonify({
                    'success': False, 
                    'conflict': True,
                    'error': f'Object "{object_name}" already exists'
                }), 409
            
            if existing_object and is_merge:
                object_id = existing_object['object_id']
                current_size = existing_object['size'] or 0
                new_total_size = current_size + total_size
                current_time = datetime.now().isoformat()
                cursor.execute('''
                    UPDATE Object 
                    SET size = ?, date_updated = ?
                    WHERE object_id = ?
                ''', (new_total_size, current_time, object_id))
                
            else:
                current_time = datetime.now().isoformat()
                cursor.execute('''
                    INSERT INTO Object (object_name, date_created, date_updated, created_by, size)
                    VALUES (?, ?, ?, ?, ?)
                ''', (object_name, current_time, current_time, created_by, total_size))
                
                object_id = cursor.lastrowid
            
            saved_files = []
            for file, file_size in valid_files:

                original_filename = secure_filename(file.filename)
                file_extension = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
                unique_filename = f"{uuid.uuid4().hex}.{file_extension}" if file_extension else str(uuid.uuid4().hex)

                object_dir = os.path.join(UPLOAD_FOLDER, f"object_{object_id}")
                os.makedirs(object_dir, exist_ok=True)

                file_path = os.path.join(object_dir, unique_filename)
                file.save(file_path)
                
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

            cursor.execute('''
                UPDATE Folder SET last_updated = ? WHERE folder_id = 1
            ''', (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))
            conn.commit()
            
            return jsonify({
                'success': True,
                'object_id': object_id,
                'object_name': object_name,
                'total_size': total_size,
                'files': saved_files,
                'merged': existing_object is not None and is_merge
            })
            
        except Exception as e:
            conn.rollback()

            if 'object_id' in locals():
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

@app.route('/edit-object', methods=['POST'])
def edit_object():
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    
    try:
        object_id = request.form.get('objectId')
        object_name = request.form.get('objectName')
        created_by = session.get('admin_id', 1)
        
        if not object_id or not object_name:
            return jsonify({'success': False, 'error': 'Object ID and name are required'}), 400
        
        files = request.files.getlist('files')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            conn.execute('BEGIN')
            
            # Check if object exists
            cursor.execute('SELECT object_id, object_name, size FROM Object WHERE object_id = ?', (object_id,))
            existing_object = cursor.fetchone()
            
            if not existing_object:
                conn.close()
                return jsonify({'success': False, 'error': 'Object not found'}), 404
            
            current_time = datetime.now().isoformat()
            current_size = existing_object['size'] or 0
            
            # Update object name and timestamp
            cursor.execute('''
                UPDATE Object 
                SET object_name = ?, date_updated = ?
                WHERE object_id = ?
            ''', (object_name, current_time, object_id))
            
            # Add new files if any
            total_new_size = 0
            saved_files = []
            
            if files and len(files) > 0:
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
                        
                        total_new_size += file_size
                        
                        # Save file
                        original_filename = secure_filename(file.filename)
                        file_extension = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
                        unique_filename = f"{uuid.uuid4().hex}.{file_extension}" if file_extension else str(uuid.uuid4().hex)
                        
                        object_dir = os.path.join(UPLOAD_FOLDER, f"object_{object_id}")
                        os.makedirs(object_dir, exist_ok=True)
                        
                        file_path = os.path.join(object_dir, unique_filename)
                        file.save(file_path)
                        
                        # Insert file record
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
            
            # Update object size if new files were added
            if total_new_size > 0:
                new_total_size = current_size + total_new_size
                cursor.execute('''
                    UPDATE Object 
                    SET size = ?
                    WHERE object_id = ?
                ''', (new_total_size, object_id))
            
            # Update folder timestamp
            cursor.execute('''
                UPDATE Folder SET last_updated = ? WHERE folder_id = 1
            ''', (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'object_id': object_id,
                'object_name': object_name,
                'files_added': len(saved_files),
                'files': saved_files
            })
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Edit failed: {str(e)}'
        }), 500

@app.route('/folder-info')
def get_folder_info():
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    
    try:
        conn = sqlite3.connect('admin.db')
        cursor = conn.cursor()
        cursor.execute("SELECT folder_name, last_updated, date_created FROM Folder WHERE folder_id = 1")
        folder = cursor.fetchone()
        conn.close()
        
        if folder:
            folder_name, last_updated, date_created = folder
            last_updated_formatted = format_date_flexible(last_updated) if last_updated else "N/A"
            date_created_formatted = format_date_flexible(date_created) if date_created else "N/A"
            
            return jsonify({
                'success': True,
                'folder': {
                    'folder_name': folder_name,
                    'last_updated': last_updated_formatted,
                    'date_created': date_created_formatted
                }
            })
        else:
            return jsonify({
                'success': True,
                'folder': {
                    'folder_name': "Not Set",
                    'last_updated': "N/A",
                    'date_created': "N/A"
                }
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to fetch folder info: {str(e)}'
        }), 500

@app.route('/objects')
def get_objects():
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    
    sort_by = request.args.get('sort', 'updated')
    
    conn = sqlite3.connect('admin.db')
    cursor = conn.cursor()

    if sort_by == 'created':
        order_clause = 'ORDER BY o.date_created DESC'
    elif sort_by == 'name-asc':
        order_clause = 'ORDER BY o.object_name ASC'
    elif sort_by == 'name-desc':
        order_clause = 'ORDER BY o.object_name DESC'
    else:  # default
        order_clause = 'ORDER BY o.date_updated DESC'
    
    cursor.execute(f'''
        SELECT 
            o.object_id,
            o.object_name,
            o.date_created,
            o.date_updated,
            o.created_by,
            o.size,
            COUNT(f.file_id) as file_count,
            a.first_name,
            a.last_name
        FROM Object o
        LEFT JOIN File f ON o.object_id = f.object_id
        LEFT JOIN Admin a ON o.created_by = a.admin_id
        GROUP BY o.object_id
        {order_clause}
    ''')
    objects_data = cursor.fetchall()
    conn.close()

    objects = []
    for obj in objects_data:
        date_created_formatted = format_date_flexible(obj[2])
        date_updated_formatted = format_date_flexible(obj[3])
        size_formatted = format_file_size(obj[5]) if obj[5] else "0 Bytes"
        
        created_by_name = "Unknown"
        if obj[7] and obj[8]:
            created_by_name = f"{obj[7]} {obj[8]}"
        elif obj[7]:
            created_by_name = obj[7]
        
        objects.append({
            'object_id': obj[0],
            'object_name': obj[1],
            'date_created': obj[2],
            'date_updated': obj[3],
            'created_by': obj[4],
            'size': obj[5],
            'file_count': obj[6],
            'date_created_formatted': date_created_formatted,
            'date_updated_formatted': date_updated_formatted,
            'size_formatted': size_formatted,
            'created_by_name': created_by_name
        })

    return jsonify({
        'success': True,
        'objects': objects
    })

@app.route('/object/<int:object_id>/files')
def get_object_files(object_id):
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT f.file_id, f.file_name, f.date_created, f.size,
                   a.first_name, a.last_name
            FROM File f
            LEFT JOIN Admin a ON f.created_by = a.admin_id
            WHERE f.object_id = ?
            ORDER BY f.date_created DESC
        ''', (object_id,))
        
        files = cursor.fetchall()
        
        formatted_files = []
        for file in files:
            formatted_files.append({
                'file_id': file[0],
                'file_name': file[1],
                'date_created': file[2],
                'size': file[3],
                'created_by_name': f"{file[4]} {file[5]}" if file[4] and file[5] else 'Unknown'
            })
        
        conn.close()
        return jsonify({
            'success': True,
            'files': formatted_files
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
        
@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('admin_id', None)
    return redirect(url_for('login'))

@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

if __name__ == '__main__':
    app.run(debug=True)