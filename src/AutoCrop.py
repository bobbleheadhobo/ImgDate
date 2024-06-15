import cv2
import numpy as np
import matplotlib.pyplot as plt
import random

class AutoCrop:
    def __init__(self):
        self.current_image = 0
        pass

    def crop_and_straighten(self, image_path):
        # Read the image
        image = cv2.imread(image_path)
        if image is None:
            print(f"Error: Could not load image {image_path}")
            return []

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Define the range for the background color (near white)
        lower_white = np.array([200, 200, 200], dtype=np.uint8)
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

        
        # Create the directory if it doesn't exist
        
        # Save the image
        cv2.imwrite(f"../img/processed/mask_{self.current_image}.jpg", morph)

        cropped_images = []
        preview_image = image.copy()

        for contour in contours:
            # Get the minimum area rectangle
            rect = cv2.minAreaRect(contour)
            box = cv2.boxPoints(rect)
            box = np.intp(box)

            # Filter out very small or very large areas
            area = cv2.contourArea(contour)
            if area < 1000000 or area > 9000000:
                continue

            # Debug draw the rotated rectangle for preview
            cv2.drawContours(preview_image, [box], 0, (0, 255, 0), 20)

            # Extract the rotated rectangle
            cropped = self.crop_rotated_rectangle(image, rect)

            if cropped.size > 0:
                cropped_images.append(cropped)
                self.current_image += 1

        # debug save the detected contours for cropping
        cv2.imwrite(f"../img/processed/contours_{random.randint(1,100)}.jpg", preview_image)

        print(f"Detected {len(cropped_images)} images.")

        return cropped_images

    def crop_rotated_rectangle(self, image, rect):
        # Get the original dimensions
        original_height, original_width = image.shape[:2]

        # Calculate the size of the new canvas (diagonal of the original image)
        new_size = int(np.sqrt(original_width**2 + original_height**2))

        # Create a larger canvas with the new size, and place the original image at the center
        canvas = np.full((new_size, new_size, 3), 255, dtype=np.uint8)  # White background
        center_x, center_y = new_size // 2, new_size // 2

        # Calculate the offset to center the image on the new canvas
        offset_x, offset_y = center_x - original_width // 2, center_y - original_height // 2

        # Place the original image on the new canvas
        canvas[offset_y:offset_y + original_height, offset_x:offset_x + original_width] = image

        # Calculate the new center for the rotation (center of the canvas)
        new_center = (center_x, center_y)

        # Get the rotation matrix for the given angle and center of the rectangle
        angle = rect[2]
        rotation_matrix = cv2.getRotationMatrix2D(new_center, angle, 1.0)

        # Perform the rotation with a constant border
        rotated = cv2.warpAffine(canvas, rotation_matrix, (new_size, new_size),
                                 flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))

        # Calculate the new center of the rotated rectangle relative to the canvas
        rect_center_adjusted = (rect[0][0] + offset_x, rect[0][1] + offset_y)

        # Adjust the center of the rotated rectangle for the new rotated canvas
        center_transformed = self.transform_center(rotation_matrix, rect_center_adjusted)

        # Extract the size of the rectangle to crop
        width, height = int(rect[1][0]), int(rect[1][1])
        expand_by = 12  # Adjust this value as needed
        size = (width + expand_by, height + expand_by)

        # Extract the rotated rectangle from the rotated image
        cropped = cv2.getRectSubPix(rotated, size, center_transformed)

        # Ensure the cropped image is rotated back correctly
        if angle < -45:
            cropped = cv2.rotate(cropped, cv2.ROTATE_90_CLOCKWISE)

        final_cropped = self.remove_border(cropped, expand_by)

        # Adjust orientation to landscape
        final_cropped = self.ensure_landscape(final_cropped)

        return final_cropped
    
    def transform_center(self, rotation_matrix, center):
        # Apply the rotation matrix to the center point
        center_array = np.array([center[0], center[1], 1]).reshape((3, 1))
        transformed_center = np.dot(rotation_matrix, center_array)
        return transformed_center[:2].flatten()
    

    def ensure_landscape(self, image):
        height, width = image.shape[:2]
        if height > width:
            # Rotate 90 degrees clockwise to switch to landscape
            image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        return image
    
    def remove_border(self, image, border_size):
        # Ensure the border size is not larger than half the image dimensions
        height, width = image.shape[:2]
        if border_size >= min(height // 2, width // 2):
            border_size = min(height // 2, width // 2) - 1
        return image[border_size:height-border_size, border_size:width-border_size]


    def preview_detected_contours(self, image):
        plt.figure(figsize=(10, 10))
        plt.gca().set_facecolor('black')
        plt.subplot(1, 2, 1)
        plt.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        plt.title('Original Image')
        plt.axis('off')
        plt.show()

if __name__ == "__main__":
    # Replace with the path to your image file
    image_path = r"C:\Users\super\OneDrive\Documents\Code\img_date\img\test\distorted\00000001_8.jpg"

    import shutil
    import os
    save_path = r"..\img\processed"
    shutil.rmtree(save_path, ignore_errors=True)
    os.makedirs(save_path, exist_ok=True)
    
    auto_crop = AutoCrop()
    cropped_images = auto_crop.crop_and_straighten(image_path)
    print(f"Detected {len(cropped_images)} images.")
    for i, img in enumerate(cropped_images):
        cv2.imwrite(f"../img/processed/cropped_{i}.jpg", img)
        print(f"Saved cropped image {i}.")