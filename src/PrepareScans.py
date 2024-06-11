import os
import shutil

def move_images(source_dir, save_dir):
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            if file.lower().endswith(('.jpg')):
                source_path = os.path.join(root, file)
                save_path = os.path.join(save_dir, file)

                # Check if file already exists
                base, extension = os.path.splitext(save_path)
                counter = 1
                while os.path.exists(save_path):
                    save_path = f"{base}_{counter}{extension}"
                    counter += 1

                shutil.move(source_path, save_path)
                print(f"Moved {file} to {save_path}")

    shutil.rmtree(source_dir)
    print(f"Deleted {source_dir}")

# Example usage
source_directory = r'C:\Users\super\OneDrive\Desktop\scans'
save_directory = r'..\img\unprocessed'

move_images(source_directory, save_directory)