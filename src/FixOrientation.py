import cv2
import dlib
import numpy as np
import os

class OrientationCorrector:
    def __init__(self, predictor_path='shape_predictor_5_face_landmarks.dat'):
        self.detector = dlib.get_frontal_face_detector()
        self.predictor = dlib.shape_predictor(predictor_path)

    def detect_faces_and_landmarks(self, image):
        # Convert to grayscale for face detection
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # Detect faces in the image
        faces = self.detector(gray)
        faces_and_landmarks = []

        for face in faces:
            # Get facial landmarks
            shape = self.predictor(gray, face)
            keypoints = [(shape.part(i).x, shape.part(i).y) for i in range(5)]
            faces_and_landmarks.append((face, keypoints))

        return faces_and_landmarks

    def determine_orientation(self, keypoints):
        # Determine the relative positions of key facial landmarks
        right_eye, _, left_eye, _, nose = keypoints
        eyes_center = ((left_eye[0] + right_eye[0]) / 2, (left_eye[1] + right_eye[1]) / 2)
        print(keypoints)
        print(eyes_center)

        # Determine the orientation of the face based on landmark positions
        if right_eye[1] > left_eye[1] and nose[0] > eyes_center[0]:
            return 'right_side_up'
        elif left_eye[1] > right_eye[1] and nose[0] < eyes_center[0]:
            return 'left_side_up'
        elif nose[1] < eyes_center[1]:
            return 'upside_down'

        return 'correct'

    def rotate_image(self, image, angle):
        # Rotate the image by the specified angle
        if angle == 0:
            return image
        elif angle == 90:
            return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        elif angle == 180:
            return cv2.rotate(image, cv2.ROTATE_180)
        elif angle == 270:
            return cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)
        return image

    def adaptive_resize_image(self, image, max_width, min_width):
        # Resize the image to a maximum width while preserving aspect ratio, but not smaller than the minimum width
        if image.shape[1] > max_width:
            ratio = max_width / float(image.shape[1])
            dim = (max_width, int(image.shape[0] * ratio))
        else:
            dim = (image.shape[1], image.shape[0])

        resized_image = cv2.resize(image, dim, interpolation=cv2.INTER_AREA)
        
        # Ensure the resized width is not less than the minimum width
        if resized_image.shape[1] < min_width:
            ratio = min_width / float(resized_image.shape[1])
            dim = (min_width, int(resized_image.shape[0] * ratio))
            resized_image = cv2.resize(resized_image, dim, interpolation=cv2.INTER_AREA)
        
        return resized_image

    def process_image(self, image):
        # Define resizing parameters
        max_width = 800
        min_width = 400

        # Step 1: Resize the image for quicker processing
        resized_image = self.adaptive_resize_image(image, max_width, min_width)
        
        # Step 2: Attempt to detect faces in the resized image
        for angle in [0, 90, 180, 270]:
            rotated_image = self.rotate_image(resized_image, angle)
            faces_and_landmarks = self.detect_faces_and_landmarks(rotated_image)

            if faces_and_landmarks:
                bbox, keypoints = faces_and_landmarks[0]
                orientation = self.determine_orientation(keypoints)
                print(f"Detected orientation on resized image: {orientation}")

                # Return the original image in the corrected orientation
                corrected_angle = self.get_rotation_angle(orientation)
                return self.rotate_image(image, corrected_angle)

        # Step 3: If no faces detected in the resized image, check the original image
        print("No faces detected in resized image, checking original image.")
        for angle in [0, 90, 180, 270]:
            rotated_image = self.rotate_image(image, angle)
            faces_and_landmarks = self.detect_faces_and_landmarks(rotated_image)

            if faces_and_landmarks:
                bbox, keypoints = faces_and_landmarks[0]
                orientation = self.determine_orientation(keypoints)
                print(f"Detected orientation on original image: {orientation}")

                # Return the original image in the corrected orientation
                corrected_angle = self.get_rotation_angle(orientation)
                return self.rotate_image(image, corrected_angle)

        # If no faces are detected, return the original image without modification
        print("No faces detected in original image.")
        return image

    def get_rotation_angle(self, orientation):
        # Map the determined orientation to the corresponding rotation angle
        if orientation == 'right_side_up':
            return 90
        elif orientation == 'left_side_up':
            return 270
        elif orientation == 'upside_down':
            return 180
        return 0  # 'correct' or no need to rotate

    def draw_landmarks(self, image, bbox, keypoints):
        # Draw rectangles around the face and circles on the facial landmarks
        (x, y, w, h) = (bbox.left(), bbox.top(), bbox.width(), bbox.height())
        cv2.rectangle(image, (x, y), (x + w, y + h), (0, 255, 0), 2)

        for (i, (x, y)) in enumerate(keypoints):
            cv2.circle(image, (x, y), 3, (0, 0, 255), -1)
            cv2.putText(image, str(i + 1), (x - 10, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

    def process_images_in_folder(self, input_folder, output_folder):
        # Ensure the output folder exists
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        for filename in os.listdir(input_folder):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                image_path = os.path.join(input_folder, filename)
                image = cv2.imread(image_path)

                if image is None:
                    print(f"Failed to load image: {filename}")
                    continue

                # Process the image and get the corrected orientation
                corrected_image = self.process_image(image)

                # Save the corrected image
                output_path = os.path.join(output_folder, filename)
                cv2.imwrite(output_path, corrected_image)
                print(f"Saved corrected image to: {output_path}")

# Example usage:
if __name__ == "__main__":
    input_folder = r'..\img\test\orientation'
    output_folder = r'..\img\test\orientation\new'

    predictor_path = 'shape_predictor_5_face_landmarks.dat'
    corrector = OrientationCorrector(predictor_path)
    corrector.process_images_in_folder(input_folder, output_folder)

    print("Processing completed.")
