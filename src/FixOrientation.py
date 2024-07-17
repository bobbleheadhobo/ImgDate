import cv2
import dlib
import os
import numpy as np
import time

class FixOrientation:
    def __init__(self, predictor_path='shape_predictor_5_face_landmarks.dat'):
        self.detector = dlib.get_frontal_face_detector()
        self.predictor = dlib.shape_predictor(predictor_path)

    def detect_faces_and_landmarks(self, gray):
        faces = self.detector(gray, 1)
        if not faces:
            return None
        face = faces[0]
        shape = self.predictor(gray, face)
        return face, np.array([(shape.part(i).x, shape.part(i).y) for i in range(5)])

    def determine_orientation(self, keypoints):
        right_eye, _, left_eye, _, nose = keypoints
        eyes_center = (left_eye + right_eye) / 2

        if right_eye[1] > left_eye[1] and nose[0] > eyes_center[0]:
            return 'right_side_up'
        if left_eye[1] > right_eye[1] and nose[0] < eyes_center[0]:
            return 'left_side_up'
        if nose[1] < eyes_center[1]:
            return 'upside_down'
        return 'correct'

    @staticmethod
    def rotate_image(image, angle):
        if angle == 0:
            return image
        return cv2.rotate(image, [cv2.ROTATE_90_CLOCKWISE, cv2.ROTATE_180, cv2.ROTATE_90_COUNTERCLOCKWISE][angle // 90 - 1])

    def process_image(self, image):
        original_image = image.copy()
        h, w = image.shape[:2]
        min_dim = min(h, w)
        scale = 1
        if min_dim > 1000:
            scale = 1000 / min_dim
            image = cv2.resize(image, (int(w * scale), int(h * scale)))

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Try upright orientation first
        result = self.detect_faces_and_landmarks(gray)
        if result:
            _, keypoints = result
            orientation = self.determine_orientation(keypoints)
            print(f"Detected orientation: {orientation}")
            return original_image

        # If no face found, try other orientations
        for angle in [90, 180, 270]:
            rotated_gray = self.rotate_image(gray, angle)
            result = self.detect_faces_and_landmarks(rotated_gray)

            if result:
                _, keypoints = result
                orientation = self.determine_orientation(keypoints)
                print(f"Detected orientation: {orientation}")
                return self.apply_orientation(original_image, angle)

        print("No faces detected.")
        return original_image

    def apply_orientation(self, image, angle):
        if angle == 0:
            return image
        return self.rotate_image(image, angle)

    def process_images_in_folder(self, input_folder, output_folder):
        os.makedirs(output_folder, exist_ok=True)
        total_time = 0
        processed_images = 0

        for filename in os.listdir(input_folder):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                input_path = os.path.join(input_folder, filename)
                output_path = os.path.join(output_folder, filename)
                
                start_time = time.time()
                
                image = cv2.imread(input_path)
                if image is None:
                    print(f"Failed to load image: {filename}")
                    continue

                corrected_image = self.process_image(image)
                cv2.imwrite(output_path, corrected_image, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
                
                end_time = time.time()
                processing_time = end_time - start_time
                total_time += processing_time
                processed_images += 1
                
                print(f"Processed {filename} in {processing_time:.2f} seconds")
                print(f"Saved corrected image to: {output_path}")

        if processed_images > 0:
            avg_time = total_time / processed_images
            print(f"\nProcessed {processed_images} images in total")
            print(f"Total processing time: {total_time:.2f} seconds")
            print(f"Average processing time per image: {avg_time:.2f} seconds")

if __name__ == "__main__":
    # input_folder = r'..\img\processed'
    # output_folder = r'..\img\processed\corrected'
    
    input_folder = r'C:\Users\super\OneDrive\Desktop\processed\processed'
    output_folder = r'C:\Users\super\OneDrive\Desktop\processed\corrected1'

    predictor_path = 'shape_predictor_5_face_landmarks.dat'
    corrector = FixOrientation(predictor_path)
    
    start_time = time.time()
    corrector.process_images_in_folder(input_folder, output_folder)
    end_time = time.time()
    
    print(f"\nTotal script execution time: {end_time - start_time:.2f} seconds")