import json
import os
import socket
from datetime import datetime
from urllib.parse import urlparse

import requests
from flask import Flask, g, render_template, request, send_from_directory
from geopy import distance as gp
from humanize import naturaldelta

UPLOAD_FOLDER = 'files'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


app = Flask(__name__)
app.debug = True
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# Self IP
SELF_IP = requests.get('https://api.ipify.org').text

# VPS locations
LOCATIONS = {
    '18.225.10.204': {
        'name': 'VPS1',
        'location': 'Dublin',
        'geo': (40.0992, -83.1141)
    },
    '3.75.230.137': {
        'name': 'VPS2',
        'location': 'Frankfurt',
        'geo': (50.1109, 8.68213)
    },
    '54.169.236.24': {
        'name': 'VPS3',
        'location': 'Singapore',
        'geo': (1.28009, 103.851)
    }
}


@app.before_request
def record_upload_time():
    g.start_time = datetime.now()


def get_nearest_ip(target_ip, locations):
    target_ip_geo = requests.get(f'http://ip-api.com/json/{target_ip}').json()
    print(target_ip)
    target_ip_geo = (target_ip_geo['lat'], target_ip_geo['lon'])
    nearest_ip = None
    min_distance = float('inf')

    for ip, data in locations.items():
        distance = gp.distance(data['geo'], target_ip_geo)
        if distance < min_distance:
            min_distance = distance
            nearest_ip = ip

    return nearest_ip


def get_file_host_ip(file_link):
    file_link = urlparse(file_link).netloc
    return socket.gethostbyname(file_link)


def get_file_extension(file_link):
    return file_link.rstrip('/').split('/')[-1]


@app.route('/download/<path:file_name>/')
def download(file_name):
    nearest_vps = get_nearest_ip(request.remote_addr, LOCATIONS)
    if nearest_vps != SELF_IP:
        return requests.get(f'http://{nearest_vps}/download/{file_name}')
    return send_from_directory(app.config['UPLOAD_FOLDER'], file_name, as_attachment=True)


@app.route('/upload/', methods=['POST'])
def upload():
    file_link = request.json['file_link']
    r = requests.get(file_link)
    file_name = get_file_extension(file_link)
    with open(f'{UPLOAD_FOLDER}/{file_name}', 'wb') as file:
        file.write(r.content)

    upload_time = naturaldelta(datetime.now() - g.start_time)
    upload_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    location = LOCATIONS[SELF_IP]

    res = {
        'vps': f'{location["name"]} {location["location"]}',
        'vps_ip': SELF_IP,
        'upload_time': upload_time,
        'upload_date': upload_date,
        'file_link': file_link,
        'file_name': file_name
    }

    return json.dumps(res)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        try:
            file_link = request.form["file_url"]
            file_location = get_file_host_ip(file_link)
            nearest_vps = get_nearest_ip(file_location, LOCATIONS)
            if nearest_vps == SELF_IP:
                result = upload(file_link)
            else:
                result = requests.post(
                    f'http://{nearest_vps}/upload/',
                    data=json.dumps({'file_link': file_link})
                ).content
            return render_template('index.html', message=result)

        except socket.gaierror:
            return render_template('index.html', error='Invalid hostname')
    return render_template('index.html')


if __name__ == '__main__':
    app.run()
