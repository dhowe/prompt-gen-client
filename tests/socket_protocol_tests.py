import json
import os.path
import time

import socketio

socket_io = socketio.Client()

driver_uid = 'test@test.com'
# driver_uid = "alex.calderwood@tenderclaws.com"

dashboard_url = 'ws://localhost:5000'
#dashboard_url = 'ws://192.241.209.27:5050/'  #

responses = {
    'load_scene_recieved': False,
    'end_scene_recieved': False,
    'on_connect': '',
}


@socket_io.event
def on_scene_loaded(packet):
    print(f'got /on_scene_loaded scene_name={packet["data"]["scene_name"]}')
    responses['load_scene_recieved'] = True


@socket_io.event
def on_scene_complete(packet):
    print(f'got /on_scene_complete scene_name={packet["data"]["scene_name"]}')
    responses['end_scene_recieved'] = True


@socket_io.event
def on_error(packet):
    '''
    NOTE: server will send this event on serious error
    It can only be overridden be sending a new load_scene msg
    '''
    msg = packet["data"]["message"]
    print(f'got /on_error message="{msg}"')


@socket_io.event
def on_publish(packet):
    content = packet['data'][0]['content']
    print(f'got /on_publish content="{content[0:80]}..."')

@socket_io.event
def on_publish_now(packet):
    content = packet['data'][0]['content']
    print(f'got /on_publish_now content="{content[0:80]}..."')



@socket_io.event
def on_connect(data):
    print(f'got /on_connect status={data["status"]}')
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

    # socket_io.wait()

    if 1:
        # load json scene file
        file_name = 'test_scene.json'
        scene_json = open(os.path.dirname(__file__) + f'/../{file_name}').read()
        socket_io.emit('load_scene', {'scene_json': scene_json, 'scene_name': file_name})
        print(f'sent /load_scene {file_name}')

        # verify we've load scene file
        time.sleep(1)
        if not responses['load_scene_recieved']:
            socket_io.disconnect()
            raise Exception('/load_scene not recieved ')
        if 0:
            time.sleep(10)

            # end the scene
            socket_io.emit('end_scene')
            print('sent /end_scene')

            # verify the scene is ended
            time.sleep(1)
            if not responses['end_scene_recieved']:
                socket_io.disconnect()
                raise Exception('/end_scene not recieved ')
        else:
            socket_io.wait()


time.sleep(5)
socket_io.disconnect()
exit(0)
