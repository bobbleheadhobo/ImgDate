# ImgDate: Automated Photo Digitization

## Description
ImgDate is a powerful Python-based tool designed to streamline the digitization and organization of printed photographs. It can automatically crop, read date stamps, and sort images, making it invaluable for film photography.

## Main Features
- **Automatic Image Cropping**: Crops multiple images from a single scan
- **Date Extraction**: Employs GPT-4 Vision to extract dates from scanned photos
- **Metadata Management**: Updates EXIF data with extracted dates on the images
- **Orientation Correction**: Automatically detects and corrects the orientation of photos using facial recognition (requires dlib)
- **File Organization**: Sorts processed images into folders by year and month
- **Multi-threading Support**: Enhances processing speed for large batches of images
- **Web Interface**: User-friendly browser interface for easy image processing

## Prerequisites
- Python 3.10 or higher
- Linux (Fedora/RHEL/Ubuntu)
- OpenAI API key

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/bobbleheadhobo/ImgDate.git
   cd ImgDate
   ```

2. Install system dependencies (required to build dlib from source):
   ```bash
   # Fedora / RHEL / CentOS
   sudo dnf install -y cmake gcc gcc-c++ python3-devel

   # Ubuntu / Debian
   sudo apt install -y cmake gcc g++ python3-dev
   ```

3. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

4. Install required Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Add your API keys:
   - Copy `.env_copy` to `.env`
   - Fill in the required keys

### Troubleshooting Installation
- If `pip install dlib` fails, ensure `cmake`, `gcc`, `gcc-c++`, and `python3-devel` are installed first

## Usage

Activate the venv, then run commands from the `src/` directory:
```bash
source venv/bin/activate
cd src
```

### 1. Web Interface
The simplest way to use ImgDate is through its web interface:

1. Start the web server:
   ```bash
   python app.py
   ```

2. Open your web browser and navigate to `http://localhost:8888`

### 2. Command Line Interface
For users who want quicker processing times and have lots of images:

1. Place your scanned images in the `img/unprocessed` folder
2. Run one of the following commands:
   ```bash
   # Process images in the unprocessed folder
   python main.py organize

   # Flags:
   # -d to delete all images in the save path
   # -c to draw contours around cropped images
   ```
3. Processed images will be saved in the `img/processed` folder by default
4. Customize ImgDate's behavior by modifying the parameters in `main.py`:

   ```python
   image_organizer = ImageOrganizer(
       scans_path="../img/unprocessed",
       save_path="../img/processed",
       error_path="../img/processed/Failed",
       archive_path="../img/processed/archive",
       crop_images=True,
       date_images=True,
       fix_orientation=True,
       archive_scans=True,
       sort_images=True
   )
   ```

## Important Notes
- For accurate date detection, ensure dates appear in:
  - Bottom right corner for landscape images
  - Bottom left corner for portrait images

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request.

## License
This project is licensed under the GNU General Public License v3.0. See the [LICENSE](COPYING.txt) file for details.
