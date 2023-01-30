from flask import Flask

app = Flask(__name__)

def main():
    # app.run(host='0.0.0.0', port=8080)
    app.run(host='0.0.0.0')

@app.route('/')
def hello():
    return 'Hello, World! 2'


if __name__ == "__main__":
    main()
