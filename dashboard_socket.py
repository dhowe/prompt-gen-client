import config
import gui
import json
import socketio
import time

from obs_control import send_subtitles, send_subtitles_now

sio = socketio.Client()

dashboard_load_scene_counter = 0
dashboard_status = 'not connected'
dashboard_url = config.get_value("dashboard_url")
dashboard_user = config.get_value("dashboard_user")
dashboard_secret = config.get_value("dashboard_password")


@sio.event
def connect():
    pass


@sio.event
def on_connect(data):
    global dashboard_status
    dashboard_status = data['status']
    msg = f'Dashboard @{dashboard_url} {dashboard_user}'
    if data['status'] != 'connected':
        msg += f" *ERROR* \"{data['error']}\""
    else:
        msg += f" {data['status']}"
    gui.update_driver(dashboard_status, dashboard_user)
    gui.message(msg)
    print(msg)


@sio.event
def on_publish(payload):
    # print('/on_publish: ', payload['data'][0]['content'])
    update_subtitles(payload)


@sio.event
def on_publish_now(data):
    print('/on_publish_now: ', data)
    update_subtitles(data, True)


@sio.event
def on_generate(data):
    print('/generated: ', data)
    # sio.emit('my response', {'response': 'my response'})


@sio.event
def on_scene_loaded(data):
    print(f'/on_scene_loaded')
    global dashboard_load_scene_counter
    dashboard_load_scene_counter += 1


@sio.event
def on_scene_complete(data):
    print(f'/on_scene_complete')


@sio.event
def on_error(packet):
    '''
    NOTE: server will send this event on serious error
    It can only be overridden be sending a new load_scene msg
    '''
    msg = packet["data"]["message"]
    print(f'/on_error message="{msg}"')
    gui.message(f"Server Error: {msg}")


def is_driver(data):
    # helper function to check if the currently assigned driver is the one
    # the message comes from
    is_driver = (data == dashboard_user) or \
                isinstance(data, dict) and data.get("author") == dashboard_user
    return is_driver, f"{data.get('author')} is not the driver" if not is_driver else ""


@sio.event
def update_subtitles(data, immediate=False):
    did_update = False
    driver, message = is_driver(data)
    # print("driver", driver, "message", message)
    if driver:
        try:
            messages = data.get("data", [])
            message_contents = [message.get("content", "") for message in messages]
            if immediate:
                did_update, message = send_subtitles_now(message_contents)
            else:
                did_update, message = send_subtitles(message_contents)
        except Exception as e:
            print('ERROR', message, e)
    sio.emit('text_updated', {'updated': did_update, 'message': message, "field": "subtitles"})


@sio.event
def disconnect():
    print('...disconnected')


def update_driver(driver, password):
    # Change the user controlling the stream: what they publish will display on OBS
    global dashboard_user, dashboard_secret
    dashboard_user = driver
    dashboard_secret = password
    message = f"new driver: {dashboard_user} secret={''.join(['*' for _ in dashboard_secret])}"
    return message


# Events we emit
def start_show(scene_json, scene_name=None):
    if sio.connected:
        force_automode = config.get_value("automode", True)
        try:
            # Set the show mode to automode (so it starts in the dashboard)
            scene_json_dict = json.loads(scene_json)
            if force_automode:
                scene_json_dict["uistate"]["automode"] = True
            msg = f"AUTOMODE={scene_json_dict['uistate']['automode']}"
            scene_json = json.dumps(scene_json_dict)
        except Exception as e:
            msg = "ERROR: failed to set automode: " + str(e)

        sio.emit('load_scene', {'scene_json': scene_json, 'scene_name': scene_name})
    else:
        msg = "ERROR: Failed to start show, dashboard not connected"

    print(msg)
    gui.message(msg)


def stop_show():
    if sio.connected: sio.emit('end_scene')


def manual_disconnect():
    try:
        sio.disconnect()
    except Exception as e:
        print("Disconnected")


def listen():
    print('Connecting to dashboard...')
    connected = False
    for i in range(1, 4):
        if not connected:
            try:
                # attempt to connect
                sio.connect(dashboard_url, auth={
                    'uid': dashboard_user,
                    'secret': dashboard_secret,
                }, wait_timeout=1)
                # check that we're connected
                time.sleep(.1)
                if not dashboard_status == 'connected':
                    sio.disconnect()
                    raise Exception(f'/connect failed with status={dashboard_status}')
                connected = True
            except Exception as e:
                print(f'Try {i}', 'Failed to connect: ', e)

    sio.wait()
