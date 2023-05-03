import json
import time

import socketio

socket_io = socketio.Client()

driver_uid = 'test@test.com'  # "adept-dev@tenderclaws.com"
dashboard_url = 'ws://192.241.209.27:5050/' #'ws://localhost:5000'

responses = {
    'load_scene_recieved': False,
    'end_scene_recieved': False,
}

@socket_io.event
def on_scene_loaded(data):
    print(f'got /on_scene_loaded')
    responses['load_scene_recieved'] = True


@socket_io.event
def on_scene_complete(data):
    print(f'got /on_scene_complete')
    responses['end_scene_recieved'] = True

@socket_io.event
def on_publish(data):
    print(f'got /on_publish')


@socket_io.event
def connect():
    print(f'Connect: dashboard.url={dashboard_url} uid={driver_uid}')


@socket_io.event
def disconnect():
    print('...disconnected')


if __name__ == "__main__":
    with open('config.json', "r") as file1:
        config = json.load(file1)
        socket_io.connect(dashboard_url, auth={
            'uid': driver_uid,
            'secret': config['dashboard_password']
        }, wait_timeout=1)

        with open('test_scene.json', "r") as file2:
            # scene_json = json.load(f)
            scene_json = file2.read()

            socket_io.emit('load_scene', {'scene_json': scene_json})
            print('message:load_scene sent')

            time.sleep(3)
            if not responses['load_scene_recieved']:
                socket_io.disconnect()
                raise Exception('/load_scene not recieved ')

            time.sleep(3)
            socket_io.emit('end_scene')
            print('message:end_scene sent')

            time.sleep(3)
            if not responses['end_scene_recieved']:
                socket_io.disconnect()
                raise Exception('/end_scene not recieved ')

    socket_io.disconnect()
    exit(0)
