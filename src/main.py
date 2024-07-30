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


    scans_path = r"..\img\test\multi_date_formats"
    save_path = r"..\img\test\multi_date_formats\processed"
    error_path = rf"{save_path}\Failed"
    archive_path = rf"{save_path}\Archive"


    # mainly used for debugging
    if args.delete:
        log.info("Deleting files in save path before operation")
        try:
            shutil.rmtree(save_path)
        except FileNotFoundError:
            pass
        except Exception as e:
            log.error(f"Failed to delete files in save path: {e}")
        os.makedirs(save_path, exist_ok=True)


    start_time = time.time()

    image_organizer = ImageOrganizer(save_path=save_path,
                                     scans_path=scans_path,
                                     error_path=error_path,
                                     archive_scans=False,
                                     sort_images=False,
                                     fix_orientation=True,
                                     crop_images=True,
                                     date_images=False)
    
    date_editor = ImageDateEditor(source_folder_path=save_path, image_organizer=image_organizer)

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