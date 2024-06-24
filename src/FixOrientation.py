import cv2
import dlib
import numpy as np
import os

class ImageOrientationCorrector:
    def __init__(self, predictor_path='shape_predictor_5_face_landmarks.dat'):
        self.detector = dlib.get_frontal_face_detector()
        self.predictor = dlib.shape_predictor(predictor_path)

    def detect_faces_and_landmarks(self, image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        faces = self.detector(gray)
        faces_and_landmarks = []

        for face in faces:
            shape = self.predictor(gray, face)
            keypoints = [(shape.part(i).x, shape.part(i).y) for i in range(5)]
            faces_and_landmarks.append((face, keypoints))

        return faces_and_landmarks

    def determine_orientation(self, keypoints):
        right_eye, _, left_eye, _, nose = keypoints
        eyes_center = ((left_eye[0] + right_eye[0]) / 2, (left_eye[1] + right_eye[1]) / 2)


        if right_eye[1] > left_eye[1] and nose[0] > eyes_center[0]:
            return 'right_side_up'
        elif left_eye[1] > right_eye[1] and nose[0] < eyes_center[0]:
            return 'left_side_up'
        elif nose[1] < eyes_center[1]:
            return 'upside_down'


        return 'correct'

    def rotate_image(self, image, angle):
        if angle == 0:
            return image
        elif angle == 90:
            return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        elif angle == 180:
            return cv2.rotate(image, cv2.ROTATE_180)
        elif angle == 270:
            return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        return image

    def process_image(self, image):

        for angle in [0, 90, 180, 270]:
            rotated_image = self.rotate_image(image, angle)
            faces_and_landmarks = self.detect_faces_and_landmarks(rotated_image)

            if faces_and_landmarks:
                _, keypoints = faces_and_landmarks[0]
                orientation = self.determine_orientation(keypoints)
                print(f"Detected orientation: {orientation}")

                # self.draw_landmarks(rotated_image, bbox, keypoints)

                return rotated_image  # Returns first face it finds

        print("No faces detected.")
        return image  # Return the resized image if no faces are detected

    def draw_landmarks(self, image, bbox, keypoints):
        (x, y, w, h) = (bbox.left(), bbox.top(), bbox.width(), bbox.height())
        cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)

        for (i, (x, y)) in enumerate(keypoints):
            cv2.circle(image, (x, y), 3, (0, 0, 255), -1)
            cv2.putText(image, str(i + 1), (x - 10, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

    def process_images_in_folder(self, input_folder, output_folder):
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        for filename in os.listdir(input_folder):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                image_path = os.path.join(input_folder, filename)
                image = cv2.imread(image_path)

                if image is None:
                    print(f"Failed to load image: {filename}")
                    continue

                corrected_image = self.process_image(image)

                output_path = os.path.join(output_folder, filename)
                cv2.imwrite(output_path, corrected_image)
                print(f"Saved corrected image to: {output_path}")

# Example usage:
if __name__ == "__main__":
    input_folder = r'..\img\processed'
    output_folder = r'..\img\test\orientation\new'

    predictor_path = 'shape_predictor_5_face_landmarks.dat'
    corrector = ImageOrientationCorrector(predictor_path)
    corrector.process_images_in_folder(input_folder, output_folder)

    print("Processing completed.")
