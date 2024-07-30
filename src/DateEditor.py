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

        # Create a frame to hold the date label and the checkbox
        self.date_frame = ttk.Frame(self.main_frame)
        self.date_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

        # Label to show the current image date
        self.date_label = tk.Label(self.date_frame, bg="lightgrey", font=("Arial", 10))
        self.date_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1, pady=1)

        # Create a BooleanVar to store the state of the checkbox
        self.magnify_date = tk.BooleanVar(value=True)

        # Create the Checkbutton widget
        self.checkbox = tk.Checkbutton(self.date_frame, text="Magnify Date", variable=self.magnify_date, command=self.magnify_date_checkbox_toggled)
        self.checkbox.pack(side=tk.RIGHT)
        

        # Bind Enter key to save the date
        self.date_entry.bind("<Return>", lambda event: self.save_date())

        # Load the first image
        self.load_next_image()


    
    def magnify_date_checkbox_toggled(self):
        if self.magnify_date.get():
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            self.display_small_image(canvas_width, canvas_height)
        else:
            self.canvas.delete("small_image")

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

        # Resize the image to fit the canvas
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        if canvas_width > 1 and canvas_height > 1:
            resized_image = cv2.resize(self.current_image, (canvas_width, canvas_height), interpolation=cv2.INTER_LANCZOS4)
            self.photo_image = self.cv2_to_tk(resized_image)

            # Update the canvas with the new image
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo_image)

            if self.magnify_date.get():
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
            self.canvas.create_image(x, y, anchor=tk.NW, image=self.small_photo_image, tags="small_image")

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
