import datetime
import os
import re
import shutil
import cv2
import calendar
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image
import pyexiv2
from threading import Lock
from AutoCrop import AutoCrop
from DateExtractor import DateExtractor
from FixOrientation import FixOrientation
from LoggerConfig import setup_logger
import SharedVariables as shared

class ImageOrganizer:
    def __init__(self, scans_path=r"..\img\unprocessed", save_path=r"..\img\processed", error_path=r"..\img\processed\Failed", archive_path=r"..\img\archive", crop_images = True, date_images = True, fix_orientation = True, archive_scans = True, sort_images = True, draw_contours = False):
        self.scans_path = scans_path
        self.save_path = save_path
        self.error_path = error_path
        self.archive_path = archive_path
        self.archive_scans = archive_scans
        self.crop_images = crop_images
        self.date_images = date_images
        self.fix_orientation = fix_orientation
        self.sort_images = sort_images
        self.auto_crop = AutoCrop(scans_path, draw_contours)
        self.date_extractor = DateExtractor()

        self.s = shared
        self.s.num_images = 0
        self.s.current_image_num = 0

        self.lock = Lock()  # For thread safety
        self.log = setup_logger("ImageOrganizer", "..\log\ImgDate.log")

        os.makedirs(save_path, exist_ok=True)
        os.makedirs(error_path, exist_ok=True)
        os.makedirs(archive_path, exist_ok=True)

    def process_images(self):
        scan_file_paths = self.get_scan_file_paths()
        if self.crop_images:
            self.log.info(f"Found {len(scan_file_paths)} {'scan' if len(scan_file_paths) == 1 else 'scans'} to process.")
        else:
            self.log.info(f"Found {len(scan_file_paths)} {'image' if len(scan_file_paths) == 1 else 'images'} to process.")
            self.s.num_images = len(scan_file_paths)
            
            

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = []
            for scan_path in scan_file_paths:
                futures.append(executor.submit(self.crop_and_save_scans, scan_path))

            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    self.log.error(f"Error processing scan: {e}")

    def crop_and_save_scans(self, scan_path):
        scan = self.load_scan(scan_path)
        original_filename = os.path.basename(scan_path)  # Get the original filename
        try:
            if self.crop_images:
                # crop scan into a list of images
                self.log.info(f"Cropping: {scan_path}")
                cropped_images = self.crop_single_scan(scan)
            else:
                # each scan here is an individual image
                scan = self.auto_crop.make_landscape(scan)
                cropped_images = [scan]

            if cropped_images:
                orientation = FixOrientation() if self.fix_orientation else None
                for img in cropped_images:
                    if self.date_images:
                        # date = "01/01/1985"  # Dummy date, replace with actual logic if needed
                        # confidence = random.randint(-1, 20)  # Dummy confidence, replace with actual logic
                        date, confidence = self.date_extractor.extract_and_validate_date(img)
                        original_exif_data = None
                    else:
                        confidence = 10
                        date = "01/01/1111" # place holder date wont actually be used
                        original_exif_data = self.date_extractor.read_image_date(scan_path)


                    if self.fix_orientation and confidence > 8:
                        try:
                            img = orientation.process_image(img)
                        except Exception as e:
                            self.log.error(f"Error in FixOrientation: {e}")

                    self.save_image(img, date, confidence, original_filename, original_exif_data)


            if self.archive_scans:
                self.move_scan_to_archive(scan_path)
        except Exception as e:
            self.log.error(f"Error processing {scan_path}: {e}")


    def move_scan_to_archive(self, scan_path):
        """
        Move the scan file to the archive folder after processing.
        """
        try:  
            archive_scan_path = os.path.join(self.archive_path, os.path.basename(scan_path))
            shutil.move(scan_path, archive_scan_path)
            self.log.info(f"Moved scan {scan_path} to {archive_scan_path}")
        except Exception as e:
            self.log.error(f"Failed to move {scan_path} to archive. Error: {e}")


    def get_scan_file_paths(self):
        image_files = []
        image_extensions = ('.jpg', '.jpeg', '.png', '.tiff')
        for file in os.listdir(self.scans_path):
            if file.lower().endswith(image_extensions):
                image_files.append(os.path.join(self.scans_path, file))
        return image_files

    def crop_single_scan(self, scan):
        cropped_images = self.auto_crop.crop_and_straighten(scan)
        with self.lock:
            self.s.num_images += len(cropped_images)
        return cropped_images
    
    def load_scan(self, scan_path):
        image = cv2.imread(scan_path)
        if image is None:
            self.log.error(f"Could not load image: {scan_path}")
            return None
        
        return image
    
    def update_metadata_and_save(self, img, date, filename, original_exif_data):
        """
        Update the image metadata with the extracted date in the format mm/dd/yyyy and save to file.
        """
        # Convert the numpy array (OpenCV format) to a PIL Image
        pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

        # Save PIL image with temp filename
        temp_filename = 'temp_image.jpg'
        pil_img.save(temp_filename, format="JPEG", quality=95)

        img_data = None
        try:
            # Load the image file with pyexiv2
            img_data = pyexiv2.Image(temp_filename)
            # img_data.read_exif()

            # get current date and time
            current_datetime = datetime.datetime.now()
            current_date = current_datetime.strftime("%m/%d/%Y")
            current_time = current_datetime.strftime("%H:%M:%S")


            # Convert the date to EXIF format "YYYY:MM:DD HH:MM:SS"
            try:
                month, day, year = date.split('/')
                date_formatted = f"{year}:{month.zfill(2)}:{day.zfill(2)} 12:00:00"  # Padding month and day with zeros
            except Exception as e:
                date_formatted = f"{current_date} {current_time}"
                self.log.error(f"Error in date format: {date}. Expected format is mm/dd/yyyy.")
                self.log.error(f"Defaulting to current date: {date_formatted}")
                
            #if not dating images, save the original date and time back to the image
            if not self.date_images and original_exif_data is not None:
                exif_tags = {
                    'Exif.Photo.DateTimeOriginal': original_exif_data["DateTimeOriginal"],   # Date Taken
                    'Exif.Image.DateTime': original_exif_data["DateTime"],                   # Date Modified
                    'Exif.Photo.DateTimeDigitized': original_exif_data["DateTimeDigitized"]  # Date Created
                }
                
            else:
                # Update the DateTimeOriginal (Date Taken), DateTime (Date Modified), and DateTimeDigitized (Date Created) fields
                exif_tags = {
                    'Exif.Photo.DateTimeOriginal': date_formatted,   # Date Taken
                    'Exif.Image.DateTime': date_formatted,           # Date Modified
                    'Exif.Photo.DateTimeDigitized': date_formatted   # Date Created
                }
                
            if original_exif_data and original_exif_data.get('comment'):
                img_data.modify_comment(f"{original_exif_data['comment']}     Re-processed Image: {current_date} {current_time}")
            else:
                img_data.modify_comment(f"Processed Image: {current_date} {current_time}")
                    
            img_data.modify_exif(exif_tags)

            try:
                img_exif = img_data.read_exif()
                if img_exif.get('Exif.Photo.DateTimeOriginal'):
                    updated_date = img_exif.get('Exif.Photo.DateTimeOriginal')
                elif img_exif.get('Exif.Image.DateTime'):
                    updated_date = img_exif.get('Exif.Image.DateTime')
                elif img_exif.get('Exif.Photo.DateTimeDigitized'):
                    updated_date = img_exif.get('Exif.Photo.DateTimeDigitized')
                else:
                    updated_date = "Unknown"
            except Exception as e:
                self.log.error(f"Error reading updated date from exif data: {e}")
                updated_date = "Unknown"

            if self.date_images:
                self.log.info(f"Updated exif date to {updated_date}")
            else:
                self.log.info(f"Kept original exif data")
        finally:
            img_data.close()

        # Rename the temporary file to the final filename
        try:
            os.rename(temp_filename, filename)
        except FileNotFoundError:
            self.log.error(f"The file {temp_filename} does not exist. Cannot rename to {filename}.")
            return False
        except PermissionError:
            self.log.error(f"Permission denied when trying to rename {temp_filename} to {filename}.")
            return False
        except Exception as e:
            self.log.error(f"An unexpected error occurred while renaming {temp_filename} to {filename}: {e}")
            return False

        #check if success
        return os.path.exists(filename)



    def save_image(self, img, date, confidence, original_filename, original_exif_data):
        """
        Save the image with the extracted date in the filename and update metadata.
        """
        with self.lock:
            filename = self.generate_filename(date, confidence, original_filename)
            success = self.update_metadata_and_save(img, date, filename, original_exif_data)
            if success:
                self.log.info(f"Saved image to {filename}")
            else:
                self.log.error(f"Failed to update metadata or save image: {filename}")

            self.s.current_image_num += 1
            self.log.info(f"Image {self.s.current_image_num} of {self.s.num_images} processed\n")
            return success


    def generate_filename(self, date, confidence, original_filename):
        """
        Generate a filename based on the date and confidence.
        """

        if date is not None:
            formatted_date = date.replace('/', '-')
            if confidence < 9:
                file_path = rf"{self.error_path}\date_{formatted_date}_confidence-{confidence}.jpg"
                self.log.warning(f"Low confidence ({confidence}) for date {date}. Saving to failed location")
                return self.duplicate_check(file_path)
            
            if self.sort_images:
                year, month_name = self.extract_year_month(date)
                self.ensure_directories_exist(year, month_name)
                if self.date_images:
                    file_path = rf"{self.save_path}\{year}\{month_name}\date_{formatted_date}.jpg"
                    return self.duplicate_check(file_path)
                else:
                    filepath = rf"{self.save_path}\{year}\{month_name}\{original_filename}"
                    return self.duplicate_check(filepath)
            
            # Not sorting images
            else:
                if self.date_images:
                    file_path = rf"{self.save_path}\date_{formatted_date}.jpg"
                    return self.duplicate_check(file_path)
                else:
                    file_path = rf"{self.save_path}\{original_filename}"
                    return self.duplicate_check(file_path)
        else:
            file_path = rf"{self.error_path}\date_not_found.jpg"
            return self.duplicate_check(file_path)
        
    def  duplicate_check(self, file_path):
        """
        Check if the filename already exists in the save path and adjust the name to avoid overwriting.
        Handles filenames like 'date_02-01-2000.jpg', 'date_07-11-1997_confidence-8.jpg', and 'date_not_found.jpg'.
        """
        path, filename = os.path.split(file_path)
        base_name, extension = os.path.splitext(filename)
        duplicate = 0
        
        # Regular expression to match different parts of the file name
        match = re.match(r"(date_)(\d{2}-\d{2}-\d{4})?(_confidence-\d+)?", base_name)
        if match:
            prefix = match.group(1)
            date = match.group(2) if match.group(2) else "not_found"
            confidence = match.group(3) if match.group(3) else ""
            
            # Construct the initial file path
            new_filename = f"{prefix}{date}{confidence}_{str(duplicate).zfill(2)}{extension}"
            new_file_path = os.path.join(path, new_filename)
            
            # Increment the duplicate counter if the file exists
            while os.path.exists(new_file_path):
                duplicate += 1
                new_filename = f"{prefix}{date}{confidence}_{str(duplicate).zfill(2)}{extension}"
                new_file_path = os.path.join(path, new_filename)
        else:
            match = re.match(r"(.+)(_\d{2})", base_name)
            # If the filename does not match the expected pattern add duplicate counter
            if match:
                base_name = match.group(1)
                duplicate = int(match.group(2)[1:])
                new_filename = f"{base_name}_{str(duplicate).zfill(2)}{extension}"
                new_file_path = os.path.join(path, new_filename)
            
            else:
                new_filename = f"{base_name}_{str(duplicate).zfill(2)}{extension}"
                new_file_path = os.path.join(path, new_filename)
                
            while os.path.exists(new_file_path):
                duplicate += 1
                new_filename = f"{base_name}_{str(duplicate).zfill(2)}{extension}"
                new_file_path = os.path.join(path, new_filename)
                
                
        return new_file_path

    def extract_year_month(self, date):
        """
        Extract year and month name from the date.
        """
        month, _, year = date.split('/')
        month_name = calendar.month_name[int(month)]
        return year, month_name

    def ensure_directories_exist(self, year, month_name):
        year_folder = os.path.join(self.save_path, year)
        month_folder = os.path.join(year_folder, month_name)
        os.makedirs(month_folder, exist_ok=True)



if __name__ == "__main__":
    # Example usage
    scans_path = r"..\img\test\skewed"
    save_path = r"..\img\processed"
    error_path = rf"{save_path}\Failed"

    # Delete files and folders in save path directory recursively
    shutil.rmtree(save_path)
    os.makedirs(save_path)

    image_organizer = ImageOrganizer(scans_path, save_path, error_path)
    image_organizer.process_images()
