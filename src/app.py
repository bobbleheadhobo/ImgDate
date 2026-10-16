import os
from dotenv import load_dotenv

load_dotenv()

# Cap the image size OpenCV will decode before it is imported (via ImageOrganizer),
# so a small file that claims huge dimensions can't exhaust memory.
MAX_IMAGE_PIXELS = int(os.getenv('MAX_IMAGE_PIXELS', 100_000_000))
os.environ.setdefault('OPENCV_IO_MAX_IMAGE_PIXELS', str(MAX_IMAGE_PIXELS))

import ipaddress
import re
import shutil
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, request, render_template, send_file, jsonify
from PIL import Image
import requests
from werkzeug.utils import secure_filename
from ImageOrganizer import ImageOrganizer
import tempfile
import zipfile
import uuid
import threading
import time
import SharedVariables as s
from LoggerConfig import setup_logger

app = Flask(__name__)

log = setup_logger("WebServer", "../log/webserver.log")

TURNSTILE_KEY = os.getenv('CF_TURNSTILE_KEY')
TURNSTILE_SITE_KEY = os.getenv('CF_TURNSTILE_SITE_KEY', '')
# Only for local testing: skips Turnstile when CF_TURNSTILE_KEY is not set
DEV_MODE = os.getenv('DEV_MODE') == '1'
# Proxies allowed to set CF-Connecting-IP (Pangolin/Newt reach the app from a local or private address)
TRUSTED_PROXIES = [
    ipaddress.ip_network(net.strip())
    for net in os.getenv(
        'TRUSTED_PROXIES',
        '127.0.0.0/8,::1/128,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,fc00::/7'
    ).split(',')
    if net.strip()
]

# Configuration
# Absolute so send_file (which resolves relative paths from src/) and os calls agree
UPLOAD_FOLDER = os.path.abspath('../img/web/uploads')
PROCESSED_FOLDER = os.path.abspath('../img/web/processed')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'tiff'}
ALLOWED_IMAGE_FORMATS = {'PNG', 'JPEG', 'TIFF', 'MPO'}  # MPO: multi-picture JPEGs from some phones/cameras
DATE_FORMATS = {'mm_dd_yy', 'yy_mm_dd', 'universal'}
DATE_RANGE_PATTERN = re.compile(r'\d{2}/\d{2}/\d{4}( to \d{2}/\d{2}/\d{4})?')
MAX_FILES_PER_UPLOAD = int(os.getenv('MAX_FILES_PER_UPLOAD', 100))
UPLOADS_PER_HOUR = int(os.getenv('UPLOADS_PER_HOUR', 20))
MAX_CONCURRENT_BATCHES = int(os.getenv('MAX_CONCURRENT_BATCHES', 2))
MAX_QUEUED_BATCHES = int(os.getenv('MAX_QUEUED_BATCHES', 10))
WORKERS_PER_BATCH = int(os.getenv('WORKERS_PER_BATCH', 3))
MAX_DATE_READS_PER_BATCH = int(os.getenv('MAX_DATE_READS_PER_BATCH', 300))  # caps OpenAI calls per upload
MIN_FREE_DISK_GB = float(os.getenv('MIN_FREE_DISK_GB', 5))
DOWNLOAD_EXPIRY_SECONDS = 60 * 60       # visitors' download links work for 1 hour
FAILED_BATCH_RETENTION_SECONDS = 2 * 60 * 60
ASSET_VERSION = '3'  # bump to bust cached JS/CSS after frontend changes

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200 MB limit

Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

# Ensure upload and processed folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

if not TURNSTILE_KEY and not DEV_MODE:
    log.error("CF_TURNSTILE_KEY is not set: all uploads will be rejected. Set DEV_MODE=1 to skip verification locally.")

# Batches run through a fixed-size pool so a flood of uploads queues instead of
# starting unlimited processing threads
batch_executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_BATCHES)

upload_times = {}  # client IP -> deque of upload timestamps in the last hour
upload_times_lock = threading.Lock()


def has_free_disk_space():
    for folder in (PROCESSED_FOLDER, tempfile.gettempdir()):
        try:
            if shutil.disk_usage(folder).free < MIN_FREE_DISK_GB * 1024 ** 3:
                log.error(f"Less than {MIN_FREE_DISK_GB} GB free in {folder}, rejecting uploads")
                return False
        except FileNotFoundError:
            continue
    return True


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_client_ip():
    """Use Cloudflare's visitor IP only when the request came through a trusted proxy."""
    remote = request.remote_addr or ''
    try:
        remote_ip = ipaddress.ip_address(remote)
    except ValueError:
        return remote

    if any(remote_ip in network for network in TRUSTED_PROXIES):
        try:
            return str(ipaddress.ip_address(request.headers.get('CF-Connecting-IP', '').strip()))
        except ValueError:
            pass
    return str(remote_ip)


def is_rate_limited(client_ip):
    now = time.time()
    # One IPv6 user usually controls a whole /64, so count it as one visitor
    key = client_ip
    try:
        if ipaddress.ip_address(client_ip).version == 6:
            key = str(ipaddress.ip_network(f"{client_ip}/64", strict=False))
    except ValueError:
        pass
    with upload_times_lock:
        times = upload_times.setdefault(key, deque())
        while times and now - times[0] > 3600:
            times.popleft()
        if len(times) >= UPLOADS_PER_HOUR:
            return True
        times.append(now)
        return False


def is_safe_image(path):
    """Check the file really is a supported image and isn't too large to decode."""
    try:
        with Image.open(path) as img:
            width, height = img.size
            return img.format in ALLOWED_IMAGE_FORMATS and width * height <= MAX_IMAGE_PIXELS
    except Exception as e:
        log.warning(f"Rejected upload {os.path.basename(path)}: {e}")
        return False


def unique_upload_path(directory, original_filename, index):
    ext = original_filename.rsplit('.', 1)[1].lower()
    filename = secure_filename(original_filename)
    # secure_filename drops non-ASCII characters, which can leave no name or no extension
    if not filename.lower().endswith('.' + ext):
        filename = f"image_{index}.{ext}"
    base, extension = os.path.splitext(filename)
    base = base[:100]  # leave room for the suffixes added later
    file_path = os.path.join(directory, base + extension)
    counter = 1
    while os.path.exists(file_path):
        file_path = os.path.join(directory, f"{base}_{counter}{extension}")
        counter += 1
    return file_path


def parse_options(form):
    """Validate the upload options. Returns (options, error message)."""
    date_format = form.get('date_format') or None
    if date_format is not None and date_format not in DATE_FORMATS:
        return None, 'Invalid date format'

    date_range = (form.get('date_range') or '').strip()
    if date_range and not DATE_RANGE_PATTERN.fullmatch(date_range):
        return None, 'Invalid date range'

    return {
        'date_format': date_format,
        'date_range': date_range,
        'fix_orientation': form.get('fix_orientation') == 'true',
        'crop_images': form.get('crop_images') == 'true',
        'date_images': form.get('date_images') == 'true',
        'draw_contours': form.get('draw_contours') == 'true',
        'sort_images': form.get('sort_images') == 'true',
        # Used in file names inside the zip, so it must not contain path separators
        'file_prefix': secure_filename((form.get('file_prefix') or '').strip())[:50],
    }, None


@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'same-origin'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' https://challenges.cloudflare.com https://static.cloudflareinsights.com; "
        "frame-src https://challenges.cloudflare.com; "
        "connect-src 'self' https://cloudflareinsights.com; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https://upload.wikimedia.org; "
        "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'"
    )
    return response


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html', turnstile_site_key=TURNSTILE_SITE_KEY, asset_version=ASSET_VERSION)


@app.route('/start-upload', methods=['POST'])
def start_upload():
    client_ip = get_client_ip()

    # Check the captcha and rate limit before touching request.form/files,
    # which would make Flask read and store the whole upload
    if not check_turnstile(request.headers.get('X-Turnstile-Token', ''), client_ip):
        return jsonify({'error': 'Human verification failed. Please reload and try again.'}), 403

    if is_rate_limited(client_ip):
        log.warning(f"Rate limited upload from {client_ip}")
        return jsonify({'error': 'Too many uploads. Please wait a while and try again.'}), 429

    queued = sum(1 for batch in list(s.batches.values()) if batch['status'] == 'queued')
    if queued >= MAX_QUEUED_BATCHES or not has_free_disk_space():
        return jsonify({'error': 'The server is busy. Please try again later.'}), 503

    if 'files[]' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    files = [file for file in request.files.getlist('files[]') if file and file.filename]

    if not files:
        return jsonify({'error': 'No selected file'}), 400

    if len(files) > MAX_FILES_PER_UPLOAD:
        return jsonify({'error': f'Please upload at most {MAX_FILES_PER_UPLOAD} images at a time'}), 400

    options, error = parse_options(request.form)
    if error:
        return jsonify({'error': error}), 400

    batch_id = str(uuid.uuid4())

    # Create a temporary directory to store uploaded files
    temp_dir = tempfile.mkdtemp()

    # Save uploaded files to the temporary directory
    saved_files = []
    try:
        for index, file in enumerate(files):
            if not allowed_file(file.filename):
                continue
            file_path = unique_upload_path(temp_dir, file.filename, index)
            file.save(file_path)
            if is_safe_image(file_path):
                saved_files.append(file_path)
            else:
                os.remove(file_path)
    except Exception as e:
        log.error(f"Error saving upload: {e}")
        shutil.rmtree(temp_dir, ignore_errors=True)
        return jsonify({'error': 'Failed to save upload'}), 500

    if not saved_files:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return jsonify({'error': 'No valid images were uploaded'}), 400

    # Store batch information
    s.batches[batch_id] = {
        'status': 'queued',
        'files': saved_files,
        'temp_dir': temp_dir,
        'created_at': time.time(),
        'options': options,
    }

    batch_executor.submit(run_batch, batch_id)

    return jsonify({'message': 'Upload started', 'batchId': batch_id}), 200


@app.route('/api/status/<batch_id>', methods=['GET'])
def get_status(batch_id):
    if batch_id in s.batches:
        batch = s.batches[batch_id]
        current_time = time.time()

        # If the batch is older than 15 minutes, consider it failed
        if batch['status'] == 'processing' and current_time - batch.get('start_time', current_time) > 15 * 60:  # 15 minutes in seconds
            log.info(f"Current time: {current_time}, "
                    f"Start time: {batch.get('start_time', current_time)}, "
                    f"Time difference: {current_time - batch.get('start_time', current_time)}")

            batch['status'] = 'failed'
            batch['error'] = 'Process timed out'

        return jsonify({
            'status': batch['status'],
            'error': batch.get('error'),
            'current_image_num': batch.get('current_image_num', 0),
            'num_images': batch.get('num_images', 0),
        }), 200
    else:
        return jsonify({'error': 'Batch not found'}), 404


@app.route('/download/<batch_id>')
def download(batch_id):
    batch = s.batches.get(batch_id)
    if batch is None:
        return jsonify({'error': 'Batch not found'}), 404

    if batch['status'] != 'completed':
        return jsonify({'error': 'Batch not completed'}), 400

    if time.time() - batch['completed_at'] > DOWNLOAD_EXPIRY_SECONDS:
        return jsonify({'error': 'Download link expired'}), 410

    zip_filename = f'ImgDate_{batch_id}.zip'
    zip_path = os.path.join(app.config['PROCESSED_FOLDER'], zip_filename)

    if not os.path.exists(zip_path):
        return jsonify({'error': 'File not found'}), 404

    try:
        return send_file(zip_path, as_attachment=True, download_name=zip_filename)
    except Exception as e:
        log.error(f"Error sending file: {str(e)}")
        return jsonify({'error': 'Failed to send file'}), 500


def run_batch(batch_id):
    batch = s.batches[batch_id]
    try:
        process_images(batch_id)
    except Exception:
        log.exception(f"Unexpected error processing batch {batch_id}")
        batch['status'] = 'failed'
        batch['error'] = 'Processing failed'
    finally:
        # Clean up the temporary directory
        temp_dir = batch.get('temp_dir')
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
            log.info(f"Deleted temporary directory: {temp_dir}")


def process_images(batch_id):
    batch = s.batches[batch_id]
    options = batch['options']
    batch['status'] = 'processing'
    batch['start_time'] = time.time()

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

        # Process images
        image_organizer = ImageOrganizer(
            save_path=save_path,
            scans_path=scans_path,
            error_path=error_path,
            archive_scans=False,
            sort_images=options['sort_images'],
            fix_orientation=options['fix_orientation'],
            crop_images=options['crop_images'],
            date_images=options['date_images'],
            draw_contours=options['draw_contours'],
            batch_progress=batch,
            date_format=options['date_format'],
            date_range=options['date_range'],
            max_workers=WORKERS_PER_BATCH,
            max_date_reads=MAX_DATE_READS_PER_BATCH
        )

        log.info("Options chosen:\n" + "\n".join(f"{k}={v}" for k, v in options.items()))

        try:
            image_organizer.process_images()
        except Exception as e:
            batch['status'] = 'failed'
            batch['error'] = 'Processing failed'
            log.error(f"Error processing images: {str(e)}")
            return

        # Apply prefix to processed images if provided
        prefix = options['file_prefix']
        if prefix:
            for root, _, files_in_dir in os.walk(save_path):
                for file in files_in_dir:
                    old_path = os.path.join(root, file)
                    new_filename = f"{prefix}_{file}"
                    new_path = os.path.join(root, new_filename)
                    try:
                        os.rename(old_path, new_path)
                    except OSError as e:
                        log.error(f"Could not add prefix to {file}: {e}")

        # Create a zip file of processed images
        zip_filename = f'ImgDate_{batch_id}.zip'
        zip_path = os.path.join(app.config['PROCESSED_FOLDER'], zip_filename)
        processed_count = 0
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for root, _, files_in_dir in os.walk(save_path):
                for file in files_in_dir:
                    zipf.write(os.path.join(root, file),
                               os.path.relpath(os.path.join(root, file), save_path))
                    processed_count += 1

            if options['draw_contours'] and os.path.exists(contours_path):
                for root, _, files_in_dir in os.walk(contours_path):
                    for file in files_in_dir:
                        zipf.write(os.path.join(root, file),
                                   os.path.relpath(os.path.join(root, file), scans_path))

        log.info(f"Processed {processed_count} images successfully")
        log.info("Finished processing request")
        batch['processed_count'] = processed_count
        batch['completed_at'] = time.time()
        batch['status'] = 'completed'


def check_turnstile(turnstile_response, visitor_ip):
    if not TURNSTILE_KEY:
        if DEV_MODE:
            log.info("CF_TURNSTILE_KEY not set and DEV_MODE=1, skipping verification")
            return True
        log.error("CF_TURNSTILE_KEY not set, rejecting upload")
        return False

    if not turnstile_response:
        return False

    try:
        response = requests.post('https://challenges.cloudflare.com/turnstile/v0/siteverify',
            data={
                'secret': TURNSTILE_KEY,
                'response': turnstile_response,
                'remoteip': visitor_ip
            },
            timeout=10
        )

        response.raise_for_status()
        log.info(f"Turnstile response: {response.text}")
        result = response.json()
    except Exception as e:
        log.error(f"Error verifying turnstile token: {str(e)}")
        return False

    return result.get('success') is True


def cleanup_expired():
    """Remove expired download zips and forget old batches."""
    now = time.time()
    for batch_id, batch in list(s.batches.items()):
        completed_at = batch.get('completed_at')
        if completed_at and now - completed_at > DOWNLOAD_EXPIRY_SECONDS:
            zip_path = os.path.join(PROCESSED_FOLDER, f'ImgDate_{batch_id}.zip')
            if os.path.exists(zip_path):
                os.remove(zip_path)
                log.info(f"Deleted expired zip: {zip_path}")
            s.batches.pop(batch_id, None)
        elif batch['status'] == 'failed' and now - batch.get('created_at', now) > FAILED_BATCH_RETENTION_SECONDS:
            s.batches.pop(batch_id, None)

    with upload_times_lock:
        for client_ip in list(upload_times):
            if not upload_times[client_ip] or now - upload_times[client_ip][-1] > 3600:
                del upload_times[client_ip]


def cleanup_loop():
    while True:
        time.sleep(5 * 60)
        try:
            cleanup_expired()
        except Exception:
            log.exception("Error cleaning up expired batches")


threading.Thread(target=cleanup_loop, daemon=True).start()

if __name__ == '__main__':
    app.run(debug=False, host=os.getenv('BIND_HOST', '0.0.0.0'), port=8888)
