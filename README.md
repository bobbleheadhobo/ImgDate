# ImgDate: Automated Photo Digitization and Organization

## Description

ImgDate is a powerful Python-based tool designed to streamline the process of digitizing and organizing printed photographs. It automates the tasks of cropping, date extraction, orientation correction, and metadata management for scanned images, making it an invaluable asset for preserving and cataloging personal or professional photo collections.

## Main Features

- **Automatic Image Cropping**: Crops multiple images from a single scan.
<br>

- **Date Extraction**: Employs GPT-4o Vision to extract dates from scanned photos.
<br>

- **Metadata Management**: Updates EXIF data with extracted dates on the images.
<br>

- **Orientation Correction**: Automatically detects and corrects the orientation of photos using facial recognition. <u>Note: This feature requires successful installation of dlib and its dependencies</u>
<br>

- **Date Editor**: Easily update the EXIF data of photos manually for the ones that the script failed to process.
<br>

- **Intelligent File Organization**: Sorts processed images into folders by year and month.
<br>

- **Multi-threading Support**: Enhances processing speed for large batches of images.
<br>

- **Error Handling**: Manages low-confidence date extractions and processing failures.

## Installation
1. Clone the repository:
git clone https://github.com/bobbleheadhobo/ImgDate.git
cd ImgDate

2. Install required dependencies:
pip install -r requirements.txt

3. Set up your OpenAI API key:
- Create a `.env` file in the project root
- Add your OpenAI API key: `OPENAI_API_KEY=your_api_key_here`

## Configuration

You can customize the behavior of ImgDate by modifying the parameters in the `ImageOrganizer` class initialization:


```
image_organizer = ImageOrganizer(
 scans_path=r"..\img\unprocessed",
 save_path=r"..\img\processed",
 error_path=r"..\img\processed\Failed",
 archive_path=r"..\img\processed\archive",
 crop_images=True,
 date_images=True, 
 fix_orientation=True,
 archive_scans=True,
 sort_images=True
)
```

## Usage

1. Place your scans images in the `img/unprocessed` folder or any folder of your choice.

2. Run the main script:
    `python main.py organize` this will crop, date and organize your images
    `python main.py edit` this will open the date editor allowing you to quickly update the date of your images
    `python main.py process` this will crop, date and organize your photos then open the date editor to fix the images that failed

3. Processed images will be saved in the `img/processed` folder or the folder of your choice



Note: when scanning images the dates of the images must be in the <span style="color:red">top right for landscape position</span> and <span style="color:red">top left for portrait position</span>. Otherwise the script will look for the date in the wrong part of the image.

## Contributing
Contributions to ImgDate are welcome! Please feel free to submit a Pull Request.
