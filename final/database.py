from flask import Flask, render_template, request, redirect, session, url_for, flash, jsonify, send_file, send_from_directory, abort
import sqlite3, bcrypt, os, mimetypes, requests, uuid
from datetime import datetime
from werkzeug.utils import secure_filename
from werkzeug.security import safe_join
from roboflow import Roboflow
import zipfile, shutil, time, json
import tempfile

app = Flask(__name__)
app.secret_key = 'your-secret-key'

ROBOFLOW_API_KEY = "AfYuRTydldlCG058tvsY"
ROBOFLOW_WORKSPACE = "eyeknow-6avgz"
ROBOFLOW_PROJECT = "eyeknow-yvckn"

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'svg'}
MAX_FILE_SIZE = 16 * 1024 * 1024

# Global variable to store current Colab server URL
CURRENT_COLAB_URL = None

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_colab_server_url():
    """Get the current Colab server URL"""
    global CURRENT_COLAB_URL
    
    # Try to read from file first (updated by Colab)
    try:
        url_file = os.path.join(os.getcwd(), 'colab_server_url.txt')
        if os.path.exists(url_file):
            with open(url_file, 'r') as f:
                url = f.read().strip()
                if url and url.startswith('http'):
                    CURRENT_COLAB_URL = url
                    return url
    except Exception as e:
        print(f"Error reading URL file: {e}")
    
    # Return cached URL if available
    if CURRENT_COLAB_URL:
        return CURRENT_COLAB_URL
    
    return None

def check_colab_server_health():
    """Check if the Colab server is running and model is available"""
    try:
        server_url = get_colab_server_url()
        if not server_url:
            return False, "Colab server URL not available. Please run the server script in Colab."
        
        # Check health endpoint
        health_url = f"{server_url}/health"
        print(f"🔍 Checking health at: {health_url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(health_url, timeout=15, headers=headers, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check successful: {data}")
            return True, data
        else:
            print(f"❌ Health check failed with status {response.status_code}")
            return False, f"Server returned status {response.status_code}"
            
    except requests.exceptions.SSLError:
        print("⚠️ SSL certificate error")
        return False, "SSL certificate error. Server is running but network restrictions apply."
    except requests.exceptions.ConnectionError:
        print("❌ Connection error to Colab server")
        return False, "Cannot connect to Colab server due to network restrictions. Server is running but not accessible from Flask app."
    except requests.exceptions.Timeout:
        print("❌ Timeout connecting to Colab server")
        return False, "Connection to Colab server timed out."
    except Exception as e:
        print(f"❌ Error checking server health: {str(e)}")
        return False, f"Error checking server health: {str(e)}"

@app.route('/update_colab_url', methods=['POST'])
def update_colab_url():
    """Route for Colab server to notify this app of its URL"""
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        
        if not url or not url.startswith('http'):
            return jsonify({'error': 'Invalid URL provided'}), 400
        
        # Save the URL to a local file
        with open('colab_server_url.txt', 'w') as f:
            f.write(url)
        
        # Update global variable
        global CURRENT_COLAB_URL
        CURRENT_COLAB_URL = url
        
        print(f"✅ Received and saved Colab URL: {url}")
        return jsonify({'message': 'Colab URL updated successfully', 'url': url}), 200
        
    except Exception as e:
        print(f"❌ Error updating Colab URL: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/download_model')
def download_model():
    """Download the model from Colab server"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    try:
        is_healthy, health_data = check_colab_server_health()
        
        if not is_healthy:
            flash(f"Cannot download model: {health_data}")
            return redirect(url_for('dashboard'))
        
        if not (isinstance(health_data, dict) and health_data.get('model_exists')):
            flash("Model not found on Colab server. Please ensure training is complete.")
            return redirect(url_for('dashboard'))
        
        response, filename = download_model_from_colab()

        def generate():
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk
        
        return app.response_class(
            generate(),
            mimetype='application/octet-stream',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Type': 'application/octet-stream'
            }
        )
        
    except Exception as e:
        print(f"❌ Download error: {str(e)}")
        flash(f"Download failed: {str(e)}")
        return redirect(url_for('dashboard'))

@app.route('/get_colab_status')
def get_colab_status():
    """Get current Colab server status (for debugging)"""
    try:
        server_url = get_colab_server_url()
        is_healthy, health_data = check_colab_server_health()
        
        return jsonify({
            'server_url': server_url,
            'is_healthy': is_healthy,
            'health_data': health_data,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        })

@app.route('/set_colab_url', methods=['GET', 'POST'])
def set_colab_url():
    """Manual page to set Colab server URL"""
    if 'username' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        url = request.form.get('url', '').strip()
        
        if not url or not url.startswith('http'):
            flash('Invalid URL provided')
            return render_template('set_colab_url.html')
        
        try:
            # Save the URL
            with open('colab_server_url.txt', 'w') as f:
                f.write(url)
            
            global CURRENT_COLAB_URL
            CURRENT_COLAB_URL = url
            
            # Test the URL
            is_healthy, health_data = check_colab_server_health()
            
            if is_healthy:
                flash('Colab URL updated successfully and server is responding!', 'success')
            else:
                flash(f'Colab URL updated but server check failed: {health_data}', 'warning')
            
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            flash(f'Error updating URL: {str(e)}')
            return render_template('set_colab_url.html')
    
    current_url = get_colab_server_url()
    return render_template('set_colab_url.html', current_url=current_url)




def upload_object_as_batch_to_roboflow(object_dir, object_name, object_id):
    """Upload an entire object as a single batch to Roboflow"""
    try:
        # Initialize Roboflow
        rf = Roboflow(api_key=ROBOFLOW_API_KEY)
        workspace = rf.workspace(ROBOFLOW_WORKSPACE)
        project = workspace.project(ROBOFLOW_PROJECT)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        batch_name = f"{object_name}"
        
        # Create temporary zip file for batch upload
        temp_zip_dir = os.path.join(os.path.dirname(object_dir), 'temp_zips')
        os.makedirs(temp_zip_dir, exist_ok=True)
        
        zip_filename = f"{batch_name}.zip"
        zip_path = os.path.join(temp_zip_dir, zip_filename)
        
        # Create zip file with all images in the object directory
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            image_count = 0
            for root, dirs, files in os.walk(object_dir):
                for file in files:
                    if file.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.svg')):
                        file_path = os.path.join(root, file)
                        arcname = file
                        zipf.write(file_path, arcname)
                        image_count += 1
            
            if image_count == 0:
                print(f"❌ No valid images found in {object_dir}")
                return False
        
        print(f"📦 Created batch zip with {image_count} images: {zip_filename}")
        
        # Upload batch to Roboflow
        try:
            print(f"🚀 Uploading batch '{batch_name}' to Roboflow...")
            
            upload_result = project.upload(
                image_path=zip_path,
                num_retry_uploads=3,
                batch_name=batch_name,
                split="train"
            )
            
            print(f"✅ Successfully uploaded batch '{batch_name}' to Roboflow")
            print(f"📊 Upload result: {upload_result}")
            
            success = True
            
        except Exception as upload_error:
            print(f"❌ Failed to upload batch '{batch_name}': {str(upload_error)}")
            success = False
        
        # Clean up temporary zip file
        try:
            if os.path.exists(zip_path):
                os.remove(zip_path)
            if os.path.exists(temp_zip_dir) and not os.listdir(temp_zip_dir):
                os.rmdir(temp_zip_dir)
        except Exception as cleanup_error:
            print(f"⚠️ Warning: Could not clean up temporary files: {str(cleanup_error)}")
        
        return success
        
    except Exception as e:
        print(f"❌ Error in batch upload process: {str(e)}")
        return False

def upload_individual_images_to_roboflow_api(object_dir, object_name, object_id):
    """Alternative method: Upload individual images via Roboflow API"""
    api_url = f"https://api.roboflow.com/dataset/{ROBOFLOW_PROJECT}/upload"
    
    # Create unique batch identifier
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    batch_id = f"{object_name}"
    
    success_count = 0
    error_count = 0
    
    # Get all image files in the directory
    image_files = []
    for filename in os.listdir(object_dir):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.svg')):
            image_files.append(filename)
    
    if not image_files:
        print(f"❌ No valid images found in {object_dir}")
        return False
    
    print(f"🚀 Uploading {len(image_files)} images individually to batch '{batch_id}'...")
    
    for i, filename in enumerate(image_files):
        file_path = os.path.join(object_dir, filename)
        
        try:
            with open(file_path, "rb") as image_file:
                # Create unique name for this image within the batch
                unique_image_name = f"{batch_id}_{i+1:03d}_{filename}"
                
                files = {
                    "file": (filename, image_file, 'image/jpeg')
                }
                
                params = {
                    "api_key": ROBOFLOW_API_KEY,
                    "name": unique_image_name,
                    "split": "train",
                    "batch": batch_id
                }
                
                response = requests.post(
                    api_url,
                    params=params,
                    files=files,
                    timeout=30
                )
                
                if response.status_code == 200:
                    print(f"✅ Uploaded {i+1}/{len(image_files)}: {filename}")
                    success_count += 1
                else:
                    print(f"❌ Failed to upload {filename}: Status {response.status_code}")
                    print(f"Response: {response.text}")
                    error_count += 1
                
                # Small delay to avoid overwhelming the API
                time.sleep(0.2)
                
        except Exception as e:
            print(f"❌ Error uploading {filename}: {str(e)}")
            error_count += 1
    
    print(f"📊 Upload summary for batch '{batch_id}' - Success: {success_count}, Errors: {error_count}")
    return success_count > 0 and error_count == 0

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
            o.roboflow_status,
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
        print(f"Raw date_created: {obj[3]} (type: {type(obj[3])})")
        print(f"Raw date_updated: {obj[4]} (type: {type(obj[4])})")
        
        date_created_formatted = format_date_flexible(obj[3])
        date_updated_formatted = format_date_flexible(obj[4])
 
        size_formatted = format_file_size(obj[6]) if obj[6] else "0 Bytes"

        created_by_name = "Unknown"
        if obj[8] and obj[9]:
            created_by_name = f"{obj[8]} {obj[9]}"
        elif obj[8]:
            created_by_name = obj[8]
        
        objects.append({
            'roboflow_status': obj[0],
            'object_id': obj[1],
            'object_name': obj[2],
            'date_created': obj[3],
            'date_updated': obj[4],
            'created_by': obj[5],
            'size': obj[6],
            'file_count': obj[7],
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

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    
    try:
        object_name = request.form.get('batchName')
        is_merge = request.form.get('merge') == 'true'
        created_by = session.get('admin_id', 1)

        if not object_name or not object_name.strip():
            return jsonify({'success': False, 'error': 'Object name is required'}), 400
        
        object_name = object_name.strip()
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
                        'error': f'File too large: {file.filename} (Max: 16MB)'
                    }), 400
                
                total_size += file_size
                valid_files.append((file, file_size))
        
        if not valid_files:
            return jsonify({'success': False, 'error': 'No valid files found'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            conn.execute('BEGIN')

            # Check if object name already exists
            cursor.execute('SELECT object_id, size FROM Object WHERE object_name = ?', (object_name,))
            existing_object = cursor.fetchone()
            
            if existing_object and not is_merge:
                conn.close()
                return jsonify({
                    'success': False, 
                    'conflict': True,
                    'error': f'Object "{object_name}" already exists'
                }), 409
            
            current_time = datetime.now().isoformat()
            
            if existing_object and is_merge:
                # Merge with existing object
                object_id = existing_object['object_id']
                current_size = existing_object['size'] or 0
                new_total_size = current_size + total_size
                
                cursor.execute('''
                    UPDATE Object 
                    SET size = ?, date_updated = ?, roboflow_status = ?
                    WHERE object_id = ?
                ''', (new_total_size, current_time, 'pending', object_id))
                
            else:
                # Create new object
                cursor.execute('''
                    INSERT INTO Object (object_name, date_created, date_updated, created_by, size, roboflow_status)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (object_name, current_time, current_time, created_by, total_size, 'pending'))
                
                object_id = cursor.lastrowid
            
            # Create object-specific directory with consistent naming
            object_dir = os.path.join(UPLOAD_FOLDER, f"{object_name}_{object_id}")
            os.makedirs(object_dir, exist_ok=True)
            
            # Save files to disk and database
            saved_files = []
            for file, file_size in valid_files:
                original_filename = secure_filename(file.filename)
                file_extension = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
                unique_filename = f"{uuid.uuid4().hex}.{file_extension}" if file_extension else str(uuid.uuid4().hex)

                file_path = os.path.join(object_dir, unique_filename)
                file.save(file_path)
                
                cursor.execute('''
                    INSERT INTO File (object_id, file_name, uuid_filename, date_created, created_by, size)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (object_id, original_filename, unique_filename, current_time, created_by, file_size))
                
                saved_files.append({
                    'file_id': cursor.lastrowid,
                    'original_name': original_filename,
                    'saved_as': unique_filename,
                    'size': file_size
                })

            # Upload to Roboflow as a single batch
            print(f"🔄 Starting Roboflow upload for object: {object_name} (ID: {object_id})")
            
            try:
                # Try batch upload first (recommended method)
                roboflow_success = upload_object_as_batch_to_roboflow(object_dir, object_name, object_id)
                
                if not roboflow_success:
                    print(f"⚠️ Batch upload failed, trying individual image upload...")
                    roboflow_success = upload_individual_images_to_roboflow_api(object_dir, object_name, object_id)
                
                final_status = "success" if roboflow_success else "failed"
                
                if roboflow_success:
                    print(f"✅ Successfully uploaded '{object_name}' to Roboflow as a batch")
                else:
                    print(f"❌ Failed to upload '{object_name}' to Roboflow")
                    
            except Exception as roboflow_error:
                print(f"❌ Roboflow upload error for '{object_name}': {str(roboflow_error)}")
                final_status = "failed"

            # Update object status
            cursor.execute('''
                UPDATE Object SET roboflow_status = ? WHERE object_id = ?
            ''', (final_status, object_id))

            # Update folder last modified time
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
                'merged': existing_object is not None and is_merge,
                'roboflow_status': final_status,
                'roboflow_uploaded': final_status == "success"
            })
            
        except Exception as e:
            conn.rollback()
            # Clean up uploaded files if database operation failed
            if 'object_dir' in locals() and os.path.exists(object_dir):
                shutil.rmtree(object_dir, ignore_errors=True)
            raise e
        finally:
            conn.close()
            
    except Exception as e:
        print(f"❌ Upload error: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Upload failed: {str(e)}'
        }), 500

@app.route('/edit_object', methods=['POST'])
def edit_object():
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    
    try:
        object_id = request.form.get('objectId')
        new_object_name = request.form.get('editObjectName')
        created_by = session.get('admin_id', 1)

        if not object_id:
            return jsonify({'success': False, 'error': 'Object ID is required'}), 400
        
        if not new_object_name or not new_object_name.strip():
            return jsonify({'success': False, 'error': 'Object name is required'}), 400

        new_object_name = new_object_name.strip()
        files = request.files.getlist('files')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            conn.execute('BEGIN')
            
            # Get existing object
            cursor.execute('SELECT object_id, object_name, size FROM Object WHERE object_id = ?', (object_id,))
            existing_object = cursor.fetchone()
            
            if not existing_object:
                conn.rollback()
                conn.close()
                return jsonify({'success': False, 'error': 'Object not found'}), 404

            # Check for name conflicts (if name is being changed)
            if existing_object['object_name'] != new_object_name:
                cursor.execute('SELECT object_id FROM Object WHERE object_name = ? AND object_id != ?', 
                             (new_object_name, object_id))
                name_conflict = cursor.fetchone()
                
                if name_conflict:
                    conn.rollback()
                    conn.close()
                    return jsonify({
                        'success': False, 
                        'error': f'Object name "{new_object_name}" already exists'
                    }), 409

            # Validate new files if any
            valid_files = []
            total_new_size = 0
            
            if files and len(files) > 0:
                for file in files:
                    if file and file.filename != '':
                        if not allowed_file(file.filename):
                            conn.rollback()
                            conn.close()
                            return jsonify({
                                'success': False, 
                                'error': f'File type not allowed: {file.filename}'
                            }), 400
                        
                        file_size = get_file_size(file)
                        if file_size > MAX_FILE_SIZE:
                            conn.rollback()
                            conn.close()
                            return jsonify({
                                'success': False, 
                                'error': f'File too large: {file.filename} (Max: 16MB)'
                            }), 400
                        
                        total_new_size += file_size
                        valid_files.append((file, file_size))
            
            # Update object in database
            current_size = existing_object['size'] or 0
            new_total_size = current_size + total_new_size
            current_time = datetime.now().isoformat()
            
            # If adding new files, set status to pending for re-upload
            new_status = 'pending' if valid_files else None
            
            if new_status:
                cursor.execute('''
                    UPDATE Object 
                    SET object_name = ?, size = ?, date_updated = ?, roboflow_status = ?
                    WHERE object_id = ?
                ''', (new_object_name, new_total_size, current_time, new_status, object_id))
            else:
                cursor.execute('''
                    UPDATE Object 
                    SET object_name = ?, size = ?, date_updated = ?
                    WHERE object_id = ?
                ''', (new_object_name, new_total_size, current_time, object_id))
            
            # Save new files if any
            saved_files = []
            if valid_files:
                # Use the NEW object name for directory - CONSISTENT WITH UPLOAD
                object_dir = os.path.join(UPLOAD_FOLDER, f"{new_object_name}_{object_id}")
                os.makedirs(object_dir, exist_ok=True)
                
                for file, file_size in valid_files:
                    original_filename = secure_filename(file.filename)
                    file_extension = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
                    unique_filename = f"{uuid.uuid4().hex}.{file_extension}" if file_extension else str(uuid.uuid4().hex)
                
                    file_path = os.path.join(object_dir, unique_filename)
                    file.save(file_path)
                    
                    cursor.execute('''
                        INSERT INTO File (object_id, file_name, uuid_filename, date_created, created_by, size)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (object_id, original_filename, unique_filename, current_time, created_by, file_size))
                    
                    saved_files.append({
                        'file_id': cursor.lastrowid,
                        'original_name': original_filename,
                        'saved_as': unique_filename,
                        'size': file_size
                    })

                # If new files were added, re-upload entire object to Roboflow as new batch
                print(f"🔄 Re-uploading updated object to Roboflow: {new_object_name} (ID: {object_id})")
                
                try:
                    roboflow_success = upload_object_as_batch_to_roboflow(object_dir, new_object_name, object_id)
                    
                    if not roboflow_success:
                        print(f"⚠️ Batch upload failed, trying individual image upload...")
                        roboflow_success = upload_individual_images_to_roboflow_api(object_dir, new_object_name, object_id)
                    
                    final_status = "success" if roboflow_success else "failed"
                    
                    cursor.execute('''
                        UPDATE Object SET roboflow_status = ? WHERE object_id = ?
                    ''', (final_status, object_id))
                    
                except Exception as roboflow_error:
                    print(f"❌ Roboflow re-upload error: {str(roboflow_error)}")
                    cursor.execute('''
                        UPDATE Object SET roboflow_status = ? WHERE object_id = ?
                    ''', ("failed", object_id))

            # Update folder timestamp
            cursor.execute('''
                UPDATE Folder SET last_updated = ? WHERE folder_id = 1
            ''', (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))

            conn.commit()
            
            return jsonify({
                'success': True,
                'object_id': object_id,
                'object_name': new_object_name,
                'total_size': new_total_size,
                'new_files': saved_files,
                'files_added': len(saved_files)
            })
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
            
    except Exception as e:
        print(f"❌ Edit error: {str(e)}")
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
            o.roboflow_status,
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
        date_created_formatted = format_date_flexible(obj[3])
        date_updated_formatted = format_date_flexible(obj[4])
        size_formatted = format_file_size(obj[6]) if obj[6] else "0 Bytes"
        
        created_by_name = "Unknown"
        if obj[8] and obj[9]:
            created_by_name = f"{obj[8]} {obj[9]}"
        elif obj[8]:
            created_by_name = obj[8]
        
        objects.append({
            'roboflow_status': obj[0],
            'object_id': obj[1],
            'object_name': obj[2],
            'date_created': obj[3],
            'date_updated': obj[4],
            'created_by': obj[5],
            'size': obj[6],
            'file_count': obj[7],
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

@app.route('/file/<int:file_id>/info')
def get_file_info(file_id):
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT f.file_id, f.file_name, f.uuid_filename, f.object_id, f.size, o.object_name
            FROM File f
            JOIN Object o ON f.object_id = o.object_id
            WHERE f.file_id = ?
        ''', (file_id,))
        
        file_record = cursor.fetchone()
        conn.close()
        
        if not file_record:
            return jsonify({'success': False, 'error': 'File not found in database'})

        object_id = file_record['object_id']
        object_name = file_record['object_name']
        file_name = file_record['file_name']
        uuid_filename = file_record['uuid_filename']
 
        # Use the same naming convention as upload: object_name + object_id
        object_dir = os.path.join(UPLOAD_FOLDER, f"{object_name}_{object_id}")
        actual_file_path = os.path.join(object_dir, uuid_filename)
        
        if not os.path.exists(actual_file_path):
            return jsonify({'success': False, 'error': f'File not found on disk: {uuid_filename}'})

        file_extension = os.path.splitext(file_name)[1].lower()
        is_image = file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg']
        
        return jsonify({
            'success': True,
            'file': {
                'file_id': file_record['file_id'],
                'file_name': file_name,
                'uuid_filename': uuid_filename,
                'file_exists': True,
                'is_image': is_image,
                'file_extension': file_extension,
                'size': file_record['size']
            }
        })
        
    except Exception as e:
        print(f"Error in get_file_info: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/file/<int:file_id>/download')
def download_file(file_id):
    """Force download of file"""
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT f.file_name, f.uuid_filename, f.object_id, o.object_name
            FROM File f
            JOIN Object o ON f.object_id = o.object_id
            WHERE f.file_id = ?
        ''', (file_id,))
        
        file_info = cursor.fetchone()
        conn.close()
        
        if not file_info:
            abort(404)
        
        file_name, uuid_filename, object_id, object_name = file_info
        # Use consistent naming: object_name + object_id
        object_dir = os.path.join(UPLOAD_FOLDER, f"{object_name}_{object_id}")
        actual_file_path = os.path.join(object_dir, uuid_filename)
        
        if not os.path.exists(actual_file_path):
            print(f"File not found: {actual_file_path}")
            abort(404)

        return send_file(actual_file_path, as_attachment=True, download_name=file_name)
            
    except Exception as e:
        print(f"Error downloading file: {e}")
        abort(500)

@app.route('/file/<int:file_id>/view')
def view_file_inline(file_id):
    """Serve file for viewing inline (e.g., images in browser)"""
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT f.file_name, f.uuid_filename, f.object_id, o.object_name
            FROM File f
            JOIN Object o ON f.object_id = o.object_id
            WHERE f.file_id = ?
        ''', (file_id,))
        
        file_info = cursor.fetchone()
        conn.close()
        
        if not file_info:
            abort(404)
        
        file_name, uuid_filename, object_id, object_name = file_info
        # Use consistent naming: object_name + object_id
        object_dir = os.path.join(UPLOAD_FOLDER, f"{object_name}_{object_id}")
        actual_file_path = os.path.join(object_dir, uuid_filename)

        if not os.path.exists(actual_file_path):
            print(f"File not found: {actual_file_path}")
            abort(404)

        content_type, _ = mimetypes.guess_type(file_name)
        if content_type is None:
            content_type = 'application/octet-stream'

        return send_file(actual_file_path, mimetype=content_type)
            
    except Exception as e:
        print(f"Error serving file: {e}")
        abort(500)

@app.route('/file/<int:file_id>')
def serve_file(file_id):
    """Serve file - inline for images, download for others"""
    if 'username' not in session:
        return jsonify({'success': False, 'error': 'Authentication required'}), 401
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT f.file_name, f.uuid_filename, f.object_id, o.object_name
            FROM File f
            JOIN Object o ON f.object_id = o.object_id
            WHERE f.file_id = ?
        ''', (file_id,))
        
        file_info = cursor.fetchone()
        conn.close()
        
        if not file_info:
            abort(404)
        
        file_name, uuid_filename, object_id, object_name = file_info
        # Use consistent naming: object_name + object_id
        object_dir = os.path.join(UPLOAD_FOLDER, f"{object_name}_{object_id}")
        actual_file_path = os.path.join(object_dir, uuid_filename)
        
        if not os.path.exists(actual_file_path):
            abort(404)

        content_type, _ = mimetypes.guess_type(file_name)
        if content_type is None:
            content_type = 'application/octet-stream'
    
        if content_type.startswith('image/'):
            return send_file(actual_file_path, mimetype=content_type)
        else:
            return send_file(actual_file_path, as_attachment=True, download_name=file_name)
            
    except Exception as e:
        print(f"Error serving file: {e}")
        abort(500)

@app.errorhandler(413)
def too_large(e):
    return jsonify({'success': False, 'error': 'File too large'}), 413

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'success': False, 'error': 'Internal server error'}), 500
        
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