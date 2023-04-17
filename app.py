import json
import os
import socket
from datetime import datetime
from urllib.parse import urlparse

import requests
from flask import Flask, g, redirect, render_template, request, send_file, send_from_directory, url_for
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


@app.route('/nearest_vps/')
def get_nearest_vps():
    nearest_vps = get_nearest_ip(request.remote_addr, LOCATIONS)
    vps_name = f'{LOCATIONS[nearest_vps]["name"]} {LOCATIONS[nearest_vps]["location"]}'
    return json.dumps({
        'nearest_vps': nearest_vps,
        'vps_name': vps_name
    })


@app.route('/download/', methods=['POST'])
def download():
    data = request.json
    file_name = data['file_name']
    vps = data['vps'] if data['vps'] else SELF_IP

    if vps == SELF_IP:
        return send_file(f'{UPLOAD_FOLDER}/{file_name}', as_attachment=True)

    r = requests.post(
        url=f'http://{vps}/download/',
        data=json.dumps({'file_name': file_name}),
        headers={'Content-Type': 'application/json'}
    )
    print(r.content)
    return r.content


@app.route('/upload/', methods=['POST'])
def upload():
    data = request.json

    file_link = data['file_link']
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

    if data['replicate']:
        for location in LOCATIONS.keys():
            if location != SELF_IP:
                try:
                    requests.post(
                        url=f'http://{location}/upload/',
                        data=json.dumps({'file_link': file_link, 'replicate': False}),
                        headers={'Content-Type': 'application/json'}
                    )
                except Exception:
                    pass

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
                    url=f'http://{nearest_vps}/upload/',
                    data=json.dumps({'file_link': file_link, 'replicate': True}),
                    headers={'Content-Type': 'application/json'}
                ).content
            result = json.loads(result)
            return render_template('index.html', message=result)

        except socket.gaierror:
            return render_template('index.html', error='Invalid hostname')
    return render_template('index.html')


if __name__ == '__main__':
    app.run()
