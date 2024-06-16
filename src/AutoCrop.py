import cv2
import numpy as np
import os
from concurrent.futures import ThreadPoolExecutor

class AutoCrop:
    def __init__(self):
        self.current_image = 0

    def crop_and_straighten(self, image_path):
        # Read the image
        image = cv2.imread(image_path)
        if image is None:
            print(f"Error: Could not load image {image_path}")
            return []

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Create a mask for background (white)
        mask = cv2.inRange(gray, 200, 255)
        mask = cv2.bitwise_not(mask)

        # Apply morphological operations to clean up the mask
        kernel = np.ones((3, 3), np.uint8)
        morph = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        # Find contours on the cleaned mask
        contours, _ = cv2.findContours(morph, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Save the mask for debugging
        cv2.imwrite(f"../img/processed/mask_{self.current_image}.jpg", morph)

        cropped_images = []
        preview_image = image.copy()

        for contour in contours:
            # Get the minimum area rectangle
            rect = cv2.minAreaRect(contour)
            area = cv2.contourArea(contour)
            if area < 1000000 or area > 9000000:
                continue

            # Draw the rotated rectangle for preview
            box = cv2.boxPoints(rect)
            box = np.intp(box)
            cv2.drawContours(preview_image, [box], 0, (0, 255, 0), 20)

            # Extract and process the rotated rectangle
            cropped = self.crop_rotated_rectangle(image, rect)

            if cropped.size > 0:
                cropped_images.append(cropped)
                self.current_image += 1

        # Save the preview for debugging
        cv2.imwrite(f"../img/processed/contours_{self.current_image}.jpg", preview_image)

        print(f"Detected {len(cropped_images)} images.")
        return cropped_images

    def crop_rotated_rectangle(self, image, rect):
        # Extract the bounding box
        box = cv2.boxPoints(rect)
        box = np.intp(box)

        # Compute the rotation matrix and warp the image
        width, height = int(rect[1][0]), int(rect[1][1])
        src_pts = box.astype("float32")
        dst_pts = np.array([[0, height-1], [0, 0], [width-1, 0], [width-1, height-1]], dtype="float32")
        M = cv2.getPerspectiveTransform(src_pts, dst_pts)
        warped = cv2.warpPerspective(image, M, (width, height))

        # Ensure the image is in landscape mode
        if warped.shape[0] > warped.shape[1]:
            warped = cv2.rotate(warped, cv2.ROTATE_90_COUNTERCLOCKWISE)

        # Remove borders if any (optional)
        final_cropped = self.remove_border(warped, 12)
        return final_cropped

    def remove_border(self, image, border_size):
        height, width = image.shape[:2]
        if border_size >= min(height // 2, width // 2):
            border_size = min(height // 2, width // 2) - 1
        return image[border_size:height-border_size, border_size:width-border_size]

if __name__ == "__main__":
    image_path = r"C:\Users\super\OneDrive\Documents\Code\img_date\img\test\distorted\00000001_7.jpg"

    import shutil
    save_path = r"..\img\processed"
    shutil.rmtree(save_path, ignore_errors=True)
    os.makedirs(save_path, exist_ok=True)
    
    auto_crop = AutoCrop()
    cropped_images = auto_crop.crop_and_straighten(image_path)
    print(f"Detected {len(cropped_images)} images.")
    for i, img in enumerate(cropped_images):
        cv2.imwrite(f"../img/processed/cropped_{i}.jpg", img)
        print(f"Saved cropped image {i}.")

    print(f"Detected {len(cropped_images)} images.")
