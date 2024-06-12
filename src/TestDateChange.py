import pyexiv2

def print_metadata(file_path):
    """
    Load and print all metadata (EXIF, XMP, IPTC) from an image.
    """
    try:
        # Open the image file with pyexiv2
        image = pyexiv2.Image(file_path)

        # Read EXIF metadata
        exif_data = image.read_exif()
        print("\nEXIF Metadata:")
        for key, value in exif_data.items():
            print(f"{key}: {value}")

        # Read XMP metadata
        xmp_data = image.read_xmp()
        print("\nXMP Metadata:")
        for key, value in xmp_data.items():
            print(f"{key}: {value}")

        # Read IPTC metadata
        iptc_data = image.read_iptc()
        print("\nIPTC Metadata:")
        for key, value in iptc_data.items():
            print(f"{key}: {value}")

    except Exception as e:
        print(f"Error reading metadata from {file_path}: {e}")

    finally:
        image.close()

if __name__ == "__main__":
    # Replace with the path to your image file
    image_path = r"..\img\processed\1985\January\2_date_01-01-1985_7608.jpg"
    
    print_metadata(image_path)
