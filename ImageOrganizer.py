import os
from AutoCrop import AutoCrop
import cv2
import random
from concurrent.futures import ThreadPoolExecutor

class ImageOrganizer:
    def __init__(self, folder_path, save_path):
        self.folder_path = folder_path
        self.save_path = save_path
        self.auto_crop = AutoCrop()

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
                    filename = f'{self.save_path}/cropped_image_{idx}_{i}.jpg'
                    cv2.imwrite(filename, img)
                    print(f"Saved: {filename}")

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

if __name__ == "__main__":
    # Example usage
    folder_path = r"img\test"
    save_path = r"img\processed"

    # Delete files in save path folder
    file_list = os.listdir(save_path)
    for file_name in file_list:
        file_path = os.path.join(save_path, file_name)
        if os.path.isfile(file_path):
            os.remove(file_path)

    image_organizer = ImageOrganizer(folder_path, save_path)
    image_organizer.process_images()
