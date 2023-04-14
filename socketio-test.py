import socketio

sio = socketio.Client()
uid = 'test@test.com'

@sio.event
def connect():
    print(f'connected as {uid}...')


@sio.event
def on_publish(data):
    print('/published: ', data)


@sio.event
def on_generate(data):
    print('/generated: ', data)
    # sio.emit('my response', {'response': 'my response'})


@sio.event
def disconnect():
    print('...disconnected')


sio.connect('ws://192.241.209.27:5050', auth={'uid': uid})
#sio.connect('ws://localhost:5050', auth={'uid': uid}, wait_timeout=1)
sio.wait()
