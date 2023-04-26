import threading
import socketio
import obs_control

sio = socketio.Client()

uid = 'test@test.com'
dashboard_url = 'ws://192.241.209.27:5050' #'ws://localhost:5050'
global_driver = uid

@sio.event
def connect():
    print(f'Connecting to Dashboard... at {dashboard_url}, uid: {uid}')


@sio.event
def on_publish(data):
    print('/published: ', data)
    update_subtitles(data)


@sio.event
def on_generate(data):
    print('/generated: ', data)
    # sio.emit('my response', {'response': 'my response'})


@sio.event
def update_topic(data):
    updated = False
    driver, message = authenticate_driver(data)
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
    updated = False
    driver, message = authenticate_driver(data)
    if driver:
        try:
            message = obs_control.send_subtitles(data.get("content", []))
            updated = True
        except Exception as e:
            message = str(e)
            print(message)
    sio.emit('text_updated', {'updated': updated, 'message': message, "field": "subtitles"})


@sio.event
def update_driver(data):
    # Change the username that has control over the stream.
    # All messages they send to the publish queue
    # will be displayed at the OBS instance
    driver = data.get("driver", global_driver)
    print(f'new driver: {driver}')


def authenticate_driver(data):
    is_driver = (data == global_driver) or \
                isinstance(data, dict) and data.get("author") == global_driver
    return is_driver, f"{data.get('author')} is not the driver" if not is_driver else ""


@sio.event
def update_obs(data):
    connected = False
    try:
        message = obs_control.update_obs_connection(
            data.get("ip"),
            data.get("port"),
            data.get("password")
        )
        connected = True
    except Exception as e:
        message = str(e)

    sio.emit('obs_connected', {'connected': connected, 'message': message})


@sio.event
def disconnect():
    print('...disconnected')
    
def listen():
    # DH: added some auth here
    # sio.connect('ws://192.241.209.27:5050', auth={'uid': uid, 'secret': obs_control.secret()}, wait_timeout=1)
    sio.connect(dashboard_url, auth={'uid': uid, 'secret': obs_control.secret()}, wait_timeout=1)
    sio.wait()


if __name__ == '__main__':
    gui_thread = threading.Thread(target=obs_control.event_loop)
    listen_thread = threading.Thread(target=listen)
    gui_thread.start()
    listen_thread.start()
    gui_thread.join()
    listen_thread.join()