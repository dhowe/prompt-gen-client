import json
import os.path
import time

import socketio

socket_io = socketio.Client()

driver_uid = 'test@test.com'  # "adept-dev@tenderclaws.com"
dashboard_url = 'ws://localhost:5000'  # 'ws://192.241.209.27:5050/' #

responses = {
    'load_scene_recieved': False,
    'end_scene_recieved': False,
    'on_connect': '',
}


@socket_io.event
def on_scene_loaded(data):
    print(f'got /on_scene_loaded')
    responses['load_scene_recieved'] += 1


@socket_io.event
def on_scene_complete(data):
    print(f'got /on_scene_complete')
    responses['end_scene_recieved'] = True


@socket_io.event
def on_publish(data):
    print(f'got /on_publish', data)


@socket_io.event
def connect():
    print(f'Connecting... dashboard.url={dashboard_url} uid={driver_uid}')


@socket_io.event
def on_connect(data):
    # print(f'got /on_connect status={data["status"]}')
    responses['on_connect'] = data['status']
    if data['status'] != 'connected':
        responses['on_connect'] = data['error']


@socket_io.event
def disconnect():
    print('...disconnected')


if __name__ == "__main__":
    config = json.load(open(os.path.dirname(__file__) + '/../config.json'))

    # attempt to connect
    socket_io.connect(dashboard_url, auth={
        'uid': driver_uid,
        'secret': config['dashboard_password']
    }, wait_timeout=1)

    # check that we're connected
    time.sleep(1)
    if responses['on_connect'] != 'connected':
        socket_io.disconnect()
        raise Exception(f'/connect failed with status={responses["on_connect"]}')

    # load json scene file
    scene_json = open(os.path.dirname(__file__) + '/test_scene.json').read()
    socket_io.emit('load_scene', {'scene_json': scene_json})
    print('message:load_scene sent')

    # verify we've load scene file
    time.sleep(1)
    if not responses['load_scene_recieved']:
        socket_io.disconnect()
        raise Exception('/load_scene not recieved ')

    time.sleep(5)

    # end the scene
    socket_io.emit('end_scene')
    print('message:end_scene sent')

    # verify the scene is ended
    time.sleep(1)
    if not responses['end_scene_recieved']:
        socket_io.disconnect()
        raise Exception('/end_scene not recieved ')

# socket_io.disconnect()
# exit(0)
