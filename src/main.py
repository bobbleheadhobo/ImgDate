import sys
import argparse
import shutil
import os
from ImageOrganizer import ImageOrganizer
from DateEditor import ImageDateEditor

def main():
    parser = argparse.ArgumentParser(description="Process images or start the editor.")
    parser.add_argument("operation", choices=["organize", "process", "edit"], help="Operation to perform")
    parser.add_argument("-d", "--delete", action="store_true", help="Delete files in save path before operation")

    args = parser.parse_args()

    scans_path = r"..\img\test\distorted"
    save_path = r"..\img\processed"
    error_path = rf"{save_path}\Failed"

    if args.delete:
        shutil.rmtree(save_path, ignore_errors=True)
        os.makedirs(save_path, exist_ok=True)


    image_organizer = ImageOrganizer(scans_path=scans_path)
    date_editor = ImageDateEditor(error_path, image_organizer)

    if args.operation == "organize":
        image_organizer.process_images()
    elif args.operation == "edit":
        date_editor.start()
    elif args.operation == "process":
        image_organizer.process_images()

        date_editor.start()

    

if __name__ == "__main__":
    main()