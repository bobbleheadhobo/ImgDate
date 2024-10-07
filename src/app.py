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

def delayed_file_deletion(file_path, delay=10):
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
    visitor_ip = request.headers.get('CF-Connecting-IP')
    if not check_turnstile(turnstile_response, visitor_ip):
        return jsonify({'error': 'Human Verification Failed. Please reload the page and try again.'}), 403
    
    if 'files[]' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    files = request.files.getlist('files[]')
    
    if not files or files[0].filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # Create a unique identifier for this batch
    batch_id = str(uuid.uuid4())
    

    # Log the IP address and other details of the request
    log.info("\n\n\n-----------------------------------")
    log.info(f"Request received from IP: {visitor_ip}")
    log.info(f"User Agent: {request.headers.get('User-Agent')}")
    log.info(f"Referrer: {request.referrer}")
    log.info(f"Uploaded files: {[file.filename for file in files]}")
    
    # Create a temporary directory for this upload
    with tempfile.TemporaryDirectory() as tmpdirname:
        scans_path = os.path.join(tmpdirname, 'scans')
        save_path = os.path.join(tmpdirname, 'processed')
        contours_path = os.path.join(scans_path, 'contours')
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

        # Log the options chosen by the user
        log.info(f"Options chosen: sort_images={request.form.get('sort_images')}, "
                 f"fix_orientation={request.form.get('fix_orientation')}, "
                 f"crop_images={request.form.get('crop_images')}, "
                 f"date_images={request.form.get('date_images')}, "
                 f"draw_contours={request.form.get('draw_contours')}, "
                 f"date_format={request.form.get('date_format')}, "
                 f"file_prefix={request.form.get('file_prefix')}")
        
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
        zip_filename = f'ImgDate_{batch_id}.zip'
        zip_path = os.path.join(app.config['PROCESSED_FOLDER'], zip_filename)
        processed_count = 0
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for root, _, files in os.walk(save_path):
                for file in files:
                    zipf.write(os.path.join(root, file), 
                               os.path.relpath(os.path.join(root, file), save_path))
                    processed_count += 1


            # If contours are drawn, zip the contours folder
            if request.form.get('draw_contours') == 'true' and os.path.exists(contours_path):
                for root, _, files in os.walk(contours_path):
                    for file in files:
                        zipf.write(os.path.join(root, file), 
                                   os.path.relpath(os.path.join(root, file), scans_path))
                        
        log.info(f"Processed {processed_count} images successfully")
        log.info("Finished processing request")
        message = "Images processed successfully"

        time.sleep(2)  # Ensure progress is updated before resetting shared variables
        s.reset()
        
        return jsonify({
            'message': message, 
            'download_url': f'/download/{batch_id}',
            'uploaded_count': uploaded_count,
            'processed_count': processed_count
        })

@app.route('/download/<batch_id>')
def download(batch_id):
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
        # Schedule the zip file for deletion after a delay
        delayed_file_deletion(zip_path)
        

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