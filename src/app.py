import shutil
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
from LoggerConfig import setup_logger

app = Flask(__name__)

load_dotenv()
TURNSTILE_KEY = os.getenv('CF_TURNSTILE_KEY')
log = setup_logger("WebServer", "../log/webserver.log")

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

def delayed_file_deletion(file_path, delay=360):
    def delete_file():
        time.sleep(delay)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                log.info(f"Successfully deleted file: {file_path}")
        except Exception as e:
            log.error(f"Error removing zip file after delay: {str(e)}")

    thread = threading.Thread(target=delete_file)
    thread.start()

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/verify-turnstile', methods=['POST'])
def verify_turnstile():
    log.info(f"Request received from IP: {request.headers.get('CF-Connecting-IP')}")
    log.info(f"User Agent: {request.headers.get('User-Agent')}")
    log.info(f"Referrer: {request.referrer}")
    
    turnstile_response = request.form.get('cf-turnstile-response')
    visitor_ip = request.headers.get('CF-Connecting-IP')
    if check_turnstile(turnstile_response, visitor_ip):
        return jsonify({'message': 'Verification successful'}), 200
    else:
        return jsonify({'error': 'Human Verification Failed. Please reload and try again.'}), 403

@app.route('/start-upload', methods=['POST'])
def start_upload():
    if 'files[]' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    files = request.files.getlist('files[]')
    
    if not files or files[0].filename == '':
        return jsonify({'error': 'No selected file'}), 400

    batch_id = str(uuid.uuid4())
    
    log.info(s)
    # log.info(s.batches)
    log.info(s.num_images)
    log.info(s.current_image_num)
    log.info(s.date_format)
    log.info(s.date_range)
    
    
    # Create a temporary directory to store uploaded files
    temp_dir = tempfile.mkdtemp()
    
    # Store batch information
    s.batches[batch_id] = {
        'status': 'started',
        'files': [],
        'temp_dir': temp_dir,
        'options': {
            'date_format': request.form.get('date_format'),
            'date_range': request.form.get('date_range'),
            'fix_orientation': request.form.get('fix_orientation') == 'true',
            'crop_images': request.form.get('crop_images') == 'true',
            'date_images': request.form.get('date_images') == 'true',
            'draw_contours': request.form.get('draw_contours') == 'true',
            'sort_images': request.form.get('sort_images') == 'true',
            'file_prefix': request.form.get('file_prefix', '').strip()
        }
    }

    # Save uploaded files to the temporary directory
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(temp_dir, filename)
            file.save(file_path)
            s.batches[batch_id]['files'].append(file_path)

    # Start processing in a background thread
    thread = threading.Thread(target=process_images, args=(batch_id, temp_dir, request.form))
    thread.start()

    return jsonify({'message': 'Upload started', 'batchId': batch_id}), 200

@app.route('/api/status/<batch_id>', methods=['GET'])
def get_status(batch_id):
    if batch_id in s.batches:
        batch = s.batches[batch_id]
        current_time = time.time()
        
        # If the batch is older than 15 minutes, consider it failed
        if current_time - batch.get('last_updated', current_time) > 15:
            batch['status'] = 'failed'
            batch['error'] = 'Process timed out'

        # Update the last_updated timestamp
        batch['last_updated'] = current_time
        
        return jsonify({
            'status': batch['status'],
            'error': batch.get('error'),
            'current_image_num': s.current_image_num,
            'num_images': s.num_images,
        }), 200
    else:
        return jsonify({'error': 'Batch not found'}), 404

@app.route('/download/<batch_id>')
def download(batch_id):
    if batch_id not in s.batches:
        return jsonify({'error': 'Batch not found'}), 404
    
    if s.batches[batch_id]['status'] != 'completed':
        return jsonify({'error': 'Batch not completed'}), 400

    zip_filename = f'ImgDate_{batch_id}.zip'
    zip_path = os.path.join(app.config['PROCESSED_FOLDER'], zip_filename)
    
    if not os.path.exists(zip_path):
        return jsonify({'error': 'File not found'}), 404

    try:
        return send_file(zip_path, as_attachment=True, download_name=zip_filename)
    except Exception as e:
        log.error(f"Error sending file: {str(e)}")
        return jsonify({'error': 'Failed to send file'}), 500
    finally:
        delayed_file_deletion(zip_path)

def process_images(batch_id, temp_dir, form):
    batch = s.batches[batch_id]
    batch['status'] = 'processing'

    log.info("\n\n\n-----------------------------------")
    log.info(f"Processing batch {batch_id}")
    log.info(f"Uploaded files: {[os.path.basename(file) for file in batch['files']]}")

    with tempfile.TemporaryDirectory() as tmpdirname:
        scans_path = os.path.join(tmpdirname, 'scans')
        save_path = os.path.join(tmpdirname, 'processed')
        contours_path = os.path.join(scans_path, 'contours')
        error_path = os.path.join(save_path, 'Failed')

        os.makedirs(scans_path)
        os.makedirs(save_path)
        os.makedirs(error_path)

        for file_path in batch['files']:
            if os.path.exists(file_path):
                shutil.move(file_path, os.path.join(scans_path, os.path.basename(file_path)))
            else:
                log.error(f"File not found: {file_path}")

        s.date_format = form.get('date_format', None)
        s.date_range = form.get('date_range', None)
        
        # Process images
        image_organizer = ImageOrganizer(
            save_path=save_path,
            scans_path=scans_path,
            error_path=error_path,
            archive_scans=False,
            sort_images=form.get('sort_images') == 'true',
            fix_orientation=form.get('fix_orientation') == 'true',
            crop_images=form.get('crop_images') == 'true',
            date_images=form.get('date_images') == 'true',
            draw_contours=form.get('draw_contours') == 'true'
        )

        log.info("Options chosen:\n" + "\n".join(f"{k}={v}" for k, v in batch['options'].items()))
        
        try:
            image_organizer.process_images()
        except Exception as e:
            batch['status'] = 'failed'
            batch['error'] = str(e)
            log.error(f"Error processing images: {str(e)}")
            return
        
        finally:
            # Clean up the temporary directory
            temp_dir = batch.get('temp_dir')
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)

        # Apply prefix to processed images if provided
        prefix = form.get('file_prefix', '').strip()
        if prefix:
            for root, _, batch['files'] in os.walk(save_path):
                for file in batch['files']:
                    old_path = os.path.join(root, file)
                    new_filename = f"{prefix}_{file}"
                    new_path = os.path.join(root, new_filename)
                    os.rename(old_path, new_path)

        # Create a zip file of processed images
        zip_filename = f'ImgDate_{batch_id}.zip'
        zip_path = os.path.join(app.config['PROCESSED_FOLDER'], zip_filename)
        processed_count = 0
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for root, _, batch['files'] in os.walk(save_path):
                for file in batch['files']:
                    zipf.write(os.path.join(root, file), 
                               os.path.relpath(os.path.join(root, file), save_path))
                    processed_count += 1

            if form.get('draw_contours') == 'true' and os.path.exists(contours_path):
                for root, _, batch['files'] in os.walk(contours_path):
                    for file in batch['files']:
                        zipf.write(os.path.join(root, file), 
                                   os.path.relpath(os.path.join(root, file), scans_path))
                        
        log.info(f"Processed {processed_count} images successfully")
        log.info("Finished processing request")

        batch['status'] = 'completed'
        batch['processed_count'] = processed_count

def check_turnstile(turnstile_response, visitor_ip):
    try:
        response = requests.post('https://challenges.cloudflare.com/turnstile/v0/siteverify',
            data={
                'secret': TURNSTILE_KEY,
                'response': turnstile_response,
                'remoteip': visitor_ip
            }
        )

        response.raise_for_status()
        log.info(f"Turnstile response: {response.text}")
        result = response.json()
    except Exception as e:
        log.error(f"Error verifying turnstile token: {str(e)}")
        return False

    return result.get('success')

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8888)