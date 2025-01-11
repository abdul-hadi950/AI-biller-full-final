from flask import Flask, render_template, request
import os
import webview
import signal
import threading
import shutil

app = Flask(__name__)


@app.route('/')
def home():
    return "<h2>THIS IS THE PAGE TO MANAGE THE MAIN PRODUCTS DATABASE<br>NOT SET FOR NOW <br>UPDATE csv MANUALLY FOR NOW</h2>"


def exit_gracefully(signum, frame):
    exit()


def run_flask():
    app.run(debug=True, use_reloader=False, port=5002)


# Start Flask app in a new thread
flask_thread = threading.Thread(target=run_flask)

if __name__ == '__main__':
    signal.signal(signal.SIGTERM, exit_gracefully)
    flask_thread.start()

window = webview.create_window('AI Biller Detect', 'http://localhost:5002/')

webview.start()


os.kill(os.getpid(), signal.SIGTERM)
