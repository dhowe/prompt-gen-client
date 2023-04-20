import obsws_python as obs
import PySimpleGUI as sg
import inspect
import time
import os, sys
import multiprocessing as mp

def debug(text):
    # make colorful and styled text
    print(f'\033[92m{text}\033[0m')

cl = None
    
def _write_settings(ip, port, password):
    with open('obs_settings.txt', 'w') as f:
        f.write(f'{ip} {port} {password}')

def _read_obs_settings():
    global cl, ip, port, password
    with open('obs_settings.txt', 'r') as f:
        ip, port, password = f.read().split(' ')
        print("Connecting to OBS... on ip: ", ip, " port: ", port, " password: ", password)
        try:
            cl = obs.ReqClient(ip=ip, port=port, password=password)
            return "Connected to OBS at " + ip + ":" + port
        except ConnectionRefusedError:
            return "Failed to connect to OBS at " + ip + ":" + port
    
# read argument from command line
_read_obs_settings()

# Custom theme
sg.theme("DarkTeal10")
sg.set_options(font=("Helvetica", 17))

class Scenes:
    def __init__(self):
        self.i = 0

    def cycle(self):
        self.i -= 1
        resp = cl.get_scene_list()
        scenes = resp.scenes
        n = len(scenes)

        cur_scene = cl.get_current_program_scene()
        scene = cur_scene.current_program_scene_name

        new = scenes[self.i % n]
        if new != scene:
            cl.set_current_program_scene(new['sceneName'])
            return f"Switching to new scene {new}"
        else:
            return None

def is_text(item):
    return 'text' in item['inputKind']

def _connect_to_obs():
    try:
        global cl
        ip = window['ip'].get()
        port = window['port'].get()
        password = window['password'].get()
        cl = obs.ReqClient(ip=ip, port=int(port), password=password)
        _write_settings(ip, port, password)
        message = 'Connected to OBS at ' + ip + ':' + port
    except Exception as e:
        message = 'Failed to connect to OBS at ' + ip + ':' + port + ' with password ' + password
        message += e.__str__()
    window['connected'].update(message)
    return message


def toggle_mic():
    cl.toggle_input_mute('Mic/Aux')

def show_items():
    cur_scene = cl.get_current_program_scene().current_program_scene_name
    items = cl.get_scene_item_list(cur_scene).scene_items
    return items

def show_inputs():
    inputs = cl.get_input_list().inputs
    return inputs

def show_texts():
    inputs = cl.get_input_list().inputs
    print(inputs)
    texts = [i for i in inputs if 'text' in i['inputKind']]
    texts = [source['inputName'] for source in texts]
    return texts


# def toggle_enabled(name, nothing):
#     enabled = cl.get_scene_item_enabled()

class OBS:
    def __init__(self) -> None:
        self.dialogue_dyn = 'Dialogue Dynamic'
        self.dialogue_static = 'Dialogue Normal'
        self.topic = "Topic"

    def change_subtitles(self, lines):
        n = len(lines)
        text = "\n".join(lines)
        text = text.strip()
        text, too_big = self.split(text)
        new = self.dialogue_static if too_big else self.dialogue_dyn
        old = self.dialogue_dyn if too_big else self.dialogue_static
        self.change_text(new, text)
        self.change_text(old, "")
        return f"Dialogue: {text}"
    
    def split(self, text):
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            if len(current_line + " " + word) <= 60:
                current_line += " " + word
            else:
                lines.append(current_line.strip())
                current_line = word
        
        lines.append(current_line.strip())
        
        return "\n".join(lines), len(lines) > 1

    
    def update_topic(self, new_topic):
        self.change_text(self.topic, new_topic.strip())
        return f"Topic: {new_topic}"
    
    def update_obs_connection(self, ip, port, password):
        try:
            global cl
            cl = obs.ReqClient(ip=ip, port=int(port), password=password)
            _write_settings(ip, port, password)
            message = 'Connected to OBS at ' + ip + ':' + port
        except Exception as e:
            message = 'Failed to connect to OBS at ' + ip + ':' + port + ' with password ' + password
            message += e.__str__()
        window['connected'].update(message)
        return message


    def change_text(self, name, new_text):
        if not name:
            return "Enter a text source. One of: " +  " ".join(show_texts())

        try:
            settings = cl.get_input_settings(name).input_settings
            settings['text'] = new_text
            cl.set_input_settings(name, settings, False)
            return f"'{name}' changed to '{new_text}'."
        except:
            msg = f"Failed to change '{name}' to '{new_text}'.\n"
            msg += "Available text sources: " +  show_texts()
        

obs_state = OBS()

scenes = Scenes()

# Buttons
def cycle_scenes():
    scenes.cycle()

def send_subtitles(lines):
    return obs_state.change_subtitles(lines)

def change_text(name, new_text):
    return obs_state.change_text(name, new_text)

# Automatically generate buttons based on available functions
function_buttons = []
available_functions = [(name, func) for name, func in globals().items() if callable(func) and not name.startswith("_") and name != "update_output"]
for name, func in available_functions:
    function_buttons.append(sg.Button(name, key=name, size=(12, 2), pad=((5, 5), (0, 5))))

layout = [
    [sg.Text(f"Not connected", key="connected", size=(40, 1)), sg.Button("Connect", key="_connect_to_obs")],
    [sg.Text("IP Address", size=(10, 1)), sg.InputText(ip, key="ip", size=(30, 1))],
    [sg.Text("Port", size=(10, 1)), sg.InputText(port, key="port", size=(30, 1))],
    [sg.Text("Password", size=(10, 1)), sg.InputText(password, key="password", size=(30, 1))],
    # timer
    [sg.Text("Timer", size=(10, 1)), sg.Text("15:00", key="timer", size=(30, 1))],
    [sg.Text("Status", size=(10, 1)), sg.Multiline(size=(50, 4), key="output", disabled=True)],
    [sg.Text("Field:", size=(0, 0)), sg.InputText("", key="field", size=(30, 1))],
    [sg.Text("Value:", size=(0, 0)), sg.Multiline("", key="value", size=(30, 1))],
    function_buttons[: len(function_buttons) // 2],
    function_buttons[len(function_buttons) // 2 :],
    [sg.Button("Exit", key="exit", size=(12, 2), pad=((0, 0), (0, 5)))],
]

window = sg.Window("OBS Control", layout)

def update_output(window, content):
    if content:
        print("content", str(content))
        window["output"].update(str(content))

def event_loop():
    return
    # while True:
    #     try:
    #         event, values = window.read()
    #         if event in (sg.WIN_CLOSED, "exit"):
    #             break
    #         elif event in globals():
    #             function = globals()[event]
    #             num_params = len(inspect.signature(function).parameters)
    #             if num_params == 2:
    #                 result = function(values["field"], values["value"])
    #             if num_params == 1:
    #                 result = function(values["value"])
    #             else:
    #                 result = function()
    #             update_output(window, result)
    #     except Exception as e:
    #         print(e)
    #         update_output(window, e)  
    # window.close()
