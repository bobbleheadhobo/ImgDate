import base64
import datetime
from time import sleep
import cv2
import re
import os
from dotenv import load_dotenv
import pyexiv2
from LoggerConfig import setup_logger

import requests

class DateExtractor:

    def __init__(self):
        self.crop_height = 0.8
        self.crop_width = 0.70
        load_dotenv()
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.log = setup_logger("DateExtractor", "..\log\ImgDate.log")
        self.MIN_YEAR = 1985

    def crop_date_64(self, img, base_64 = True):
        """
        Crop the bottom right corner of the image where the date is located.
        Converts to base64 and returns the cropped image.
        """
        # Crop the bottom right corner
        h, w, _ = img.shape
        # cv2.rectangle(img, (int(w*self.crop_width), int(h*self.crop_height)), (w, h), (0, 255, 0), 5)
        cropped_img = img[int(h*self.crop_height):h, int(w*self.crop_width):w]
        
        if base_64:
            _, buffer = cv2.imencode('.jpg', cropped_img)


            # Convert the cropped image to base64
            cropped_img = base64.b64encode(buffer).decode('utf-8')

        # # Debug Optional: Save the processed image for debugging
        # cv2.imwrite(f"../img/processed/date_{random.randint(1, 100)}.jpg", cropped_img)

        # return base64_img
        return cropped_img

    def read_date(self, base64_image, retries = 3):
        """
        Use gpt4o API to extract text from the processed image.
        """

        headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
        "model": "gpt-4o",
        "messages": [
            {
            "role": "user",
            "content": [
                {
                "type": "text",
                "text": "This is a film image that contains a date, typically in orange or red text. This image has been cropped down to enlarge the text size. The date will be in the format 'YY MM DD. A way to differentiate the two dates is that the year will always start an apostrophe. Please read the date and provide it in the format MM DD \'YY. Respond only with the date and a confidence level from 1 to 10 on how certain you are of its accuracy. Example \"12 07 \'01 | confidence: 10\". If the date is unclear or cannot be read, please respond with not found | confidence: -1\" as a placeholder."
                },
                {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_image}",
                    "detail": "low"
                }
                }
            ]
            }
        ],
        "max_tokens": 300
        }

        for attempt in range(retries):
            try:
                response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
                response.raise_for_status()  # Raise an HTTPError for bad responses
                extracted_date = response.json()["choices"][0]["message"]["content"]
                extracted_date = extracted_date.split("|")
                confidence = extracted_date[1].strip().replace("confidence: ", "")
                extracted_date = extracted_date[0].strip()
                return extracted_date, confidence
            except requests.exceptions.RequestException as e:
                self.log.error(f"Error extracting date (attempt {attempt + 1}/{retries}): {e}")
                if attempt < retries - 1:
                    sleep(2 * attempt)  # Exponential backoff
                else:
                    return None, -1

   

    def validate_date_format(self, text):
        """
        Validate the extracted text to see if it matches the date format mm dd 'yy.
        """
        # self.log.info(f"Extracted date: {text}")
        # Define the regex pattern for the date format mm dd 'yy
        pattern = r'(\d{1,2})[.\-/ ](\d{1,2})[.\-/ ]\'*(\d{2,4})'
        
        # Search for the pattern in the extracted text
        match = re.search(pattern, text)
        
        if match:
            month, day, year = match.groups()

            # check century
            current_year_full = str(datetime.datetime.now().year)

            if len(year) == 2:
                current_year = current_year_full[-2:]
                if int(year) > int(current_year):
                    year = "19" + year
                else:
                    year = "20" + year

            date = f"{month.zfill(2)}/{day.zfill(2)}/{year}"

            # Validate the date
            if int(month) > 12 or int(day) > 31 or int(year) > int(current_year_full) or int(year) < self.MIN_YEAR:
                self.log.error("Out of bounds date detected.")
                return date, False

            return date, True
        else:
            self.log.error("No valid date found in image.")
            
            if "not found" in text.lower():
                return None, False
            
            return text, False
        

    def extract_and_validate_date(self, img):
        """
        High-level function to process the image, extract text, and validate the date.
        """
        # Read and process the image
        cropped_img = self.crop_date_64(img)
        
        # Extract text using Google Vision
        extracted_date, confidence = self.read_date(cropped_img)
        
        if extracted_date:
            # Validate the extracted text as a date
            clean_date, is_valid = self.validate_date_format(extracted_date)
            self.log.info(f"Extracted date: {clean_date} | Confidence: {confidence}")
            if not is_valid:
                confidence = -1

            return clean_date, int(confidence)
        else:
            self.log.error("No date extracted from the image.")
            return None, -1

    def read_image_date(self, image_path):
        """
        Reads the EXIF data from the given image and returns a dictionary of date-related EXIF fields
        that are not None. If all date-related EXIF fields are None, returns None.
        """
        # Load the image and read its EXIF data
        img_data = pyexiv2.Image(image_path)
        exif = img_data.read_exif()
        # print(f"exif {exif}")
        
        # Initialize an empty dictionary to store the date-related EXIF fields
        exif_date = {}
        
        # List of tuples containing the EXIF key and the corresponding dictionary key
        keys = [
            ('Exif.Image.DateTime', 'DateTime'),
            ('Exif.Photo.DateTimeOriginal', 'DateTimeOriginal'),
            ('Exif.Photo.DateTimeDigitized', 'DateTimeDigitized'),
        ]
        
        try:
            # Iterate through the keys and add non-None values to the date dictionary
            for exif_key, date_key in keys:
                if exif_key in exif and exif[exif_key]:  # Check if the EXIF key exists and its value is not None or empty
                    exif_date[date_key] = exif[exif_key]
                else:
                    exif_date[date_key] = "unknown"
            
            exif_date['comment'] = img_data.read_comment()
            # If the date dictionary is empty, set it to None
            if not exif_date:
                self.log.warn("No exif date found in image.")
                exif_date = None
            
        except KeyError as e:
            self.log.error(f"Error getting exif data from image: {e}")
            exif_date = None

        return exif_date


if __name__ == "__main__":
    # Example usage
    image_path = r"..\debug\cropped_image_2_5.jpg"
    image = cv2.imread(image_path)

    date_extractor = DateExtractor()
    date = date_extractor.extract_and_validate_date(image)
    print(date)

