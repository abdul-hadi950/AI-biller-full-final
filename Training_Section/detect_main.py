from flask import Flask, render_template, request
import os
import webview
import signal
import threading
import shutil
from ultralytics import YOLO

from extras import detect_objects

app = Flask(__name__)

app.config['DETECTION_UPLOAD_PATH'] = 'static/manual_detections'


model = None
classes = None


@app.route('/detecting', methods=['POST', 'GET'])
def detecting():
    global model, classes

    if request.method == 'POST':
        # directly after training, new model should load
        if model is None:
            model = YOLO('workspace/classifier.pt')
            classes = model.names
        file = request.files.get('input-file')
        if file:
            file.save(os.path.join(app.config['DETECTION_UPLOAD_PATH'], file.filename))

            results = detect_objects(file.filename, model)
            shutil.copy(f'runs/detect/predict/{file.filename}', f'static/manual_detections/{file.filename}')
            result = results[0].boxes

            detected_scores = []
            detected_names = []

            for i in range(len(result)):
                class_id = int(result[i].cls[0].tolist())
                detected_names.append(classes[class_id])
                detected_scores.append(round(result[i].conf[0].tolist(), 2))

            return render_template('detect.html', filename=file.filename, scores=detected_scores, names=detected_names)
    return render_template('detect.html')


def exit_gracefully(signum, frame):
    exit()


def run_flask():
    app.run(debug=True, use_reloader=False, port=5001)


# Start Flask app in a new thread
flask_thread = threading.Thread(target=run_flask)

if __name__ == '__main__':
    signal.signal(signal.SIGTERM, exit_gracefully)
    flask_thread.start()

window = webview.create_window('AI Biller Detect', 'http://localhost:5001/detecting')

webview.start()

if os.path.exists('runs/detect/predict'):
    shutil.rmtree('runs/detect/predict')

os.kill(os.getpid(), signal.SIGTERM)
