import socketio

sio = socketio.Client()
sio.connect('http://localhost:5000')

#sio.emit('message', {'from': 'client'})


@sio.on('on_publish')
def response(data):
    print('generation_complete')
    print(data)  # {'from': 'server'}

    sio.disconnect()
    exit(0)
