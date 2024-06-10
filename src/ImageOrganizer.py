import io
import os
from AutoCrop import AutoCrop
import cv2
import random
import piexif
import calendar
from PIL import Image
from concurrent.futures import ThreadPoolExecutor
from DateExtractor import DateExtractor

class ImageOrganizer:
    def __init__(self, scans_path, save_path, error_path):
        self.scans_path = scans_path
        self.save_path = save_path
        self.error_path = error_path
        self.auto_crop = AutoCrop()
        self.date_extractor = DateExtractor()

        if not os.path.exists(save_path):
            os.makedirs(save_path)

        if not os.path.exists(error_path):
            os.makedirs(error_path)

    def process_images(self):
        scan_file_paths = self.get_scan_file_paths()

        # Process images in parallel
        with ThreadPoolExecutor() as executor:
            results = list(executor.map(self.process_single_image, scan_file_paths))
        
        # Flatten the list of lists and save images
        for idx, cropped_images in enumerate(results):
            if cropped_images:
                for i, img in enumerate(cropped_images):
                    # filename = f'{self.save_path}/cropped_image_{idx}_{i}.jpg'
                    # cv2.imwrite(filename, img)
                    # print(f"Saved: {filename}")
                    date, confidence = self.date_extractor.extract_and_validate_date(img)
                    # date = "12/07/2001"
                    # confidence = 9
                    if date:
                        img = self.update_image_metadata(img, date)

                    self.save_image(img, date, confidence)



    def get_scan_file_paths(self):
        image_files = []
        for file in os.listdir(self.scans_path):
            if file.endswith(".jpg"):
                image_files.append(os.path.join(self.scans_path, file))
        return image_files

    def process_single_image(self, image_path):
        print(f"Processing: {image_path}")
        cropped_images = self.auto_crop.crop_and_straighten(image_path)
        return cropped_images
    
    def update_image_metadata(self, img, date):
        """
        Update the image metadata with the extracted date in the format mm/dd/yyyy.
        """
        # Convert the numpy array (OpenCV format) to a PIL Image
        pil_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))

        # Convert the date to EXIF format "YYYY:MM:DD HH:MM:SS"
        try:
            month, day, year = date.split('/')
            date_formatted = f"{year}:{month.zfill(2)}:{day.zfill(2)} 12:00:00"  # Padding month and day with zeros
        except ValueError:
            print(f"Error in date format: {date}. Expected format is mm/dd/yyyy.")
            return None

        # Save to a BytesIO stream to keep it in memory
        with io.BytesIO() as output:
            pil_img.save(output, format="JPEG")
            image_bytes = output.getvalue()

        # Load the EXIF data into piexif
        exif_dict = piexif.load(image_bytes)

        # Update the DateTimeOriginal field with the formatted date
        exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = date_formatted.encode('utf-8')

        # Save the updated EXIF data back to the image
        exif_bytes = piexif.dump(exif_dict)

        # Save to another BytesIO stream to keep it in memory
        with io.BytesIO() as updated_output:
            pil_img.save(updated_output, format="JPEG", exif=exif_bytes)
            updated_image_bytes = updated_output.getvalue()

        print(f"Updated image exif date: {date}")

        return updated_image_bytes
    
    def save_image(self, img, date, confidence):
        """
        Save the image with the extracted date in the filename.
        """
        # Generate a random number to avoid overwriting existing files
        random_number = random.randint(1000, 9999)

        if date:
            # Get the year and month from the date
            month, _, year = date.split('/')

            month_name = calendar.month_name[int(month)]

            # Create the year folder if it doesn't exist
            year_folder = os.path.join(self.save_path, year)
            if not os.path.exists(year_folder):
                os.makedirs(year_folder)

            # Create the month folder if it doesn't exist
            month_folder = os.path.join(year_folder, month_name)
            if not os.path.exists(month_folder):
                os.makedirs(month_folder)

            if confidence < 9:
                # Likely incorrect date
                filename = rf"{self.save_path}\Failed\date_{date.replace('/', '-')}_confidence-{confidence}_{random_number}.jpg"
            else:
                filename = rf"{self.save_path}\{year}\{month_name}\date_{date.replace('/', '-')}_{random_number}.jpg"

        else:
            # No date found
            filename = rf"{self.save_path}\Failed\date_not_found_{random_number}.jpg"

        with open(filename, 'wb') as f:
            f.write(img)

        # Verify if the file was saved
        if os.path.exists(filename):
            print(f"Saved image with date {date} to {filename}")
        else:
            print(f"Error saving image with date {date} to {filename}")

if __name__ == "__main__":
    # Example usage
    scans_path = r"..\img\test\New folder"
    save_path = r"..\img\processed"
    error_path = rf"{save_path}\Failed"

    # Delete files and folders in save path directory recursively
    for root, dirs, files in os.walk(save_path):
        for file in files:
            file_path = os.path.join(root, file)
            os.remove(file_path)
        for dir in dirs:
            dir_path = os.path.join(root, dir)
            os.rmdir(dir_path)
    # file_list = os.listdir(save_path)
    # for file_name in file_list:
    #     file_path = os.path.join(save_path, file_name)
    #     if os.path.isfile(file_path):
    #         os.remove(file_path)

    image_organizer = ImageOrganizer(scans_path, save_path, error_path)
    image_organizer.process_images()
