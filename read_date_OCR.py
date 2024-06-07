import cv2
import pytesseract
import numpy as np
import re
from PIL import Image
import piexif

# Path to Tesseract OCR
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def hex_to_hsv(hex_color):
    # Convert hex to RGB
    h = hex_color.lstrip('#')
    rgb = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    # Convert RGB to HSV
    rgb = np.uint8([[list(rgb)]])
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    return hsv[0][0]

def extract_date(image_path):
    # Read image
    img = cv2.imread(image_path)
    
    # Crop the bottom right corner where the date is located
    h, w, _ = img.shape
    crop_img = img[int(h*0.75):h, int(w*0.7):w]
    
    # Define precise color ranges for orange in HSV
    lower_orange_hex = '#be6a3d'
    upper_orange_hex = '#f7cf07'
    
    lower_orange_hsv = hex_to_hsv(lower_orange_hex)
    upper_orange_hsv = hex_to_hsv(upper_orange_hex)
    
    # Convert to HSV to filter the orange color
    hsv = cv2.cvtColor(crop_img, cv2.COLOR_BGR2HSV)
    
    # Create a mask for the orange color
    mask = cv2.inRange(hsv, lower_orange_hsv, upper_orange_hsv)
    res = cv2.bitwise_and(crop_img, crop_img, mask=mask)
    
    # Convert to grayscale
    gray = cv2.cvtColor(res, cv2.COLOR_BGR2GRAY)
    
    # Enhance the contrast
    gray = cv2.equalizeHist(gray)
    
    # Apply morphological operations to remove noise and enhance the text
    kernel = np.ones((3, 3), np.uint8)
    gray = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
    
    # Apply dilation and erosion to make the text more distinct
    gray = cv2.dilate(gray, kernel, iterations=1)
    gray = cv2.erode(gray, kernel, iterations=1)
    
    # Apply additional filtering
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    
    # Try different thresholding methods
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Find contours and filter out small ones
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    mask = np.zeros_like(binary)
    for contour in contours:
        if cv2.contourArea(contour) > 10:  # You might need to adjust this threshold
            cv2.drawContours(mask, [contour], -1, 255, -1)
    
    preview_image(mask)
    
    # Use pytesseract to extract text
    config = '--psm 7'  # Assume a single line of text
    text = pytesseract.image_to_string(mask, config=config)
    print(f"Extracted text: {text}")
    
    # Extract the date using regex
    match = re.search(r'(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})', text)
    if match:
        day, month, year = match.groups()
        if len(year) == 2:
            year = '20' + year if int(year) < 50 else '19' + year  # Handling Y2K
        return f"{year}:{month.zfill(2)}:{day.zfill(2)} 00:00:00"
    return None


def preview_image(img):
    # Display the image
    cv2.imshow("Image Preview", img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

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
image_path = 'img/test.png'
date = extract_date(image_path)
if date:
    update_image_metadata(image_path, date)
else:
    print("No date found in the image")
