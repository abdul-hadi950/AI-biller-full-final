import torch
import cv2

import pickle
import os
from google_auth_oauthlib.flow import Flow, InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from google.auth.transport.requests import Request
import io
from zipfile import ZipFile, ZIP_DEFLATED
import shutil

import time
import serial


def Create_Service(client_secret_file, api_name, api_version, *scopes):
    # print(client_secret_file, api_name, api_version, scopes, sep='-')
    CLIENT_SECRET_FILE = client_secret_file
    API_SERVICE_NAME = api_name
    API_VERSION = api_version
    SCOPES = [scope for scope in scopes[0]]
    print(SCOPES)

    cred = None

    pickle_file = f'token_{API_SERVICE_NAME}_{API_VERSION}.pickle'
    # print(pickle_file)

    # if pickle_file exists, no need to redirect into the google sign in
    if os.path.exists(pickle_file):
        with open(pickle_file, 'rb') as token:
            cred = pickle.load(token)

    # if there is no pickle file, or the pickle file is not valid
    if not cred or not cred.valid:
        if cred and cred.expired and cred.refresh_token:
            cred.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            cred = flow.run_local_server()

        with open(pickle_file, 'wb') as token:
            pickle.dump(cred, token)

    try:
        service = build(API_SERVICE_NAME, API_VERSION, credentials=cred)
        print(API_SERVICE_NAME, 'service created successfully')
        return service
    except Exception as e:
        print('Unable to connect.')
        print(e)
        return None


def create_yaml():
    dataset_folder = os.path.join(os.getcwd(), 'workspace', 'dataset')
    file_content = f"""path: '{dataset_folder}'
train: 'train/images'
val: 'valid/images'

names:
"""

    with open('collected_images/labels/classes.txt', 'r') as f:
        classes = f.readlines()
    for i, cls in enumerate(classes):
        file_content = file_content + '  ' + str(i) + f': {cls}'
    with open('workspace/custom_data.yaml', 'w') as f:
        f.write(file_content)


def strip_optimizer(f='best.pt', s=''):
    x = torch.load(f, map_location=torch.device('cpu'))
    if x.get('ema'):
        x['model'] = x['ema']
    for k in 'optimizer', 'best_fitness', 'wandb_id', 'ema', 'updates':
        x[k] = None
    x['epoch'] = -1
    x['model'].half()  # to FP16
    for p in x['model'].parameters():
        p.requires_grad = False
    torch.save(x, s or f)
    mb = os.path.getsize(s or f) / 1E6
    print(f"Optimizer stripped from {f},{(' saved as %s,' % s) if s else ''} {mb:.1f}MB")


def archive_and_upload(service):
    folder_name = 'workspace/for_cloud'
    zip_filename = 'workspace/for_cloud.zip'
    zip_file = ZipFile(zip_filename, 'w', ZIP_DEFLATED)
    for root, dirs, files in os.walk(folder_name):
        for file in files:
            file_path = os.path.join(root, file)
            zip_file.write(file_path, arcname=os.path.relpath(file_path, folder_name))
    zip_file.close()

    # delete the folder 'for_cloud' now
    shutil.rmtree('workspace/for_cloud')

    # uploading to drive
    main_folder_id = 'YOUR_FOLDER_ID'
    file_name = 'for_cloud.zip'

    file_path = f'workspace/{file_name}'
    mime_type = 'application/zip'

    file_metadata = {
        'name': file_name,
        'parents': [main_folder_id]
    }

    media = MediaFileUpload(file_path, mimetype=mime_type)
    print('start')
    while True:
        try:
            service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            break
        except:
            pass
    print('Uploaded to google drive successfully')


def download_weight(service):
    main_folder_id = 'YOUR_FOLDER_ID'

    while True:
        try:
            results = service.files().list(q=f"'{main_folder_id}' in parents and trashed = false",
                                           fields="nextPageToken, files(id, name, mimeType)").execute()
            break
        except:
            pass

    items = results.get('files', [])
    weight_file = next((item for item in items if item['name'] == 'best.pt'), None)
    weight_file_id = weight_file['id']

    while True:
        try:
            request = service.files().get_media(fileId=weight_file_id)
            break
        except:
            pass
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fd=fh, request=request)

    done = False
    while not done:
        status, done = downloader.next_chunk()
        print('Download progress {0}'.format(status.progress() * 100))

    fh.seek(0)

    with open(os.path.join('workspace', 'classifier.pt'), 'wb') as f:
        f.write(fh.read())
        f.close()


def detect_objects(filename, model):
    image = f'static/manual_detections/{filename}'
    img = cv2.resize(cv2.imread(image), (640, 480))
    cv2.imwrite(f'static/manual_detections/{filename}', img)
    new_image_results = model.predict(source=image, verbose=True, save=True)
    return new_image_results


def rotate_and_capture_images(faces=1, product_name=''):
    step_pin = 2
    dir_pin = 5
    steps_per_revolution = 200
    micro_delay = 3000

    arduino_port = 'COM3'
    arduino = serial.Serial(arduino_port, 9600, timeout=1)

    def rotate_stepper_motor():
        arduino.write(b'H')  # Send a character to indicate rotation command to Arduino
        time.sleep(0.1)
        arduino.write(b'L')
        time.sleep(0.1)

    cap = cv2.VideoCapture(0)
    cap.read()
    time.sleep(4)

    count = 1

    for i in range(1, faces+1):
        print(f'Capturing images of face {i}')
        try:
            for j in range(14):
                frame = cap.read()[1]
                cv2.imwrite(f'collected_images/images/{product_name + str(count)}.jpg', frame)
                rotate_stepper_motor()
                time.sleep(1)
                count += 1
        except (KeyboardInterrupt, SystemExit):
            print('Arduino safely closed')

        if i < faces:
            input(f'Are you ready to capture face {i + 1} : ')
            time.sleep(2)

    print("All images successfully captured\n")
    cap.release()
    arduino.close()

