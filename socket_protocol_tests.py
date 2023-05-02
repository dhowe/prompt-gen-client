import json
import time

import socketio

socket_io = socketio.Client()

driver_uid = 'test@test.com'  # "adept-dev@tenderclaws.com"
dashboard_url = 'ws://localhost:5000'


@socket_io.on('remote_load_scene')
def remote_load_scene(data):
    print(f'got /remote_load_scene')


@socket_io.on('remote_end_scene')
def remote_load_scene(data):
    print(f'got /remote_end_scene')


@socket_io.event
def connect():
    print(f'Connecting to Dashboard... at {dashboard_url}, uid: {driver_uid}')


@socket_io.event
def disconnect():
    print('...disconnected')


if __name__ == "__main__":
    with open('obs_config.json', "r") as file1:
        config = json.load(file1)
        socket_io.connect(dashboard_url, auth={
            'uid': driver_uid,
            'secret': config['dashboard_password']
        }, wait_timeout=1)
        with open('test_scene.json', "r") as file2:
            # scene_json = json.load(f)
            scene_json = file2.read()
            socket_io.emit('load_scene', {'scene_json': scene_json})
            print('load_scene sent');
            time.sleep(5)
            socket_io.emit('end_scene')
            print('end_scene sent');
            time.sleep(5)
            socket_io.disconnect()

    exit(0)
