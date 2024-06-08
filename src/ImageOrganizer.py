import io
import os
from AutoCrop import AutoCrop
import cv2
import random
import piexif
from PIL import Image
from concurrent.futures import ThreadPoolExecutor
from DateExtractor import DateExtractor

class ImageOrganizer:
    def __init__(self, folder_path, save_path):
        self.folder_path = folder_path
        self.save_path = save_path
        self.auto_crop = AutoCrop()
        self.date_extractor = DateExtractor()

        if not os.path.exists(save_path):
            os.makedirs(save_path)

    def process_images(self):
        image_files = self.get_image_files()

        # Process images in parallel
        with ThreadPoolExecutor() as executor:
            results = list(executor.map(self.process_single_image, image_files))
        
        # Flatten the list of lists and save images
        for idx, cropped_images in enumerate(results):
            if cropped_images:
                for i, img in enumerate(cropped_images):
                    # filename = f'{self.save_path}/cropped_image_{idx}_{i}.jpg'
                    # cv2.imwrite(filename, img)
                    # print(f"Saved: {filename}")
                    # date = self.date_extractor.extract_and_validate_date(img)
                    date = "12/07/2001"
                    self.update_image_metadata(img, date)



    def get_image_files(self):
        image_files = []
        for file in os.listdir(self.folder_path):
            if file.endswith(".jpg"):
                image_files.append(os.path.join(self.folder_path, file))
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
            date_formatted = f"{year}:{month.zfill(2)}:{day.zfill(2)} 00:00:00"  # Padding month and day with zeros
        except ValueError:
            print(f"Error in date format: {date}. Expected format is mm/dd/yyyy.")
            return

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

        # Optionally, write the updated image back to disk
        updated_image_path = f"../img/processed/updated_image{random.randint(10,1000)}.jpg"
        with open(updated_image_path, 'wb') as file:
            file.write(updated_image_bytes)

        print(f"Updated image saved with date {date} to {updated_image_path}")


if __name__ == "__main__":
    # Example usage
    folder_path = r"..\img\test\New folder"
    save_path = r"..\img\processed"

    # Delete files in save path folder
    file_list = os.listdir(save_path)
    for file_name in file_list:
        file_path = os.path.join(save_path, file_name)
        if os.path.isfile(file_path):
            os.remove(file_path)

    image_organizer = ImageOrganizer(folder_path, save_path)
    image_organizer.process_images()
