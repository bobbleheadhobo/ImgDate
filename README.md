# ImgDate: Automated Photo Digitization

## Description
ImgDate is a powerful Python-based tool designed to streamline the process of digitizing and organizing printed photographs. It can automatically crop, read date stamps, and sort images making it an invaluable for film photography.

## Main Features
- **Automatic Image Cropping**: Crops multiple images from a single scan
- **Date Extraction**: Employs GPT-4 Vision to extract dates from scanned photos
- **Metadata Management**: Updates EXIF data with extracted dates on the images
- **Orientation Correction**: Automatically detects and corrects the orientation of photos using facial recognition (requires dlib)
- **Date Editor**: Easily update the EXIF data of photos manually for the ones that the script failed to process
- **File Organization**: Sorts processed images into folders by year and month
- **Multi-threading Support**: Enhances processing speed for large batches of images
- **Web Interface**: User-friendly browser interface for easy image processing and date editing

## Prerequisites
- Python 3.8 or higher
- Windows operating system (for Visual Studio Build Tools)
- OpenAI API key
- 64-bit Python installation (required for dlib)

## Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/bobbleheadhobo/ImgDate.git
   cd ImgDate
   ```

2. Install Microsoft Visual Studio Build Tools (required for dlib):
   - Download Visual Studio Build Tools from [Microsoft's website](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
   - Run the installer
   - Select "Desktop development with C++"
   - Make sure the following components are checked:
     - MSVC Build Tools
     - Windows 10 SDK
     - C++ CMake tools for Windows
   - Click Install

3. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Add your API keys in .env_copy
   - Enter the needed keys
   - Rename the file to .env

### Troubleshooting Installation
- If you encounter issues installing dlib, make sure you have Python 64-bit installed
- After installing Visual Studio Build Tools, you may need to restart your computer
- If the pip install still fails, you can try installing dlib separately first:
  ```bash
  pip install dlib
  ```

## Usage

### 1. Web Interface
The simplest way to use ImgDate is through its web interface:

1. Start the web server:
   ```bash
   python app.py
   ```

2. Open your web browser and navigate to `http://localhost:5000`

### 2. Command Line Interface
For users who want quicker processing times and have lots of images:

1. Place your scanned images in the `img/unprocessed` folder
2. Run one of the following commands:
   ```bash
   # Process and organize images automatically
   python main.py organize

   # Open the date editor for manually editing dates
   python main.py edit

   # Process images and then open editor for failed detections
   python main.py process
   ```
3. Processed images will be saved in the `img/processed` folder by default
4. Customize ImgDate's behavior by modifying the parameters in main.py:

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
       sort_images=True,
       draw_contours=True
   )
   ```

## Important Notes
- For accurate date detection, ensure dates appear in:
  - Top right corner for landscape images
  - Top left corner for portrait images

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## License
This project is licensed under the GNU General Public License v3.0. See the [LICENSE](LICENSE) file for details.
