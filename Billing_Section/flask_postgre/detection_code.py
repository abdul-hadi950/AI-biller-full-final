import cv2
from ultralytics import YOLO
import pandas as pd
import socketio
import os
import time
import webbrowser

from app import cursor

model = YOLO('classifier.pt')
classes = list(model.names.values())

products_data = pd.read_csv('products.csv')
weighing_products = products_data['classname'][(products_data['is_weighing'] == True)].to_list()
disabled_products = products_data['classname'][(products_data['is_disabled'] == True)].to_list()
price_data = {}
for class_ in classes:
    if class_ not in disabled_products:
        price_data[class_] = products_data['price'][(products_data['classname'] == class_)].to_list()[0]
real_name = {}
for class_ in classes:
    if class_ not in disabled_products:
        real_name[class_] = products_data['name'][(products_data['classname'] == class_)].to_list()[0]


cap = cv2.VideoCapture(0)

print('detecting first one')
model.predict(cap.read()[1])


# socket connection to port 5000
sio = socketio.Client()
while True:
    try:
        sio.connect('http://localhost:5000/')
        break
    except:
        pass


import serial

baud_rate = 9600
port_count = 1

while True:
    arduino_port = f'COM{port_count}'
    try:
        ser = serial.Serial(arduino_port, baud_rate)
        print(f'Connected to COM{port_count}')
        break
    except:
        port_count += 1
        pass


def find_weight():
    while True:
        if ser.in_waiting > 0:
            try:
                val = abs(float(ser.readline().decode('utf-8').rstrip()))

                if val > 25:
                    break
            except:
                pass

    return val


webbrowser.open('http://127.0.0.1:3000')
print('loop started')

f = 0
s = []


try:
    while cap.isOpened():

        res, frame = cap.read()

        results = model.predict(frame, verbose=False)
        result = results[0].boxes

        if len(result) == 0:
            continue

        detected_names = []

        for i in range(len(result)):
            score = round(result[i].conf[0].tolist(), 2)
            if score > 0.9:
                class_id = int(result[i].cls[0].tolist())
                detected_names.append(classes[class_id])

        if len(detected_names) == 0:
            continue

        if f < 10:
            if len(detected_names) != len(s):
                s = detected_names
                f = 0
                continue
            s = detected_names
            f += 1
            continue

        f = 0
        s = []

        detected_names = [name for name in detected_names if name not in disabled_products]
        temp_cart = []
        for name in set(detected_names):
            product_name = real_name[name]

            if name in weighing_products:
                if len(set(detected_names)) != 1:
                    continue
                print('Going to weight after 3 seconds.')
                time.sleep(3)
                print('Weighing...')
                weight = find_weight()
                print("weight: ", weight)
                quantity = round(weight / 1000, 2)
                print("quantity: ", quantity)
            else:
                quantity = detected_names.count(name)

            price = price_data[name]

            # current product names in database
            cursor.execute("SELECT * FROM products ORDER BY product_id;")
            rows = cursor.fetchall()
            current_database_products = []
            for row in rows:
                current_database_products.append(row[1])

            if product_name not in current_database_products:
                temp_cart.append({"product_name": product_name, "quantity": quantity, "price": price})

        if len(temp_cart) > 0:
            sio.emit('data', {
                "temp_cart": temp_cart
            })
            print(temp_cart)

            time.sleep(2)   # small rest after one is successfully added

except (KeyboardInterrupt, SystemExit):

    ser.close()
    print('SERIAL CONNECTION CLOSED')

    cap.release()
    print('CAM RELEASED\n')

    print('AI BILLER TERMINATED')
