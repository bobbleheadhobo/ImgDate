import base64
import datetime
import cv2
import numpy as np
from google.cloud import vision
from google.cloud.vision_v1 import types
from PIL import Image
import piexif
import re
import random
from matplotlib import pyplot as plt
import os
from dotenv import load_dotenv

import requests

class DateExtractor:

    def __init__(self):
        self.crop_height = 0.8
        self.crop_width = 0.70
        load_dotenv()
        self.api_key = os.getenv('OPENAI_API_KEY')

    def crop_date_64(self, img):
        """
        Crop the bottom right corner of the image where the date is located.
        Converts to base64 and returns the cropped image.
        """
        # Crop the bottom right corner
        h, w, _ = img.shape
        # cv2.rectangle(img, (int(w*self.crop_width), int(h*self.crop_height)), (w, h), (0, 255, 0), 5)
        cropped_img = img[int(h*self.crop_height):h, int(w*self.crop_width):w]
        

        _, buffer = cv2.imencode('.jpg', cropped_img)

        # Optional: Save the processed image for debugging
        processed_image_path = f"../img/processed/date{random.randint(1, 100)}.jpg"
        cv2.imwrite(processed_image_path, cropped_img)

        # Convert the cropped image to base64
        base64_img = base64.b64encode(buffer).decode('utf-8')

        return base64_img

    def read_date(self, base64_image):
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
                "text": "This is a film image that likely contains a date, typically in orange or red text. This image has been cropped down to enlarge the text size. Please read the date and provide it in the format MM DD \'YY. Respond only with the date and a confidence level from 1 to 10 on how certain you are of its accuracy. Example \"12 07 \'01 | confidence: 10\". If the date is unclear or cannot be read, please respond with \"01 01 \'85 | confidence: -1\" as a placeholder."
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

        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

        extracted_date = response.json()["choices"][0]["message"]["content"]

        extracted_date = extracted_date.split("|")[0].strip()
        confidence = extracted_date.split("|")[1].strip().replace("confidence: ", "")

        return extracted_date, confidence

   

    def validate_date_format(self, text):
        """
        Validate the extracted text to see if it matches the date format mm dd 'yy.
        """
        # Define the regex pattern for the date format mm dd 'yy
        pattern = r'(\d{1,2})[.\-/ ](\d{1,2})[.\-/ ]\'(\d{2})'
        
        # Search for the pattern in the extracted text
        match = re.search(pattern, text)
        
        if match:
            month, day, year = match.groups()


            # check century
            current_year_full = str(datetime.datetime.now().year)
            current_year = current_year_full[-2:]
            if int(year) > int(current_year):
                year = "19" + year
            else:
                year = "20" + year

            # Validate the date
            if int(month) > 12 or int(day) > 31 or int(year) > int(current_year_full) or int(year) < 1985:
                print("Invalid date detected.")
                return None
            
            # checks for placeholder date when not found
            if month == "01" or day == "01" or year == "1985":
                print("Date not found in image")
                return None

            print(f"Extracted date: {month}/{day}/{year}")
            return f"{month.zfill(2)}/{day.zfill(2)}/{year}"
        else:
            print("No valid date found in the text.")
            return None

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
            valid_date = self.validate_date_format(extracted_date)
            return valid_date, confidence
        else:
            print("No text extracted from the image.")
            return None, -1




if __name__ == "__main__":
    # Example usage
    image_path = r"..\debug\cropped_image_2_5.jpg"
    image = cv2.imread(image_path)

    date_extractor = DateExtractor()
    date = date_extractor.extract_and_validate_date(image)
    print(date)

