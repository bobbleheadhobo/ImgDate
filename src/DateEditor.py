from datetime import datetime
import re
import tkinter as tk
from tkinter import ttk
import cv2
import os
from PIL import Image, ImageTk
import numpy as np
import pyexiv2
from ImageOrganizer import ImageOrganizer  
from DateExtractor import DateExtractor

class ImageDateEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Date Editor")

        self.image_organizer = ImageOrganizer()
        self.date_extractor = DateExtractor()
        self.current_image_path = None
        self.current_image = None
        self.failed_images = self.get_failed_images()
        self.image_organizer.num_images = len(self.failed_images)
        self.current_index = 0


    def setup_gui(self):
        # Set up the main frame
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Canvas for displaying the large image
        self.canvas = tk.Canvas(self.main_frame, bg="gray")
        self.canvas.pack(fill=tk.BOTH, expand=True, side=tk.TOP)
        self.canvas.bind("<Configure>", self.on_resize)


        # Button to save the date
        self.save_button = ttk.Button(self.main_frame, text="Save Date", command=self.save_date)
        self.save_button.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

        # Entry for date input
        self.date_entry = ttk.Entry(self.main_frame, width=20)
        self.date_entry.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)
        self.date_entry.focus_set()  # Automatically focus on the entry widget

        # Bind Enter key to save the date
        self.date_entry.bind("<Return>", lambda event: self.save_date())

        # label to show current image date
        self.date_label = tk.Label(self.main_frame)
        self.date_label.pack(side=tk.BOTTOM, fill=tk.X, padx=1, pady=1)

        # Load the first image
        self.load_next_image()

    def update_label(self, text):
        self.date_label.config(text=text)

    def show_alert(self, text, txt_color):
        self.date_entry.config(foreground=txt_color)  # Change text color to the specified color
        self.date_entry.delete(0, tk.END)  # Clear the entry widget
        self.date_entry.insert(0, text)  # Insert the new text
        self.root.after(700, lambda: self.reset_date_entry())  # Reset the entry widget after 1 second

    def reset_date_entry(self):
        self.date_entry.config(foreground="black")  # Change text color to the specified color
        self.date_entry.delete(0, tk.END)  # Clear the entry widget
        self.date_entry.insert(0, "")  # Insert "Save" as the new text


    def get_failed_images(self):
        failed_path = self.image_organizer.error_path
        return [os.path.join(failed_path, file) for file in os.listdir(failed_path) if file.endswith(".jpg")]
    

    def get_image_date(self):
            img_data = pyexiv2.Image(self.current_image_path)
            exif = img_data.read_exif()
            exif_date = exif['Exif.Image.DateTime']
            date = self.infer_date(exif_date)
            return date

    def load_next_image(self):
        if self.current_index < len(self.failed_images):
            self.current_image_path = self.failed_images[self.current_index]
            self.current_index += 1

            # Load the large image
            self.current_image = cv2.imread(self.current_image_path)
            self.update_label(f"Image date: {self.get_image_date()}")


            # Display the large image
            self.display_image()
        else:
            print("No more images to display.")

    def display_image(self):
        if self.current_image is None:
            return

        # Resize the image to fit the canvas
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        if canvas_width > 1 and canvas_height > 1:
            resized_image = cv2.resize(self.current_image, (canvas_width, canvas_height), interpolation=cv2.INTER_LANCZOS4)
            self.photo_image = self.cv2_to_tk(resized_image)

            # Update the canvas with the new image
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo_image)

            # Display the small image in the bottom right corner
            self.display_small_image(canvas_width, canvas_height)

    def display_small_image(self, canvas_width, canvas_height):
        if self.current_image is None:
            return

        # Extract and resize the small image
        small_image = self.date_extractor.crop_date_64(self.current_image, False)
        if small_image is not None:
            small_image_resized = cv2.resize(small_image, (int(canvas_width * 0.4), int(canvas_height * 0.4)), interpolation=cv2.INTER_LANCZOS4)
            self.small_photo_image = self.cv2_to_tk(small_image_resized)

            # Calculate the position for the small image
            x = canvas_width - int(canvas_width * 0.4)  
            y = canvas_height - int(canvas_height * 0.4) 

            # Overlay the small image on the canvas
            self.canvas.create_image(x, y, anchor=tk.NW, image=self.small_photo_image)

    def on_resize(self, event):
        self.display_image()

    def save_date(self):
        # Get the entered date
        date = self.date_entry.get()

        # Validate and update the image metadata
        inferred_date = self.validate_date(date)
        if inferred_date:
            print(f"Updated date for {self.current_image_path} to {inferred_date}")
            success = self.image_organizer.save_image(self.current_image, inferred_date, 10)

            if success:
                self.show_alert("Image updated", "green")
                # Delete the current image
                os.remove(self.current_image_path)
            else:
                self.show_alert("Failed to save image", "red")


            # Load the next image
            self.load_next_image()
        else:
            self.show_alert("Invalid Date", "red")
            print("Invalid date format. Please enter a date in the format mm/dd/yyyy.")

    def infer_date(self, date):
        date = date.strip()
        # Define date patterns
        patterns = [
            (r'^(\d{2})[:\/\s-]?(\d{2})[:\/\s-]?(\d{4})$', "%m%d%Y"),  # 01/07/2001, 01 07 2001, 01072001
            (r'^(\d{1,2})[\/\s-]?(\d{1,2})[\/\s-]?(\d{2})$', "%m%d%y"),  # 1/7/01, 1 7 01, 01/07/01
            (r'^(\d{1,2})[\/\s-]?(\d{1,2})[\/\s-]?(\d{4})$', "%m%d%Y"),  # 1/7/2001
            (r'(\d{4})[\:/\s-](\d{2})[\/:\s-](\d{2})', "%Y%m%d"), # yyyy:mm:dd
            (r'^(\d{2})(\d{2})(\d{4})$', "%d%m%Y"),  # 31122000
            (r'^(\d{2})(\d{2})(\d{2})$', "%d%m%y"),  # 311299
        ]

        for pattern, date_format in patterns:
            match = re.match(pattern, date)
            if match:
                # Reconstruct the date string based on captured groups
                reconstructed_date = ''.join(match.groups())
                try:
                    # Parse and format the date
                    parsed_date = datetime.strptime(reconstructed_date, date_format)
                    formatted_date = parsed_date.strftime("%m/%d/%Y")
                    return formatted_date
                except ValueError:
                    continue

        # If no pattern matched, return False or raise an error
        return False

    def validate_date(self, date):
        inferred_date = self.infer_date(date)
        print(f"Inferred date: {inferred_date}")
        if inferred_date and self.date_extractor.validate_date_format(inferred_date):
            print(f"Validated date: {inferred_date}")
            return inferred_date
        print(f"Invalid date: {date}")
        return False

    def cv2_to_tk(self, img):
        """Convert a cv2 image to a Tkinter PhotoImage"""
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(img_rgb)
        return ImageTk.PhotoImage(img_pil)

if __name__ == "__main__":
    # Set up the ImageOrganizer
    scans_path = r"..\img\test\skewed"
    save_path = r"..\img\processed"
    error_path = rf"{save_path}\Failed"

    # # Delete files and folders in save path directory recursively
    # shutil.rmtree(save_path)
    # os.makedirs(save_path)

    image_organizer = ImageOrganizer(scans_path, save_path, error_path)

    # Create the Tkinter window
    root = tk.Tk()
    date_editor = ImageDateEditor(root)
    date_editor.setup_gui()
    root.mainloop()


