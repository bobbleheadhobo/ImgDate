import os
import shutil
from ImageOrganizer import ImageOrganizer
from DateEditor import ImageDateEditor

if __name__ == "__main__":
    # Set up the ImageOrganizer
    scans_path = r"..\img\test"
    save_path = r"..\img\processed"
    error_path = rf"{save_path}\Failed"

    # # # Delete files and folders in save path directory recursively
    # shutil.rmtree(save_path)
    # os.makedirs(save_path)

    image_organizer = ImageOrganizer()
    image_organizer.process_images()

    # Create the Tkinter window
    date_editor = ImageDateEditor(error_path, image_organizer)
    date_editor.start()