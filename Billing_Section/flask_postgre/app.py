from flask import Flask, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

from flask_socketio import SocketIO, emit

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:3000"}})
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://postgres:password@localhost/databaseName"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

socketio = SocketIO(app, cors_allowed_origins="*")

db = SQLAlchemy(app)


# cursor is used to manipulate database using SQL queries
with app.app_context():
    conn = db.engine.raw_connection()
    cursor = conn.cursor()


# WHEN A CLIENT CONNECTS
@socketio.on('connect')
def connected():
    print('\n' ,f"Client {request.sid} is connected.", '\n')
    emit('connect', f"Client {request.sid} is connected.", broadcast=True)


# WHEN A CLIENT DISCONNECTS
@socketio.on('disconnect')
def disconnected():
    print('\n' ,f"Client {request.sid} is disconnected.", '\n')
    emit('disconnect', f"Client {request.sid} disconnected.", broadcast=True)


# get all products from database and emits it to clients
def get_all_products_and_emit():
    cursor.execute("SELECT * FROM products ORDER BY product_id;")
    rows = cursor.fetchall()
    results = []
    for row in rows:
        results.append({
            "product_id": row[0],
            "product_name": row[1],
            "quantity": row[2],
            "price": row[3]
        })

    emit('data', {"results": results}, broadcast=True)


# WHEN NEW PRODUCTS GET DETECTED
@socketio.on('data')
def addproduct(data):
    # adds product to database
    temp_cart = data['temp_cart']
    for item in temp_cart:
        cursor.execute(f"INSERT INTO products(product_name, quantity, price) VALUES('{item['product_name']}', {item['quantity']}, {item['price']})")

    conn.commit()

    get_all_products_and_emit()


# WHEN QUANTITY GETS CHANGED BY USER (decrement or increment)
@socketio.on('change_quantity')
def change_quantity(data):
    cursor.execute(f"UPDATE products SET quantity={data['Quantity']} WHERE product_id={data['Id']}")
    conn.commit()

    get_all_products_and_emit()


# WHEN USER DELETES A SINGLE PRODUCT
@socketio.on('delete_product')
def delete_product(data):
    cursor.execute(f"DELETE FROM products WHERE product_id={data['Id']}")
    conn.commit()

    get_all_products_and_emit()


# WHEN USER CLEARS THE CART
@socketio.on('delete_all')
def delete_all():
    cursor.execute("DELETE FROM products")
    cursor.execute("SELECT setval('products_product_id_seq', 1, false);")
    conn.commit()


if __name__ == '__main__':
    # products table is cleared before starting the server
    cursor.execute("DELETE FROM products")
    cursor.execute("SELECT setval('products_product_id_seq', 1, false);")
    conn.commit()
    
    socketio.run(app, debug=True)
