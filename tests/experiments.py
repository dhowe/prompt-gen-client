# A placeholder for functions that are being tested

# # start a 15 min timer
# # when timer is done, switch to a scene
# def go_to_show_timer():
#     print("Starting timer for 15 minutes...")
#     p = mp.Process(target=_timer)
#     p.start()

# def _timer():
#     # set the countdown every second
#     for i in range(15 * 60):
#         time.sleep(1)
#         display = f"{15 - i // 60}:{60 - i % 60}"
#         window['timer'].update(display)
#         print(display)
#     cl.set_current_program_scene("Scene")
#     time.sleep(0.1 * 60)
#     cl.set_current_program_scene("Cutscene")

# def change_text(name, new_text):
#     return obsc.change_text(name, new_text)

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


# def update_driver(values):
#     global uid
#     driver_uid = window['driver_uid'].get()
#     event_queue.put("update_driver", values)
#     return 

# def update_drvier():
#     uid = window["uid"].get()
#     return f"New Driver UID: {uid}"

# def toggle_enabled(name, nothing):
#     enabled = cl.get_scene_item_enabled()

def change_text(self, name, new_text):
    if not name:
        return "Enter a text source. One of: " + " ".join(show_texts())

    try:
        settings = self.cl.get_input_settings(name).input_settings
        settings['text'] = new_text
        self.cl.set_input_settings(name, settings, False)
        return f"'{name}' changed to '{new_text}'."
    except:
        msg = f"Failed to change '{name}' to '{new_text}'.\n"
        msg += "Available text sources: " + " ".join(show_texts())

def toggle_mic():
    cl.toggle_input_mute('Mic/Aux')

def animate_text():
    cur_scene = cl.get_current_program_scene().current_program_scene_name
    items = cl.get_scene_item_list(cur_scene).scene_items
    texts = [i for i in items if i['inputKind'] == 'text_ft2_source_v2']

    name = texts[1]['sourceName']
    id = texts[1]['sceneItemId']

    transform = cl.get_scene_item_transform("Scene", id).scene_item_transform
    
    print(str(transform))
    x = transform['positionX']

    for i in range(50):
        x += 1
        transform['positionX'] = x
        cl.set_scene_item_transform("Scene", id, transform)
        time.sleep(0.1)
    
    
def upload_scene():
    import socketio, os
    file_name = 'test_scene.json'
    scene_json = open(os.path.dirname(__file__) + f'/../{file_name}').read()
    socket_io.emit('load_scene', {'scene_json': scene_json, 'scene_name': file_name})
    print(f'sent /load_scene {file_name}')

if __name__ == "__main__":
    upload_scene()