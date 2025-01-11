import cv2
import shutil
from ultralytics import YOLO

model = YOLO('workspace/classifier.pt')

cap = cv2.VideoCapture(0)
while cap.isOpened():
    res, frame = cap.read()
    model.predict(source=frame, verbose=False, save=True, conf=0.8)
    image = cv2.imread('runs/detect/predict/image0.jpg')
    cv2.imshow('Frame', image)
    if cv2.waitKey(50) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

try:
    shutil.rmtree('runs/detect/predict')
except:
    pass
