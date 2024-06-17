import datetime
import os
import shutil
import numpy as np
import cv2
import random
import calendar
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
import pyexiv2
from AutoCrop import AutoCrop
from DateExtractor import DateExtractor
from LoggerConfig import setup_logger

class ImageOrganizer:
    def __init__(self, scans_path=r"..\img\unprocessed", save_path=r"..\img\processed", error_path=r"..\img\processed\Failed"):
        self.scans_path = scans_path
        self.save_path = save_path
        self.error_path = error_path
        self.num_images = 0
        self.current_image_num = 0
        self.auto_crop = AutoCrop()
        self.date_extractor = DateExtractor()
        self.log = setup_logger("ImageOrganizer", "..\log\ImgDate.log")

        os.makedirs(save_path, exist_ok=True)
        os.makedirs(error_path, exist_ok=True)

    def process_images(self):
        scan_file_paths = self.get_scan_file_paths()
        self.log.info(f"Found {len(scan_file_paths)} {'scan' if len(scan_file_paths) == 1 else 'scans'} to process.")


        with ThreadPoolExecutor(max_workers=10) as executor:  # Adjust number of workers as needed
            results = list(executor.map(self.process_single_scan, scan_file_paths))
        
        # Save images in parallel
        for cropped_images in results:
            if cropped_images:
                for img in cropped_images:
                    date = "01/01/1985"  # Dummy date, replace with actual logic if needed
                    confidence = random.randint(-1, 20)  # Dummy confidence, replace with actual logic
                    # date, confidence = self.date_extractor.extract_and_validate_date(img)
                    self.save_image(img, date, confidence)

    def get_scan_file_paths(self):
        image_files = []
        for file in os.listdir(self.scans_path):
            if file.endswith(".jpg"):
                image_files.append(os.path.join(self.scans_path, file))
        return image_files

    def process_single_scan(self, scan_path):
        self.log.info(f"Cropping: {scan_path}")
        cropped_images = self.auto_crop.crop_and_straighten(scan_path)
        self.num_images += len(cropped_images)
        return cropped_images
    
    def update_metadata_and_save(self, img, date, filename):
        """
        Update the image metadata with the extracted date in the format mm/dd/yyyy and save to file.
        """
        # Convert the numpy array (OpenCV format) to a PIL Image
        pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

        # Save PIL image to disk temporarily
        temp_filename = 'temp_image.jpg'
        pil_img.save(temp_filename, format="JPEG")

        try:
            # Load the image file with pyexiv2
            img_data = pyexiv2.Image(temp_filename)
            img_data.read_exif()

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
                

            # Update the DateTimeOriginal (Date Taken), DateTime (Date Modified), and DateTimeDigitized (Date Created) fields
            exif_tags = {
                'Exif.Photo.DateTimeOriginal': date_formatted,   # Date Taken
                'Exif.Image.DateTime': date_formatted,           # Date Modified
                'Exif.Photo.DateTimeDigitized': date_formatted   # Date Created

            }
            img_data.modify_exif(exif_tags)

            img_data.modify_comment(f"Scanned: {date_formatted}")
            img_data.modify_exif({'Exif.Photo.DateTimeOriginal': date_formatted})


            img_data.modify_comment(f"Scanned photo: {current_date} {current_time}")

            self.log.info(f"Updated exif date to {date_formatted}")
        finally:
            img_data.close()

        # Rename the temp file to the final filename
        os.rename(temp_filename, filename)

        #check if success
        return os.path.exists(filename)



    def save_image(self, img, date, confidence):
        """
        Save the image with the extracted date in the filename and update metadata.
        """
        filename = self.generate_filename(date, confidence)
        success = self.update_metadata_and_save(img, date, filename)
        if success is not None:
            self.log.info(f"Saved image to {filename}")
        else:
            self.log.error(f"Failed to update metadata or save image: {filename}")

        self.current_image_num += 1
        self.log.info(f"Image {self.current_image_num} of {self.num_images} processed\n")
        return success


    def generate_filename(self, date, confidence):
        """
        Generate a filename based on the date and confidence.
        """
        random_number = random.randint(1000, 9999)

        if date is not None:
            formatted_date = date.replace('/', '-')
            if confidence < 9:
                return rf"{self.error_path}\{self.current_image_num}_date_{formatted_date}_confidence-{confidence}_{random_number}.jpg"
            
            year, month_name = self.extract_year_month(date)
            self.ensure_directories_exist(year, month_name)
            return rf"{self.save_path}\{year}\{month_name}\{self.current_image_num}_date_{formatted_date}_{random_number}.jpg"
        else:
            return rf"{self.error_path}\{self.current_image_num}_date_not_found_{random_number}.jpg"

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

    def save_file(self, img, filename):
        """
        Save the image file to the specified filename.
        """
        # Check if img is a byte string and decode it to a numpy array if needed
        if isinstance(img, bytes):
            img_array = np.frombuffer(img, dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        # Ensure the image is C-contiguous
        if isinstance(img, np.ndarray):
            img = np.ascontiguousarray(img)
        
        # Encode the image as JPEG before saving
        success, encoded_img = cv2.imencode('.jpg', img)
        if not success:
            self.log.error(f"Failed to encode image")
            return

        with open(filename, 'wb') as f:
            f.write(encoded_img.tobytes())
        
        if os.path.exists(filename):
            self.log.info(f"Saved image to {filename}")
        else:
            self.log.error(f"Error saving image to {filename}")



if __name__ == "__main__":
    # Example usage
    scans_path = r"..\img\test\New folder"
    save_path = r"..\img\processed"
    error_path = rf"{save_path}\Failed"

    # Delete files and folders in save path directory recursively
    shutil.rmtree(save_path)
    os.makedirs(save_path)

    image_organizer = ImageOrganizer(scans_path, save_path, error_path)
    image_organizer.process_images()
