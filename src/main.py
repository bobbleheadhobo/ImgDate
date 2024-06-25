import time
import argparse
import shutil
import os
from ImageOrganizer import ImageOrganizer
from DateEditor import ImageDateEditor
from LoggerConfig import setup_logger

def main():
    parser = argparse.ArgumentParser(description="Process images or start the editor.")
    parser.add_argument("operation", choices=["organize", "process", "edit"], help="Operation to perform")
    parser.add_argument("-d", "--delete", action="store_true", help="(Debug) Delete files in save path before operation")

    args = parser.parse_args()
    log = setup_logger("Main", "..\log\ImgDate.log")


    scans_path = r"..\img\unprocessed"
    save_path = r"..\img\processed"
    error_path = rf"{save_path}\Failed"

    start_time = time.time()

    # mainly used for debugging
    if args.delete:
        shutil.rmtree(save_path, ignore_errors=True)
        os.makedirs(save_path, exist_ok=True)



    image_organizer = ImageOrganizer(scans_path=scans_path, archive_scans=False, sort_images=False, date_images=True, crop_images=True)
    date_editor = ImageDateEditor(error_path, image_organizer)

    log.info(f"\n\n------------------------------\nStarting operation: {args.operation}\n------------------------------\n")


    if args.operation == "organize":
        image_organizer.process_images()
    elif args.operation == "edit":
        date_editor.start()
    elif args.operation == "process":
        image_organizer.process_images()

        date_editor.start()

    end_time = time.time()
    seconds = end_time - start_time
    if seconds < 60:
        log.info(f"Time taken to process images: {seconds} seconds")
    else:
        minutes = seconds / 60
        log.info(f"Time taken to process images: {minutes} minutes")

    

if __name__ == "__main__":
    main()