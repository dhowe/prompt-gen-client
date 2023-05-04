import socketio
import obs_control
import config
import time

sio = socketio.Client()

driver_uid = config.get_config_value("dashboard_user")
driver_password = config.get_config_value("dasboard_password")
dashboard_url = config.get_config_value("dashboard_url")
# dashboard_url = 'ws://192.241.209.27:5050' #'ws://localhost:5050'

responses = {
    'load_scene_recieved': False,
    'end_scene_recieved': False,
    'on_connect': '',
}

@sio.event
def connect():
    print(f'Connecting to Dashboard... at {dashboard_url}, uid: {driver_uid}')


@sio.event
def on_connect(data):
    print(f'got /on_connect status={data["status"]}')
    responses['on_connect'] = data['status']
    if data['status'] != 'connected':
        responses['on_connect'] = data['error']
        obs_control.update_output_better("Failed to connect to Dashboard: "+ responses['on_connect'])
        obs_control.update_driver(False)
    else:
        obs_control.update_output_better("Connected to Dashboard")
        obs_control.update_driver(True)
        print(f"Connected to Dashboard", responses['on_connect'])


@sio.event
def on_publish(data):
    print('/published: ', data)
    update_subtitles(data)


@sio.event
def on_generate(data):
    print('/generated: ', data)
    # sio.emit('my response', {'response': 'my response'})

@sio.event
def on_scene_loaded(data):  # this one is pending
    print(f'got /on_scene_loaded')

@sio.event
def on_scene_complete(data):
    print(f'got /on_scene_complete')


def is_driver(data):
    # helper function to check if the currently assigned driver is the one
    # the message comes from
    is_driver = (data == driver_uid) or \
                isinstance(data, dict) and data.get("author") == driver_uid
    return is_driver, f"{data.get('author')} is not the driver" if not is_driver else ""


@sio.event
def update_topic(data):
    updated = False
    driver, message = is_driver(data)
    field = "topic"
    if driver:
        try:
            message = obs_control.change_text(field, data.get("content", ""))
            updated = True
        except Exception as e:
            message = str(e)
            print(message)
    sio.emit('text_updated', {'updated': updated, 'message': message, "field": field})


@sio.event
def update_subtitles(data):
    did_update = False
    driver, message = is_driver(data)
    if driver:
        try:
            messages = data.get("data", [])
            message_contents = [message.get("content", "") for message in messages]
            did_update, message = obs_control.send_subtitles(message_contents)
        except Exception as e:
            print(message, e)
    sio.emit('text_updated', {'updated': did_update, 'message': message, "field": "subtitles"})


 
def update_driver(driver, password):
    # Change the username that has control over the stream.
    # All messages they send to the publish queue
    # will be displayed at the OBS instance
    global driver_uid, driver_password
    driver_uid = driver
    driver_password = password
    message = f"new driver: {driver_uid} and password {''.join(['*' for _ in driver_password])}"
    return message

# Events we emit
def start_show(scene_json):
    if sio.connected:
        sio.emit('load_scene', {'scene_json': scene_json})
    
def stop_show():
    if sio.connected:
        sio.emit('end_scene')

@sio.event
def disconnect():
    print('...disconnected')

def manual_disconnect():
    try:
        sio.disconnect()
    except Exception as e:
        print("Disconnected")

def listen():
    # attempt to connect
    sio.connect(dashboard_url, auth={
        'uid': driver_uid,
        'secret': driver_password,
    }, wait_timeout=1)
    
    
    # check that we're connected
    time.sleep(1)
    if responses['on_connect'] != 'connected':
        sio.disconnect()
        raise Exception(f'/connect failed with status={responses["on_connect"]}')

    sio.wait()

    
    