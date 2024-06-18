import cv2
import numpy as np
import os
from LoggerConfig import setup_logger

class AutoCrop:
    def __init__(self):
        self.current_image = 0
        self.log = setup_logger("AutoCrop", "..\log\ImgDate.log")

    def crop_and_straighten(self, image_path):
        image = cv2.imread(image_path)
        if image is None:
            self.log.error(f"Could not load image: {image_path}")
            return []

        # Use the improved method to create a robust mask
        mask = self.create_mask(image)

        # Find contours on the mask
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Save the mask for debugging
        # cv2.imwrite(f"../img/processed/mask_{self.current_image}.jpg", mask)

        cropped_images = []
        preview_image = image.copy()

        for contour in contours:
            rect = cv2.minAreaRect(contour)
            area = cv2.contourArea(contour)

            # Debug self.log.info contour areas

            # Filter out too small or too large areas - adjust these values based on image characteristics
            if area < 1000000 or area > 9000000:
                continue

            # debug Draw the rotated rectangle for preview
            # box = cv2.boxPoints(rect)
            # box = np.intp(box)
            # cv2.drawContours(preview_image, [box], 0, (0, 255, 0), 10)

            # Extract and process the rotated rectangle
            cropped = self.crop_rotated_rectangle(image, rect)

            # Validate the cropped image to ensure it has enough non-white content
            if cropped.size > 0 and self.is_valid_crop(cropped):
                cropped_images.append(cropped)
                self.current_image += 1

        # Save the preview for debugging
        # cv2.imwrite(f"../img/processed/contours_{self.current_image}.jpg", preview_image)

        self.log.info(f"Detected {len(cropped_images)} images.")
        return cropped_images

    def create_mask(self, image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Adaptive thresholding to handle varying lighting conditions
        adaptive_thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
        )

        # Combine adaptive threshold with color thresholding
        lower_white = np.array([200, 200, 200], dtype=np.uint8)
        upper_white = np.array([255, 255, 255], dtype=np.uint8)
        color_mask = cv2.inRange(image, lower_white, upper_white)
        color_mask_inv = cv2.bitwise_not(color_mask)

        # Combine masks to better segment areas
        combined_mask = cv2.bitwise_and(adaptive_thresh, adaptive_thresh, mask=color_mask_inv)

        # Apply morphological operations to clean up the mask
        kernel = np.ones((5, 5), np.uint8)
        morph = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel, iterations=2)

        return morph

    def crop_rotated_rectangle(self, image, rect):
        # Extract the bounding box
        box = cv2.boxPoints(rect)
        box = np.intp(box)

        # Compute the perspective transform matrix and warp the image
        width, height = int(rect[1][0]), int(rect[1][1])
        src_pts = box.astype("float32")
        dst_pts = np.array([[0, height-1], [0, 0], [width-1, 0], [width-1, height-1]], dtype="float32")
        M = cv2.getPerspectiveTransform(src_pts, dst_pts)
        warped = cv2.warpPerspective(image, M, (width, height))

        # Ensure the image is in landscape mode
        if warped.shape[0] > warped.shape[1]:
            warped = cv2.rotate(warped, cv2.ROTATE_90_COUNTERCLOCKWISE)

        # Optionally remove borders (adjust the size as needed)
        final_cropped = self.remove_border(warped, 12)
        return final_cropped

    def is_valid_crop(self, image, min_content_threshold=0.1):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        non_white_ratio = np.sum(gray < 240) / (gray.shape[0] * gray.shape[1])
        return non_white_ratio > min_content_threshold

    def remove_border(self, image, border_size):
        height, width = image.shape[:2]
        if border_size >= min(height // 2, width // 2):
            border_size = min(height // 2, width // 2) - 1
        return image[border_size:height-border_size, border_size:width-border_size]

if __name__ == "__main__":
    image_path = r"C:\Users\super\OneDrive\Documents\Code\img_date\img\unprocessed\00000001_4.jpg"

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
