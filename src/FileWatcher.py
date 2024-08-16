'''
Simple script to automate the process of dating digitized film entirely in the background
with the help of resilio sync for moving the files back and forth
'''

import shutil
import threading
import time
import os
import pyexiv2
import requests
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime
from ImageOrganizer import ImageOrganizer  # Assuming image_organizer is a module
from dotenv import load_dotenv
from LoggerConfig import setup_logger

log = setup_logger("FileWatcher", "..\log\ImgDate.log")
check_time = 60
start_time = 100
timeout = 600  # 10 minutes


# Step 1: Implement Event Handler to Monitor Directory
class FileChangeHandler(FileSystemEventHandler):
    def __init__(self):
        self.last_event_time = datetime.now()
        self.changes_detected = False

    # Only set changes_detected to True for created files
    def on_created(self, event):
        if not event.is_directory:
            self.last_event_time = datetime.now()
            self.changes_detected = True
            log.info(f"File added: {event.src_path}")


def run_with_timeout(func, timeout):
    thread = threading.Thread(target=func)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        raise TimeoutError("Function execution timed out")


# Step 2: Monitor the directory and check if no new files for 30 minutes
def monitor_directory(directory_to_watch):  # 1800 seconds = 30 minutes
    log.info(f"Monitoring directory: {directory_to_watch}")
    event_handler = FileChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, path=directory_to_watch, recursive=False)
    observer.start()

    try:
        while True:
            # Calculate time since the last detected event
            time_since_last_event = (datetime.now() - event_handler.last_event_time).total_seconds()

            if event_handler.changes_detected and time_since_last_event >= start_time:
                log.info(f"New file(s) detected and no more new files have been added for {start_time/60} minutes.")
                event_handler.changes_detected = False  # Reset the flag
                return True  # Trigger your processing function

            # Sleep briefly to avoid CPU hogging
            time.sleep(check_time)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()
    log.info("Observer has been stopped and joined.")
    


# Step 3: Count the number of images
def count_images(directory):
    image_extensions = ('.jpg', '.jpeg', '.png', '.tiff', '.bmp')  # Add more if needed
    image_files = [f for f in os.listdir(directory) if f.lower().endswith(image_extensions)]
    log.info(f"Number of images found: {len(image_files)}")
    return len(image_files), image_files


def get_exif_dates(directory, image_files):
    oldest_date = None
    youngest_date = None

    for filename in image_files:
        file_path = os.path.join(directory, filename)
        try:
            img_data = pyexiv2.Image(file_path)
            img_exif = img_data.read_exif()
            if img_exif.get('Exif.Photo.DateTimeOriginal'):
                img_datetime = img_exif.get('Exif.Photo.DateTimeOriginal')
            elif img_exif.get('Exif.Image.DateTime'):
                img_datetime = img_exif.get('Exif.Image.DateTime')
            elif img_exif.get('Exif.Photo.DateTimeDigitized'):
                img_datetime = img_exif.get('Exif.Photo.DateTimeDigitized')
            else:
                img_datetime = None

            if img_datetime:
                image_date = datetime.strptime(img_datetime, "%Y:%m:%d %H:%M:%S")

                if oldest_date is None or image_date < oldest_date:
                    oldest_date = image_date
                if youngest_date is None or image_date > youngest_date:
                    youngest_date = image_date
        except Exception as e:
            log.error(f"Failed to read EXIF data for {filename}: {e}")

    # Convert to string format only if dates were found
    youngest_date_str = youngest_date.strftime("%m:%d:%Y") if youngest_date else None
    oldest_date_str = oldest_date.strftime("%m:%d:%Y") if oldest_date else None

    return youngest_date_str, oldest_date_str

 
def prepend_filenames(directory, image_files):
    log.info("Prepending filenames...")
    for filename in image_files:
        counter = 0
        base, ext = os.path.splitext(filename)
        new_filename = f"digitized_film_{base}{ext}"
        new_file_path = os.path.join(directory, new_filename)

        # Handle naming conflicts
        while os.path.exists(new_file_path):
            counter += 1
            base, ext = os.path.splitext(filename)
            new_filename = f"digitized_film_{base}_{str(counter).zfill(2)}{ext}"
            new_file_path = os.path.join(directory, new_filename)

        try:
            os.rename(os.path.join(directory, filename), new_file_path)
            log.info(f"Renamed {filename} to {new_filename}")
        except Exception as e:
            log.error(f"Failed to rename {filename} to {new_filename}: {e}")
        
def move_failed_to_saved(failed_dir, saved_dir):
    failed_filenames = []
    for filename in os.listdir(failed_dir):
        failed_file_path = os.path.join(failed_dir, filename)
        saved_file_path = os.path.join(saved_dir, filename)
        
        if os.path.isfile(failed_file_path):
            shutil.move(failed_file_path, saved_file_path)
            failed_filenames.append(filename)
            
    return failed_filenames


# Step 6: Trigger Image Organizer and Notify Webhook
def main(directory_to_watch, save_path, error_path, archive_path, WEBHOOK):
    while True:
        # Monitor the directory
        if monitor_directory(directory_to_watch):
            # Count the number of images
            initial_num_images, image_files = count_images(directory_to_watch)
            
            title = "Processing images"
            message = f"Reading date for {initial_num_images} images..."
            response = requests.post(f"https://trigger.macrodroid.com/{WEBHOOK}/universal?title={title}&message={message}")
  
            # create temp save dir
            temp_save_path = os.path.join(save_path, "temp")
            os.makedirs(temp_save_path, exist_ok=True)
            
            if initial_num_images > 0:

                # Call the image organizer script
                image_organizer = ImageOrganizer(
                    save_path=temp_save_path,
                    scans_path=directory_to_watch,
                    error_path=error_path,
                    archive_path=archive_path,
                    archive_scans=True,
                    sort_images=False,
                    fix_orientation=True,
                    crop_images=False,
                    date_images=True,
                    draw_contours=False
                )
                try:
                    run_with_timeout(image_organizer.process_images(), timeout=600)
                except TimeoutError:
                    log.error("Main function timed out after 10 minutes")
                    title = "File Watcher Timeout"
                    message = "The file watcher operation timed out after 10 minutes"
                    response = requests.post(f"https://trigger.macrodroid.com/{WEBHOOK}/universal?title={title}&message={message}")
                    
                
                # get files names and list before adding failed one in
                
                failed_filenames = move_failed_to_saved(error_path, temp_save_path)
                num_failed = len(failed_filenames)
                
                processed_num_images, image_files = count_images(temp_save_path)
                
                # Prepend filenames
                prepend_filenames(temp_save_path, image_files)      
                
                processed_num_images, image_files = count_images(temp_save_path)
                          
                
                processed_num_images
                if processed_num_images > 0:
                    # Read EXIF dates and get the youngest and oldest dates
                    youngest_date, oldest_date = get_exif_dates(temp_save_path, image_files)
                    if youngest_date and oldest_date:
                        log.info(f"Youngest image date: {youngest_date}")
                        log.info(f"Oldest image date: {oldest_date}")
                    else: # No EXIF dates found
                        log.info("No EXIF dates found in the images.")
                        
                    if initial_num_images == processed_num_images:
                        title = "Processed Images Successfully"
                        message = f'''Successfully processed all {processed_num_images} images\nDate range: {oldest_date} - {youngest_date}\nNo errors occurred'''
                    else:
                        title = "Processed Images With Errors"
                        error_list_str = '\n'.join(failed_filenames)
                        message = f'''Processed {processed_num_images} of {initial_num_images} images\nDate range: {oldest_date} - {youngest_date}\n\n{num_failed} images failed to process:\n{error_list_str}'''
                else:
                    log.info("Error No images processed.")
                    title = "Failed To Process Images"
                    message = f'''Processed {processed_num_images} of {initial_num_images} images'''
                
                log.info(f"Sending webhook notification: {title} - {message}")
                # Send POST request to the webhook
                response = requests.post(f"https://trigger.macrodroid.com/{WEBHOOK}/universal?title={title}&message={message}")


                if response.status_code == 200:
                    log.info("Webhook notification sent successfully.")
                else:
                    log.error(f"Failed to send webhook notification: {response.status_code}")
                    
                # move files in temp save dir to actual save dir
                for image_file in image_files:
                    try:
                        source_path = os.path.join(temp_save_path, image_file)
                        final_save_path = os.path.join(save_path, image_file)
                        shutil.move(source_path, final_save_path)
                        log.info(f"Moved scan {image_file} to {final_save_path}")
                    except Exception as e:
                        log.error(f"Failed to move {image_file} to final save directory. Error: {e}")
                        title = "Error moving saved images"
                        message = f"Failed to move saved images out of temp folder:\n{e}"
                        response = requests.post(f"https://trigger.macrodroid.com/{WEBHOOK}/universal?title={title}&message={message}")
  
                    
                num_archive, _ = count_images(archive_path)
                
                if num_archive == processed_num_images:
                    log.info("Deleting old files in archive dir")
                    try:
                        shutil.rmtree(archive_path)
                    except FileNotFoundError:
                        pass
                    except Exception as e:
                        log.error(f"Failed to delete files in archive path: {e}")
                        title = "Error deleting archived images"
                        message = f"Failed to delete with error:\n{e}"
                        response = requests.post(f"https://trigger.macrodroid.com/{WEBHOOK}/universal?title={title}&message={message}")
                else:
                    log.warning(f"{processed_num_images} Processed images and {num_archive} archive images aren't the same amount")
  
                        
                    

        # Continue running without high CPU usage
        time.sleep(check_time)  # Sleep briefly to avoid CPU hogging


if __name__ == "__main__":
    directory_to_watch = r"C:\Users\super\OneDrive\Pictures\test"
    save_path = r"C:\Users\super\OneDrive\Pictures\digitizedfilm\processed"
    error_path = r"C:\Users\super\OneDrive\Pictures\digitizedfilm\failed"
    archive_path = r"C:\Users\super\OneDrive\Pictures\digitizedfilm\archive"
    
    # Check if .env file exists
    if not os.path.isfile('../.env'):
        raise Exception(".env file not found.")

    load_dotenv()
    WEBHOOK = os.getenv('WEBHOOK')

    log.info(f"\n\n------------------------------\nStarting File Watcher\n------------------------------\n")
    try:
        # Run the main function with a 10-minute (600 seconds) timeout
        main(directory_to_watch, save_path, error_path, archive_path, WEBHOOK)

    except Exception as e:
        log.error(f"An error occurred: {e}")
        title = "Error in File Watcher"
        message = f"An error occurred in the file watcher:\n{e}"
        response = requests.post(f"https://trigger.macrodroid.com/{WEBHOOK}/universal?title={title}&message={message}")
