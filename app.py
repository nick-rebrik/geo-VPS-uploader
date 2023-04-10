from flask import Flask
import socket


app = Flask(__name__)
app.debug = True


# VPS locations
LOCATIONS = {
    '18.225.10.204': 'VPS1 Frankfurt 18.225.10.204',
    '3.75.230.137': 'VPS2 Frankfurt 3.75.230.137',
    '54.169.236.24': 'VPS3 Frankfurt 54.169.236.24'
}


@app.route('/', methods=['GET', 'POST'])
def index():
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    return LOCATIONS[ip_address]


@app.route('/download/<path:file>/')
def download(file):
    pass


@app.route('/upload/', methods=['POST'])
def upload():  # Make API endpoint ot download files
    pass


if __name__ == '__main__':
    app.run()
