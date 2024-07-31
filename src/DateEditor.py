from datetime import datetime
import re
import time
import tkinter as tk
from tkinter import ttk
import cv2
import os
from PIL import Image, ImageTk
import pyexiv2
from DateExtractor import DateExtractor
from LoggerConfig import setup_logger

class ImageDateEditor:
    def __init__(self, source_folder_path, image_organizer):
        self.root = tk.Tk()
        self.image_organizer = image_organizer
        self.source_folder_path = source_folder_path
        self.date_extractor = DateExtractor()
        self.current_image_path = None
        self.current_image = None
        self.current_index = 0
        self.magnifier_size = 200  # Size of the magnifier
        self.zoom_factor = 3  # How much to zoom in
        self.log = setup_logger("DateEditor", "..\log\ImgDate.log")

    def setup_gui(self):
        self.log.info("Starting date editor")
        
        self.failed_images = self.get_failed_images(source_path=self.source_folder_path)
        self.num_images = len(self.failed_images)
        self.image_organizer.num_images = self.num_images

        self.root.title("Quick Date Editor")
        # Make the window appear on top initially
        self.root.attributes("-topmost", True)

        # Set up the main frame
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Show number of images left at the top
        self.num_images_label = tk.Label(self.main_frame, bg="lightblue", font=("Arial", 12))
        self.num_images_label.pack(side=tk.TOP, fill=tk.X, padx=1, pady=1)

        # Canvas for displaying the large image
        self.canvas = tk.Canvas(self.main_frame, bg="white")
        self.canvas.pack(fill=tk.BOTH, expand=True, side=tk.TOP)
        self.canvas.bind("<Configure>", self.on_resize)

        # Button to save the date
        self.save_button = ttk.Button(self.main_frame, text="Save Date", command=self.save_date)
        self.save_button.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

        # Entry for date input
        self.date_entry = ttk.Entry(self.main_frame, width=20)
        self.date_entry.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)
        self.date_entry.focus_set()  # Automatically focus on the entry widget

        # Create a frame to hold the date label
        self.date_frame = ttk.Frame(self.main_frame)
        self.date_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

        # Label to show the current image date
        self.date_label = tk.Label(self.date_frame, bg="lightgrey", font=("Arial", 10))
        self.date_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1, pady=1)
        

        # Bind Enter key to save the date
        self.date_entry.bind("<Return>", lambda event: self.save_date())
        
        # Add mouse bindings for magnifier
        self.canvas.bind("<Motion>", self.update_magnifier)
        self.canvas.bind("<Leave>", self.hide_magnifier)
        
        # Load the first image
        self.load_next_image()

    def update_magnifier(self, event):
        if not hasattr(self, 'resized_image'):
            return

        # Get the position relative to the image
        x = event.x - self.image_x
        y = event.y - self.image_y

        # Check if the cursor is over the image
        if 0 <= x < self.resized_image.shape[1] and 0 <= y < self.resized_image.shape[0]:
            # Calculate the region to magnify
            left = max(0, x - self.magnifier_size // (2 * self.zoom_factor))
            top = max(0, y - self.magnifier_size // (2 * self.zoom_factor))
            right = min(self.resized_image.shape[1], x + self.magnifier_size // (2 * self.zoom_factor))
            bottom = min(self.resized_image.shape[0], y + self.magnifier_size // (2 * self.zoom_factor))

            # Extract the region
            magnified_region = self.resized_image[top:bottom, left:right]

            # Resize the region
            magnified = cv2.resize(magnified_region, (self.magnifier_size, self.magnifier_size), interpolation=cv2.INTER_LINEAR)

            # Convert to PhotoImage
            self.magnified_photo = self.cv2_to_tk(magnified)

            # Position the magnified image near the cursor
            mag_x = event.x + 20
            mag_y = event.y + 20

            # Ensure the magnified image stays within the canvas
            if mag_x + self.magnifier_size > self.canvas.winfo_width():
                mag_x = event.x - self.magnifier_size - 20
            if mag_y + self.magnifier_size > self.canvas.winfo_height():
                mag_y = event.y - self.magnifier_size - 20

            # Display the magnified image
            self.canvas.delete("magnifier")
            self.canvas.create_image(mag_x, mag_y, anchor=tk.NW, image=self.magnified_photo, tags="magnifier")

    def hide_magnifier(self, event):
        self.canvas.delete("magnifier")

    def update_date_label(self, text):
        self.date_label.config(text=text)

    def update_num_image_label(self, text):
        self.num_images_label.config(text=text)

    def show_alert(self, text, txt_color):
        self.date_entry.config(foreground=txt_color)  # Change text color to the specified color
        self.date_entry.delete(0, tk.END)  # Clear the entry widget
        self.date_entry.insert(0, text)  # Insert the new text
        self.root.after(500, lambda: self.reset_date_entry())  # Reset the entry widget after 1 second

    def reset_date_entry(self):
        self.date_entry.config(foreground="black")  # Change text color back to black
        self.date_entry.delete(0, tk.END)  # Clear the entry widget
        self.date_entry.insert(0, "")  # Reset the entry widget

    def get_failed_images(self, source_path):
        return [os.path.join(source_path, file) for file in os.listdir(source_path) if file.endswith(".jpg")]

    def get_image_date(self):
        img_data = pyexiv2.Image(self.current_image_path)
        exif = img_data.read_exif()
        try:
            exif_date = exif['Exif.Image.DateTime']
            date = self.infer_date(exif_date)
        except KeyError:
            date = None
        return date

    def load_next_image(self):
        if self.current_index < self.num_images:
            self.current_image_path = self.failed_images[self.current_index]
            self.current_index += 1

            # Load the large image
            self.current_image = cv2.imread(self.current_image_path)
            self.update_date_label(f"Image date: {self.get_image_date()}")
            self.update_num_image_label(f"{self.current_index} of {self.num_images} images")

            # Display the large image
            self.display_image()
        else:
            self.update_num_image_label(f"All images processed")
            time.sleep(1)
            self.log.info("No more images to display.")
            self.root.destroy()

    def display_image(self):
        if self.current_image is None:
            return

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        if canvas_width > 1 and canvas_height > 1:
            # Get original image dimensions
            img_height, img_width = self.current_image.shape[:2]
            
            # Calculate aspect ratios
            img_aspect = img_width / img_height
            canvas_aspect = canvas_width / canvas_height
            
            if img_aspect > canvas_aspect:
                # Image is wider than canvas
                new_width = canvas_width
                new_height = int(canvas_width / img_aspect)
            else:
                # Image is taller than canvas
                new_height = canvas_height
                new_width = int(canvas_height * img_aspect)
            
            self.resized_image = cv2.resize(self.current_image, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
            self.photo_image = self.cv2_to_tk(self.resized_image)

            # Calculate position to center the image
            self.image_x = (canvas_width - new_width) // 2
            self.image_y = (canvas_height - new_height) // 2

            # Clear previous image and create new one
            self.canvas.delete("all")
            self.canvas.create_image(self.image_x, self.image_y, anchor=tk.NW, image=self.photo_image)


    def on_resize(self, event):
        self.display_image()

    def save_date(self):
        """
        Save the date entered by the user or inferred from the image metadata,
        update the image's metadata, and proceed to the next image.
        """
        # Get the entered date from the date entry field
        date = self.date_entry.get().strip()  # Remove leading/trailing spaces
        self.log.info(f"Entered date: {date}")

        if date == "":
            # If no date is entered, attempt to infer the date from the image metadata
            self.log.info("skipping")
            self.show_alert("Skipping", "blue")
            self.load_next_image()
            return
        else:
            date = self.validate_date(date)

        if date is not None:  # Check specifically for None

            # Attempt to save the image with the updated metadata
            existing_exif_data = None
            file_name = self.generate_filename(date)
            success = self.image_organizer.save_image(self.current_image, date, 10, file_name, existing_exif_data)
            
            if success:
                self.show_alert(f"{date}", "green")
                # Delete the current image file after successful update
                try:
                    os.remove(self.current_image_path)
                    self.log.info(f"Deleted current image: {self.current_image_path}")
                except OSError as e:
                    self.log.info(f"Error deleting file {self.current_image_path}: {e}")
            else:
                self.show_alert("Failed to save image", "red")

            # Load the next image
            self.load_next_image()
        else:
            # Handle invalid date format
            self.show_alert("Invalid Date", "red")
            self.log.info("Invalid date format. Please enter a date in the format mm/dd/yyyy.")

    def infer_date(self, date):
        date = date.strip()
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
                reconstructed_date = ''.join(match.groups())
                try:
                    parsed_date = datetime.strptime(reconstructed_date, date_format)
                    formatted_date = parsed_date.strftime("%m/%d/%Y")
                    return formatted_date
                except ValueError:
                    continue

        return None  # Explicitly return None if no pattern matched

    def validate_date(self, date):
        inferred_date = self.infer_date(date)
        if inferred_date and self.date_extractor.validate_date_format(inferred_date):
            self.log.info(f"Validated date: {inferred_date}")
            return inferred_date
        self.log.error(f"Invalid date: {date}")
        return None  # Explicitly return None for invalid dates

    def generate_filename(self, date,):
        if date is None:  # Check specifically for None
            self.log.error("Invalid date provided for filename generation.")
            raise ValueError("Invalid date provided for filename generation.")

        # Continue with filename generation if date is valid
        formatted_date = date.replace('/', '-')
        filename = f"date_{formatted_date}.jpg"
        filepath = os.path.join(self.image_organizer.save_path, filename)
        filepath = self.image_organizer.duplicate_check(filepath)
        return os.path.basename(filepath)
        
        

    def cv2_to_tk(self, cv_image):
        # Convert the OpenCV image (BGR) to a format compatible with Tkinter (RGB)
        rgb_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
        image_pil = Image.fromarray(rgb_image)
        return ImageTk.PhotoImage(image_pil)

    def start(self):
        self.setup_gui()
        self.root.mainloop()
