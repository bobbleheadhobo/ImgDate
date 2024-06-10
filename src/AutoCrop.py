import cv2
import numpy as np
import matplotlib.pyplot as plt
import random

class AutoCrop:
    def __init__(self):
        pass

    def crop_and_straighten(self, image_path):
        # Read the image
        image = cv2.imread(image_path)
        if image is None:
            print(f"Error: Could not load image {image_path}")
            return []

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Define the range for the background color (near white)
        lower_white = np.array([180, 180, 180], dtype=np.uint8)
        upper_white = np.array([255, 255, 255], dtype=np.uint8)

        # Create a mask to isolate the background
        mask = cv2.inRange(image, lower_white, upper_white)
        mask = cv2.bitwise_not(mask)  # Invert mask to highlight non-background areas

        # Apply the mask to the grayscale image to highlight potential image areas
        masked_image = cv2.bitwise_and(gray, gray, mask=mask)

        # Apply morphological operations to clean up the mask
        kernel = np.ones((5, 5), np.uint8)
        morph = cv2.morphologyEx(masked_image, cv2.MORPH_CLOSE, kernel, iterations=2)

        # Find contours on the cleaned mask
        contours, _ = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        cv2.imwrite(f"img/processed/mask{random.randint(1,100)}.jpg", morph)

        cropped_images = []
        preview_image = image.copy()

        for contour in contours:
            # Get the minimum area rectangle
            rect = cv2.minAreaRect(contour)
            box = cv2.boxPoints(rect)
            box = np.int0(box)

            # Filter out very small or very large areas
            area = cv2.contourArea(contour)
            if area < 1000000 or area > 9000000:
                continue

            # Debug draw the rotated rectangle for preview
            # cv2.drawContours(preview_image, [box], 0, (0, 255, 0), 10)

            # Extract the rotated rectangle
            cropped = self.crop_rotated_rectangle(image, rect)

            if cropped.size > 0:
                cropped_images.append(cropped)

        # debug save the detected contours for cropping
        # cv2.imwrite(f"img/processed/image{random.randint(1,100)}.jpg", preview_image)

        print(f"Detected {len(cropped_images)} images.")

        return cropped_images

    def crop_rotated_rectangle(self, image, rect):
        # Get the rotation matrix for the given angle and center of the rectangle
        width = int(rect[1][0])
        height = int(rect[1][1])
        angle = rect[2]

        # Calculate the center and the rotation matrix
        center = (rect[0][0], rect[0][1])
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        
        # Perform the rotation
        rotated = cv2.warpAffine(image, rotation_matrix, (image.shape[1], image.shape[0]), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

        # Crop the rotated rectangle from the rotated image
        expand_by = 12  # Adjust this value as needed
        size = (width + expand_by, height + expand_by)
        cropped = cv2.getRectSubPix(rotated, size, center)

        # Ensure the cropped image is rotated back correctly
        if angle < -45:
            cropped = cv2.rotate(cropped, cv2.ROTATE_90_CLOCKWISE)

        final_cropped = self.remove_border(cropped, expand_by)

        # Adjust orientation to landscape
        final_cropped = self.ensure_landscape(final_cropped)

        return final_cropped

    def ensure_landscape(self, image):
        height, width = image.shape[:2]
        if height > width:
            # Rotate 90 degrees clockwise to switch to landscape
            image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        return image
    
    def remove_border(self, image, border_size):
        # Remove the border by slicing off the edges
        height, width = image.shape[:2]
        return image[border_size:height-border_size, border_size:width-border_size]

    def preview_detected_contours(self, image, trimmed):
        plt.figure(figsize=(10, 10))
        plt.gca().set_facecolor('black')
        plt.subplot(1, 2, 1)
        plt.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        plt.title('Original Image')
        plt.axis('off')

        plt.subplot(1, 2, 2)
        plt.imshow(cv2.cvtColor(trimmed, cv2.COLOR_BGR2RGB))
        plt.title('Trimmed Image')
        plt.axis('off')
        plt.tight_layout()
        plt.show()
