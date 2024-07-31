# ImgDate: Automated Photo Digitization

## Description

ImgDate is a powerful Python-based tool designed to streamline the process of digitizing and organizing printed photographs. It automates the tasks of cropping, date extraction, orientation correction, and metadata management for scanned images, making it an invaluable asset for preserving and cataloging personal or professional photo collections.

## Main Features

- **Automatic Image Cropping**: Crops multiple images from a single scan.
<br>

- **Date Extraction**: Employs GPT-4o Vision to extract dates from scanned photos.
<br>

- **Metadata Management**: Updates EXIF data with extracted dates on the images.
<br>

- **Orientation Correction**: Automatically detects and corrects the orientation of photos using facial recognition. Note: This feature requires successful installation of dlib and its dependencies
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
<br>
cd ImgDate

2. Install required dependencies:
<br>
pip install -r requirements.txt

3. Set up your OpenAI API key:
<br>
- Create a `.env` file in the project root
<br>
- Add your OpenAI API key: `OPENAI_API_KEY=your_api_key_here`

## Configuration

You can customize the behavior of ImgDate by modifying the parameters in the `ImageOrganizer` class initialization:


```python
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
    `python main.py organize` Crops, dates and organizes your images.
<br>

    `python main.py edit` Opens the date editor allowing you to quickly update the date of your images.
<br>

    `python main.py process` Crop, date and organize your photos then open the date editor to fix the images that failed.

3. Processed images will be saved in the `img/processed` folder or the folder of your choice

<be>
> [!IMPORTANT]
> When scanning images the dates of the images must be in the top right for landscape position and top left for portrait position. Otherwise the script will look for the date in the wrong part of the image.

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request.
