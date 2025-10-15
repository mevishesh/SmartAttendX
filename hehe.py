import dlib, cv2, numpy as np
print("dlib version:", dlib.__version__)
img = cv2.imread("C:/Users/DHEERAJ/Desktop/SmartAttendX/face_recognition/trained_faces/1/1.jpg")
img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
img = np.ascontiguousarray(img, dtype="uint8")
detector = dlib.get_frontal_face_detector()
faces = detector(img, 1)
print("Faces detected:", len(faces))
