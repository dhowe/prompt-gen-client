import json
import time

import socketio

socket_io = socketio.Client()

driver_uid = 'test@test.com'  # "adept-dev@tenderclaws.com"
# dashboard_url = 'ws://localhost:5000'
dashboard_url = "ws://192.241.209.27:5050"


@socket_io.event
def on_scene_loaded(data):  # this one is pending
    print(f'got /on_load_scene')


@socket_io.event
def on_scene_complete(data):
    print(f'got /on_end_scene')


@socket_io.event
def connect():
    print(f'Connect: dashboard.url={dashboard_url} uid={driver_uid}')


@socket_io.event
def disconnect():
    print('...disconnected')


if __name__ == "__main__":
    with open('../config.json', "r") as file1:
        config = json.load(file1)
        socket_io.connect(dashboard_url, auth={
            'uid': driver_uid,
            'secret': config['dashboard_password']
        }, wait_timeout=1)
        with open('test_scene.json', "r") as file2:
            # scene_json = json.load(f)
            scene_json = file2.read()
            socket_io.emit('load_scene', {'scene_json': scene_json})
            print('message:load_scene sent');
            time.sleep(5)
            socket_io.emit('end_scene')
            print('message:end_scene sent');
            time.sleep(5)
            socket_io.disconnect()
    exit(0)
