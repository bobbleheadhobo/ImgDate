from flask import Flask, request, render_template, send_file, jsonify
import requests
from werkzeug.utils import secure_filename
import os
from ImageOrganizer import ImageOrganizer
import tempfile
import zipfile
import uuid
import threading
import time
from dotenv import load_dotenv
import SharedVariables as s

app = Flask(__name__)

TURNSTILE_KEY = os.getenv('CF_TURNSTILE_KEY')

# Configuration
UPLOAD_FOLDER = '../img/web/uploads'
PROCESSED_FOLDER = '../img/web/processed'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200 MB limit

# Ensure upload and processed folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def delayed_file_deletion(file_path, delay=10):
    def delete_file():
        time.sleep(delay)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                app.logger.info(f"Successfully deleted file: {file_path}")
        except Exception as e:
            app.logger.error(f"Error removing zip file after delay: {str(e)}")

    thread = threading.Thread(target=delete_file)
    thread.start()

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/api/progress', methods=['GET'])
def get_progress():
    if hasattr(s, 'num_images') and hasattr(s, 'current_image_num'):
        return jsonify({
            'num_images': s.num_images,
            'current_image_num': s.current_image_num
        }), 200
    else:
        return jsonify({'error': 'Progress not available'}), 404

@app.route('/upload', methods=['POST'])
def upload_and_process():
    
    turnstile_response = request.form.get('cf-turnstile-response')
    if not check_turnstile(turnstile_response):
        return jsonify({'error': 'Invalid token'}), 403
    
    if 'files[]' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    files = request.files.getlist('files[]')
    
    if not files or files[0].filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # Create a unique identifier for this batch
    batch_id = str(uuid.uuid4())
    
    # Reset shared variables
    s.reset()
    
    # Create a temporary directory for this upload
    with tempfile.TemporaryDirectory() as tmpdirname:
        scans_path = os.path.join(tmpdirname, 'scans')
        save_path = os.path.join(tmpdirname, 'processed')
        error_path = os.path.join(save_path, 'Failed')

        os.makedirs(scans_path)
        os.makedirs(save_path)
        os.makedirs(error_path)

        # Save uploaded files
        uploaded_count = 0
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(scans_path, filename))
                uploaded_count += 1

        s.date_format = request.form.get('date_format', None)
        
        # Process images
        image_organizer = ImageOrganizer(
            save_path=save_path,
            scans_path=scans_path,
            error_path=error_path,
            archive_scans=False,  # Removed archive functionality
            sort_images=request.form.get('sort_images') == 'true',
            fix_orientation=request.form.get('fix_orientation') == 'true',
            crop_images=request.form.get('crop_images') == 'true',
            date_images=request.form.get('date_images') == 'true',
            draw_contours=request.form.get('draw_contours') == 'true'
        )
        
        try:
            image_organizer.process_images()
        except Exception as e:
            return jsonify({'error': str(e)}), 500

        # Apply prefix to processed images if provided
        prefix = request.form.get('file_prefix', '').strip()
        if prefix:
            for root, _, files in os.walk(save_path):
                for file in files:
                    old_path = os.path.join(root, file)
                    new_filename = f"{prefix}_{file}"
                    new_path = os.path.join(root, new_filename)
                    os.rename(old_path, new_path)

        # Create a zip file of processed images
        zip_filename = f'processed_images_{batch_id}.zip'
        zip_path = os.path.join(app.config['PROCESSED_FOLDER'], zip_filename)
        processed_count = 0
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for root, _, files in os.walk(save_path):
                for file in files:
                    zipf.write(os.path.join(root, file), 
                               os.path.relpath(os.path.join(root, file), save_path))
                    processed_count += 1

        message = 'Images processed successfully'
        if uploaded_count != processed_count:
            message += f'. Warning: {uploaded_count - processed_count} images are missing from the processed output. Consider running again with contours enabled.'

        return jsonify({
            'message': message, 
            'download_url': f'/download/{batch_id}',
            'uploaded_count': uploaded_count,
            'processed_count': processed_count
        })

@app.route('/download/<batch_id>')
def download(batch_id):
    zip_filename = f'processed_images_{batch_id}.zip'
    zip_path = os.path.join(app.config['PROCESSED_FOLDER'], zip_filename)
    
    if not os.path.exists(zip_path):
        return jsonify({'error': 'File not found'}), 404

    try:
        return send_file(zip_path, as_attachment=True, download_name=zip_filename)
    except Exception as e:
        app.logger.error(f"Error sending file: {str(e)}")
        return jsonify({'error': 'Failed to send file'}), 500
    finally:
        # Schedule the zip file for deletion after a delay
        delayed_file_deletion(zip_path)
        

def check_turnstile(turnstile_response):
    try:
        response = requests.post('https://challenges.cloudflare.com/turnstile/v0/siteverify',
            data={
                'secret': TURNSTILE_KEY,
                'response': turnstile_response
                }
        )

        response.raise_for_status()
        print("response")
        print(response)
        result = response.json()
    except Exception as e:
        app.logger.error(f"Error verifying turnstile token: {str(e)}")
        return False

    return result.get('success')
    

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8888)