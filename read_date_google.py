import os
from google.cloud import vision
from google.cloud.vision_v1 import types
from PIL import Image
import piexif

def detect_text_google_cloud(image_path):
    # Initialize the Vision API client
    client = vision.ImageAnnotatorClient()

    # Read the image file
    with open(image_path, 'rb') as image_file:
        content = image_file.read()

    image = vision.Image(content=content)
    
    # Perform text detection
    response = client.text_detection(image=image)
    texts = response.text_annotations
    
    if texts:
        return texts[0].description.strip()
    return None

def extract_date_from_text(text):
    import re
    # Extract the date using regex
    match = re.search(r'(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})', text)
    if match:
        day, month, year = match.groups()
        if len(year) == 2:
            year = '20' + year if int(year) < 50 else '19' + year  # Handling Y2K
        return f"{year}:{month.zfill(2)}:{day.zfill(2)} 00:00:00"
    return None

def update_image_metadata(image_path, date):
    # Read image
    img = Image.open(image_path)
    
    # Load existing EXIF data
    exif_dict = piexif.load(img.info['exif'])
    
    # Update the DateTimeOriginal field
    exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = date
    
    # Save the updated EXIF data back to the image
    exif_bytes = piexif.dump(exif_dict)
    piexif.insert(exif_bytes, image_path)
    print(f"Updated {image_path} with date {date}")

# Example usage
image_path = '/mnt/data/image.png'
text = detect_text_google_cloud(image_path)
if text:
    date = extract_date_from_text(text)
    if date:
        update_image_metadata(image_path, date)
    else:
        print("No valid date found in the text")
else:
    print("No text found in the image")
