import json, time
import socketio
import gui
import config
from obs_control import send_subtitles

sio = socketio.Client()

driver_uid = config.get_config_value("dashboard_user")
driver_password = config.get_config_value("dasboard_password")
dashboard_url = config.get_config_value("dashboard_url")
# dashboard_url = 'ws://192.241.209.27:5050' #'ws://localhost:5050'

responses = {
    'load_scene_recieved': 0,
    'end_scene_recieved': 0,
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
        gui.message("Failed to connect to Dashboard: "+ responses['on_connect'])
        gui.update_driver(False, driver_uid)
    else:
        gui.message("Connected to Dashboard")
        gui.update_driver(True, driver_uid)
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
    responses['load_scene_recieved'] += 1

@sio.event
def on_scene_complete(data):
    print(f'got /on_scene_complete')
    responses['end_scene_recieved'] += 1

@sio.event
def on_error(packet):
    '''
    NOTE: server will send this event on serious error
    It can only be overridden be sending a new load_scene msg
    '''
    msg = packet["data"]["message"]
    print(f'got /on_error message="{msg}"')
    gui.message(f"Server Error: {msg}")


def is_driver(data):
    # helper function to check if the currently assigned driver is the one
    # the message comes from
    is_driver = (data == driver_uid) or \
                isinstance(data, dict) and data.get("author") == driver_uid
    return is_driver, f"{data.get('author')} is not the driver" if not is_driver else ""


@sio.event
def update_subtitles(data):
    did_update = False
    driver, message = is_driver(data)
    print("driver", driver, "message", message)
    if driver:
        try:
            messages = data.get("data", [])
            message_contents = [message.get("content", "") for message in messages]
            did_update, message = send_subtitles(message_contents)
        except Exception as e:
            print(message, e)
    sio.emit('text_updated', {'updated': did_update, 'message': message, "field": "subtitles"})

@sio.event
def disconnect():
    print('...disconnected')

 
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
def start_show(scene_json, scene_name=None):
    if sio.connected:
        try:
            # Set the show mode to automode (so it starts in the dashboard)
            scene_json_dict = json.loads(scene_json)
            scene_json_dict["uistate"]["automode"] = True
            scene_json = json.dumps(scene_json_dict)
        except Exception as e:
            message = "Error failed to set automode: "+ str(e)
            gui.message(message)

        scene_name = scene_name or "Untitled"
        try:
            automode = f"Automode: {scene_json_dict['uistate']['automode']}"
            print("AUTOMODE: ", automode)
            gui.message(automode)
        except Exception:
            gui.message("Error fetching automode")

        sio.emit('load_scene', {'scene_json': scene_json, 'scene_name': scene_name})


    
def stop_show():
    if sio.connected:
        sio.emit('end_scene')


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

    
    