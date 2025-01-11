from flask import Flask, render_template, request
import os
import webview
import signal
import threading
import shutil
import time
import subprocess
from ultralytics import YOLO

from extras import create_yaml, strip_optimizer, detect_objects, Create_Service
from extras import archive_and_upload, download_weight, rotate_and_capture_images

from PIL import Image

# creating google drive api service
CLIENT_SECRET_FILE = 'client_secret_file.json'
API_NAME = 'drive'
API_VERSION = 'v3'
SCOPES = ['https://www.googleapis.com/auth/drive',
          'https://www.googleapis.com/auth/drive.appdata',
          'https://www.googleapis.com/auth/drive.file',
          'https://www.googleapis.com/auth/drive.metadata',
          'https://www.googleapis.com/auth/drive.metadata.readonly',
          'https://www.googleapis.com/auth/drive.readonly',
          'https://www.googleapis.com/auth/drive.activity']
while True:
    try:
        drive_service = Create_Service(CLIENT_SECRET_FILE, API_NAME, API_VERSION, SCOPES)
        break
    except:
        pass

# flask app initialization
app = Flask(__name__)

# configuring paths for new images, and for detection purpose
app.config['UPLOAD_PATH'] = 'collected_images/images'
app.config['DETECTION_UPLOAD_PATH'] = 'static/manual_detections'


@app.route('/')
def home():
    return render_template('main.html')


@app.route('/collect-images', methods=['POST', 'GET'])
def collect_images():
    if request.method == 'POST':
        # delete existing 'images' and 'labels' in 'collected_images'
        try:
            shutil.rmtree('collected_images/images')
        except:
            pass
        try:
            shutil.rmtree('collected_images/labels')
        except:
            pass
        # make new 'images' and 'labels'
        os.mkdir('collected_images/images')
        os.mkdir('collected_images/labels')

        # create first checkpoint
        f = open('checkpoint/ckpt/1.txt', 'w')
        f.close()

    return render_template('step1.html')


@app.route('/label-images', methods=['POST', 'GET'])
def label_images():
    if request.method == 'POST':
        print('files' in request.files)
        print('num-faces' in request.form)

        if 'files' in request.files:
            # saving files that are selected to 'collected_images/images'
            files = request.files.getlist('files')
            for file in files:
                image = Image.open(file)
                # resize the image to 640 pixels wide while preserving the aspect ratio
                image = image.resize((640, int(image.height * (640 / image.width))))
                # save the resized image to the server
                image.save(os.path.join(app.config['UPLOAD_PATH'], file.filename))

        elif 'num-faces' in request.form and 'product-name' in request.form:
            num_faces = request.form['num-faces']
            prod_name = request.form['product-name']
            rotate_and_capture_images(int(num_faces), str(prod_name))

        # create 2nd checkpoint
        f = open('checkpoint/ckpt/2.txt', 'w')
        f.close()

    # count no. of files in 'collected_images/images'
    images_count = len(os.listdir('collected_images/images'))
    return render_template('step2.html', number=images_count)


@app.route('/train-model', methods=['POST', 'GET'])
def labelling_process():
    current_dir = os.getcwd()
    images_folder = os.path.join(current_dir, 'collected_images', 'images')
    labels_folder = os.path.join(current_dir, 'collected_images', 'labels')

    if request.method == 'POST':
        while True:
            # if labelling of images already started
            if os.path.exists('collected_images/labels/classes.txt'):
                classes_file = os.path.join(current_dir, 'collected_images', 'labels', 'classes.txt')
                # command to open labelimg
                os.system(f'labelimg "{images_folder}" "{classes_file}" "{labels_folder}"')
            else:
                classes_file = os.path.join(current_dir, 'workspace', 'current_classes.txt')
                os.system(f'labelimg "{images_folder}" "{classes_file}" "{labels_folder}"')

            # checking if all images are annotated
            if len(os.listdir('collected_images/labels')) - 1 == len(os.listdir('collected_images/images')):
                # create 3rd checkpoint
                f = open('checkpoint/ckpt/3.txt', 'w')
                f.close()
                break
            else:
                print('ALL IMAGES SHOULD BE LABELLED!!')
                choice = input("Enter 'y' to continue labelling : ")
                if choice == 'y' or choice == 'Y':
                    pass
                else:
                    return "<h2>YOU CAN EXIT NOW !</h2>"

    return render_template('step3.html')


@app.route('/training', methods=['POST', 'GET'])
def training():
    if request.method == 'POST':

        if os.path.exists('collected_images/labels/classes.txt'):
            # create 'custom_data.yaml' inside 'workspace' (replaces old one)
            create_yaml()

            # replace 'current_classes.txt' with new one
            shutil.move('collected_images/labels/classes.txt', 'workspace/current_classes.txt')

            # copy all collected images and labels to workspace directory
            shutil.copytree('collected_images/images/.', 'workspace/dataset/train/images', dirs_exist_ok=True)
            shutil.copytree('collected_images/labels/.', 'workspace/dataset/train/labels', dirs_exist_ok=True)

        # whether user decide to train on Local PC or On cloud
        train_choice = request.form['train-choice']

        # if train in PC is chosen
        if train_choice == 'pc-train':

            # training command
            current_dir = os.getcwd()
            custom_data = os.path.join(current_dir, 'workspace', 'custom_data.yaml')
            epochs = 200

            if os.path.exists('runs/detect/first_train/weights/last.pt'):
                shutil.copy('runs/detect/first_train/weights/last.pt', 'runs/detect/last.pt')
                if os.path.exists('runs/detect/first_train/weights/best.pt'):
                    shutil.copy('runs/detect/first_train/weights/best.pt', 'runs/detect/best.pt')
                shutil.rmtree('runs/detect/first_train')
                checkpoint = os.path.join(current_dir, 'runs', 'detect', 'last.pt')
                train_command = f'yolo task=detect mode=train model="{checkpoint}" imgsz=640 data="{custom_data}" epochs={epochs} batch=4 name=first_train workers=1 augment=True optimize=True patience=200 resume device=0'
            else:
                if os.path.exists('runs'):
                    shutil.rmtree('runs')
                train_command = f'yolo task=detect mode=train model=yolov8s.pt imgsz=640 data="{custom_data}" epochs={epochs} batch=4 name=first_train workers=1 augment=True optimize=True patience=200 device=0'

            try:
                os.system(command=f'{train_command}')
            except RuntimeError:
                return '<h1>Your PC suck !!<br>Try again after restarting.</h1>'

            # creates 4th checkpoint only if training is completed
            last_epoch = 0
            try:
                with open('runs/detect/first_train/results.csv', 'r') as f:
                    last_epoch = int(f.readlines()[-1].split()[0][:-1]) + 1
            except:
                pass

            if last_epoch == epochs and os.path.exists('runs/detect/first_train/confusion_matrix.png'):
                if not os.path.exists('runs/detect/first_train/weights/best.pt'):
                    print('Missing of last or best file !')
                    best_file = 'runs/detect/best.pt'
                    strip_optimizer(best_file)
                    shutil.copy('runs/detect/best.pt', 'runs/detect/first_train/weights/best.pt')
                    print('Best.pt stripped and copied to weights!')
                shutil.copy('runs/detect/first_train/weights/best.pt', 'workspace/classifier.pt')
                shutil.rmtree('runs/detect/first_train')

                f = open('checkpoint/ckpt/4.txt', 'w')
                f.close()
            else:
                return '<h1>Seems like training not completed.<br>Exit Now and rerun.</h1>'

        # if cloud train is chosen
        else:
            # copy dataset folder and custom_data.yaml in new 'for_cloud'
            shutil.copytree('workspace/dataset', 'workspace/for_cloud/dataset')
            shutil.copy('workspace/custom_data.yaml', 'workspace/for_cloud')

            # make for_cloud.zip
            archive_and_upload(drive_service)
            os.system(command='kaggle kernels push -p kaggle_notebook')
            print('kaggle notebook running, this may take long')
            while True:
                time.sleep(10)
                result = subprocess.check_output(['kaggle', 'kernels', 'status', 'groupeleven/yolov8-training'])
                output = result.decode('utf-8')
                if 'complete' in output:
                    break
            download_weight(service=drive_service)
            print('New weight downloaded.')
            f = open('checkpoint/ckpt/4.txt', 'w')
            f.close()
            return render_template('step3.2.html')

    if os.path.exists('checkpoint/ckpt/4.txt'):
        return render_template('step3.2.html')

    return render_template('step3.html')


model = None
classes = None


@app.route('/detecting', methods=['POST'])
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
            
            return render_template('step4.html', filename=file.filename, scores=detected_scores, names=detected_names)
        return render_template('step4.html')


@app.route('/finish', methods=['POST'])
def finish():
    if request.method == 'POST':
        shutil.copy('workspace/classifier.pt', '../Billing_Section/flask_postgre/classifier.pt')
        finish_page = '<h1 style="margin-top:100px; color: red; text-align:center;">NEW MODEL TRAINED</h1>' \
                      '<h2 style="text-align: center">YOU CAN CLOSE THE TAB NOW</h2>'
        shutil.rmtree('checkpoint/ckpt')
        os.mkdir('checkpoint/ckpt')
        return finish_page


def exit_gracefully(signum, frame):
    exit()


def run_flask():
    app.run(debug=True, use_reloader=False)


# Start Flask app in a new thread
flask_thread = threading.Thread(target=run_flask)

if __name__ == '__main__':
    signal.signal(signal.SIGTERM, exit_gracefully)
    flask_thread.start()

# CHECKING CHECKPOINT AND OPENS ACCORDING TO IT
no_of_ckpt_files = len(os.listdir('checkpoint/ckpt'))
if no_of_ckpt_files == 0:
    # Open the Flask app in a webview window
    window = webview.create_window('AI Biller Train', 'http://localhost:5000', width=1920, height=1080)
elif no_of_ckpt_files == 1:
    window = webview.create_window('AI Biller Train', 'http://localhost:5000/collect-images', width=1920, height=1080)
elif no_of_ckpt_files == 2:
    window = webview.create_window('AI Biller Train', 'http://localhost:5000/label-images', width=1920, height=1080)
elif no_of_ckpt_files == 3:
    window = webview.create_window('AI Biller Train', 'http://localhost:5000/train-model', width=1920, height=1080)
else:
    window = webview.create_window('AI Biller Train', 'http://localhost:5000/training', width=1920, height=1080)

webview.start()

if os.path.exists('runs/detect/predict'):
    shutil.rmtree('runs/detect/predict')

os.kill(os.getpid(), signal.SIGTERM)

