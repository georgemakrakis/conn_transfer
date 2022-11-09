
# Bruno Capuano
# start a webserver with flask in a thread
# start a different thread +1 a shared var

from flask import Flask, session
import threading
import time
import requests
from werkzeug.serving import WSGIRequestHandler

# Used to force specific rates that we want
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

counter = 0
data = ""
app = Flask(__name__)

#limiter = Limiter(app, key_func=get_remote_address)

def mainSum():
    # increment counter every 10 seconds
    global counter
    while True:
        counter = counter + 1
        t = time.localtime()
        current_time = time.strftime("%H:%M:%S", t)    
        print(str(f"{current_time} - count: {counter}"))
        # time.sleep(10)
        time.sleep(1)

def sync():
    global counter
    while True:
        count_resp = requests.get('http://192.168.108.141/counter')
        counter = int(count_resp.text)
        print(counter)
        time.sleep(5)

def startWebServer():
    WSGIRequestHandler.protocol_version = "HTTP/1.1"
    app.run(host='0.0.0.0', port=80, threaded=True)

@app.route("/")
def main():
    global counter
    current_time = time.strftime("%H:%M:%S", t)
    return str(f"Server 1 \n{current_time} – count: {counter}")

# This route will be used to syncronize the two servers
@app.route('/counter')
#@limiter.limit("1000/second", override_defaults=True)
def get_count():
    global counter
    return str(counter)

if __name__ == "__main__":
    stateThread = threading.Thread(target=mainSum)
    #stateThread = threading.Thread(target=sync)
    stateThread.daemon = True
    stateThread.start()

    webThread = threading.Thread(target=startWebServer)
    webThread.start()
