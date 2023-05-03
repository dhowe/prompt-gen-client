import socketio
import obs_control

sio = socketio.Client()

driver_uid = "test@test.com"
dashboard_url = 'ws://192.241.209.27:5050' #'ws://localhost:5050'
global_driver = driver_uid

@sio.event
def connect():
    print(f'Connecting to Dashboard... at {dashboard_url}, uid: {driver_uid}')


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
    print(f'got /on_load_scene')

@sio.event
def on_scene_complete(data):
    print(f'got /on_end_scene')


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
    is_driver, message = is_driver(data)
    if is_driver:
        try:
            messages = data.get("data", [])
            message_contents = [message.get("content", "") for message in messages]
            did_update, message = obs_control.send_subtitles(message_contents)
        except Exception as e:
            print(message, e)
    sio.emit('text_updated', {'updated': did_update, 'message': message, "field": "subtitles"})


# @sio.event
# def update_obs(data):
#     connected = False
#     try:
#         message = obs_control.update_obs_connection(
#             data.get("ip"),
#             data.get("port"),
#             data.get("password")
#         )
#         connected = True
#     except Exception as e:
#         message = str(e)

#     sio.emit('obs_connected', {'connected': connected, 'message': message})

 
# @sio.eventcurrently not supporting the dashboard changing the driver
def update_driver(data):
    # Change the username that has control over the stream.
    # All messages they send to the publish queue
    # will be displayed at the OBS instance
    global global_driver
    global_driver = data if isinstance(data, str) else data.get("driver", global_driver)
    message = f'new driver: {global_driver}'
    return message


def is_driver(data):
    # helper function to check if the currently assigned driver is the one
    # the message comes from
    is_driver = (data == global_driver) or \
                isinstance(data, dict) and data.get("author") == global_driver
    return is_driver, f"{data.get('author')} is not the driver" if not is_driver else ""

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

def listen():
    # DH: added some auth here
    # sio.connect('ws://192.241.209.27:5050', auth={'uid': uid, 'secret': obs_control.secret()}, wait_timeout=1)
    sio.connect(dashboard_url, auth={'uid': driver_uid, 'secret': obs_control.secret()}, wait_timeout=1)
    sio.wait()