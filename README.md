# ImgDate: Automated Photo Digitization and Organization

## Description

ImgDate is a powerful Python-based tool designed to streamline the process of digitizing and organizing printed photographs. It automates the tasks of cropping, date extraction, orientation correction, and metadata management for scanned images, making it an invaluable asset for preserving and cataloging personal or professional photo collections.

## Main Features

- **Automatic Image Cropping**: Utilizes computer vision techniques to detect and crop individual photos from scanned sheets.
- **Date Extraction**: Employs GPT-4o Vision to extract dates from scanned photos.

- **Metadata Management**: Updates EXIF data with extracted dates on the images.

- **Orientation Correction**: Automatically detects and corrects the orientation of photos using facial recognition. <u>Note: This feature requires successful installation of dlib and its dependencies</u>

- **Intelligent File Organization**: Sorts processed images into folders by year and month.

- **Multi-threading Support**: Enhances processing speed for large batches of images.

- **Error Handling**: Manages low-confidence date extractions and processing failures.

## Use Cases

- Digitizing family photo albums
- Archiving historical photograph collections
- Processing large volumes of printed photos for digital preservation
- Organizing scanned images from various sources

## Installation
1. Clone the repository:
git clone https://github.com/bobbleheadhobo/ImgDate.git
cd ImgDate

2. Install required dependencies:
pip install -r requirements.txt

3. Set up your OpenAI API key:
- Create a `.env` file in the project root
- Add your OpenAI API key: `OPENAI_API_KEY=your_api_key_here`

## Usage

1. Place your scanned images in the `img/unprocessed` folder.

2. Run the main script:

3. Processed images will be saved in the `img/processed` folder, organized by year and month.

## Configuration

You can customize the behavior of ImgDate by modifying the parameters in the `ImageOrganizer` class initialization:

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

## Contributing
Contributions to ImgDate are welcome! Please feel free to submit a Pull Request.