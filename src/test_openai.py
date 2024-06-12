import base64
import requests

# OpenAI API Key

# Function to encode the image
def encode_image(image_path):
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')

# Path to your image
image_path = r"C:\Users\super\OneDrive\Documents\Code\img_date\img\processed\date69.jpg"

# Getting the base64 string
base64_image = encode_image(image_path)

headers = {
  "Content-Type": "application/json",
  "Authorization": f"Bearer {api_key}"
}

payload = {
  "model": "gpt-4o",
  "messages": [
    {
      "role": "user",
      "content": [
        {
          "type": "text",
          "text": "This is a film image that likely contains a date, typically in orange or red text. This image has been cropped down to enlarge the text size. Please read the date and provide it in the format MM DD \'YY. Respond only with the date and a confidence level from 1 to 10 on how certain you are of its accuracy. Example \"12 07 \'01 | confidence: 10\". If the date is unclear or cannot be read, please respond with \"01 01 \'59 | confidence: -1\" as a placeholder."
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

try:
    extracted_text = response.json()["choices"][0]["message"]["content"]
    print(f"Extracted text: {extracted_text}")
except (KeyError, IndexError):
    print("No text extracted from the image.")