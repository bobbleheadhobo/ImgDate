import cv2
from deepface import DeepFace
import numpy as np
import pickle
from datetime import datetime

# Load profiles
with open(os.path.join(profile_dir, 'profiles.pkl'), 'rb') as f:
    profiles = pickle.load(f)

# Function to estimate the photo date
def estimate_photo_date(birth_year, estimated_age):
    current_year = datetime.now().year
    estimated_year = current_year - estimated_age
    return estimated_year

# Function to update profiles
def update_profiles(profile_name, embedding, age):
    profiles[profile_name]["embeddings"].append(embedding)
    profiles[profile_name]["ages"].append(age)

# Function to process and update image metadata
def process_images(image_folder):
    for filename in os.listdir(image_folder):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            image_path = os.path.join(image_folder, filename)
            try:
                # Analyze the image using DeepFace
                result = DeepFace.analyze(img_path=image_path, actions=['age', 'identity'])

                for analysis in result:
                    person_name = analysis["identity"]
                    if person_name in profiles:
                        embedding = analysis["embedding"]
                        estimated_age = analysis["age"]
                        update_profiles(person_name, embedding, estimated_age)
                        estimated_year = estimate_photo_date(profiles[person_name]["birth_year"], estimated_age)
                        update_image_metadata(image_path, estimated_year)
                    else:
                        print(f"Unknown person in {image_path}")
            except Exception as e:
                print(f"Error processing {image_path}: {e}")

# Function to update image metadata
def update_image_metadata(image_path, estimated_year):
    try:
        exif_dict = piexif.load(image_path)
        date_str = f"{estimated_year}:01:01 00:00:00"
        exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = date_str
        exif_bytes = piexif.dump(exif_dict)
        piexif.insert(exif_bytes, image_path)
        print(f"Updated {image_path} with estimated date {date_str}")
    except Exception as e:
        print(f"Failed to update metadata for {image_path}: {e}")

# Directory containing the images
image_folder = 'path/to/your/image/folder'

# Process the images
process_images(image_folder)

# Save updated profiles
with open(os.path.join(profile_dir, 'profiles.pkl'), 'wb') as f:
    pickle.dump(profiles, f)
