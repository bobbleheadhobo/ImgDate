import io
import os
import shutil
import numpy as np
import cv2
import random
import piexif
import calendar
from concurrent.futures import ThreadPoolExecutor
from AutoCrop import AutoCrop
from DateExtractor import DateExtractor

class ImageOrganizer:
    def __init__(self, scans_path, save_path, error_path):
        self.scans_path = scans_path
        self.save_path = save_path
        self.error_path = error_path
        self.num_images = 0
        self.current_image = 0
        self.auto_crop = AutoCrop()
        self.date_extractor = DateExtractor()

        if not os.path.exists(save_path):
            os.makedirs(save_path)

        if not os.path.exists(error_path):
            os.makedirs(error_path)

    def process_images(self):
        scan_file_paths = self.get_scan_file_paths()
        print(f"Found {len(scan_file_paths)} scans to process.")

        # Process images in parallel
        with ThreadPoolExecutor() as executor:
            results = list(executor.map(self.process_single_scan, scan_file_paths))
        
        # Flatten the list of lists and save images
        for idx, cropped_images in enumerate(results):
            if cropped_images:
                for i, img in enumerate(cropped_images):
                    filename = f'{self.save_path}/cropped_image_{self.current_image}.jpg'
                    cv2.imwrite(filename, img)
                    date, confidence = self.date_extractor.extract_and_validate_date(img)

                    if date is not None and confidence >= 0:
                        img = self.update_image_metadata(img, date)
                    self.save_image(img, date, confidence)

    def get_scan_file_paths(self):
        image_files = []
        for file in os.listdir(self.scans_path):
            if file.endswith(".jpg"):
                image_files.append(os.path.join(self.scans_path, file))
        return image_files

    def process_single_scan(self, scan_path):
        print(f"Processing: {scan_path}")
        cropped_images = self.auto_crop.crop_and_straighten(scan_path)
        self.num_images += len(cropped_images)
        return cropped_images
    
    def update_image_metadata(self, img, date):
        """
        Update the image metadata with the extracted date in the format mm/dd/yyyy.
        """
        try:
            month, day, year = date.split('/')
            date_formatted = f"{year}:{month.zfill(2)}:{day.zfill(2)} 12:00:00"  # Padding month and day with zeros
        except ValueError:
            print(f"Error in date format: {date}. Expected format is mm/dd/yyyy.")
            return None

        # Encode the image as a JPEG
        success, encoded_img = cv2.imencode('.jpg', img)
        if not success:
            print(f"Failed to encode image")
            return None

        # Load the EXIF data into piexif
        exif_dict = piexif.load(encoded_img.tobytes())

        # Update the DateTimeOriginal field with the formatted date
        exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = date_formatted.encode('utf-8')

        # Save the updated EXIF data back to the image
        exif_bytes = piexif.dump(exif_dict)

        # Use BytesIO to handle the image bytes
        with io.BytesIO() as output:
            piexif.insert(exif_bytes, encoded_img.tobytes(), output)
            updated_image_bytes = output.getvalue()

        print(f"Updated image exif date: {date}")

        return updated_image_bytes
    
    def save_image(self, img, date, confidence):
        """
        Save the image with the extracted date in the filename.
        """
        filename = self.generate_filename(date, confidence)
        self.save_file(img, filename)
        self.current_image += 1
        print(f"Image {self.current_image} of {self.num_images} processed\n")

    def generate_filename(self, date, confidence):
        """
        Generate a filename based on the date and confidence.
        """
        random_number = random.randint(1000, 9999)

        if date is not None:
            formatted_date = date.replace('/', '-')
            if confidence < 9:
                return rf"{self.save_path}\Failed\{self.current_image}_date_{formatted_date}_confidence-{confidence}_{random_number}.jpg"
            
            year, month_name = self.extract_year_month(date)
            self.ensure_directories_exist(year, month_name)
            return rf"{self.save_path}\{year}\{month_name}\{self.current_image}_date_{formatted_date}_{random_number}.jpg"
        else:
            return rf"{self.save_path}\Failed\{self.current_image}_date_not_found_{random_number}.jpg"

    def extract_year_month(self, date):
        """
        Extract year and month name from the date.
        """
        month, _, year = date.split('/')
        month_name = calendar.month_name[int(month)]
        return year, month_name

    def ensure_directories_exist(self, year, month_name):
        """
        Ensure the year and month directories exist.
        """
        year_folder = os.path.join(self.save_path, year)
        if not os.path.exists(year_folder):
            os.makedirs(year_folder)

        month_folder = os.path.join(year_folder, month_name)
        if not os.path.exists(month_folder):
            os.makedirs(month_folder)

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
            print(f"Failed to encode image")
            return

        with open(filename, 'wb') as f:
            f.write(encoded_img.tobytes())
        
        if os.path.exists(filename):
            print(f"Saved image to {filename}")
        else:
            print(f"Error saving image to {filename}")

if __name__ == "__main__":
    # Example usage
    scans_path = r"..\img\test"
    save_path = r"..\img\processed"
    error_path = rf"{save_path}\Failed"

    # Delete files and folders in save path directory recursively
    shutil.rmtree(save_path)
    os.makedirs(save_path)

    image_organizer = ImageOrganizer(scans_path, save_path, error_path)
    image_organizer.process_images()
