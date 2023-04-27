import obsws_python as obs
import PySimpleGUI as sg # https://python.libhunt.com/pysimplegui-alternatives
import inspect
import multiprocessing as mp
import queue, threading, time

# Create a queue to communicate between threads
event_queue = queue.Queue()

def debug(text):
    # make colorful and styled text
    print(f'\033[92m{text}\033[0m')

# Custom theme
sg.theme("LightGray1")
sg.set_options(font=("Helvetica", 16))

class OBSController:
    def __init__(self) -> None:
        self.dialogue_dyn = 'Dialogue Dynamic'
        self.dialogue_static = 'Dialogue Normal'
        self.topic = "Topic"
        self.ip = None
        self.port = None
        self.password = None
        self.cl = None
        self.connected = False

        self.subtitles_queue = queue.Queue()
        self.subtitles_thread = threading.Thread(target=self.subtitles_process)
        self.subtitles_thread.start()

    def subtitles_process(self):
        while True:
            try:
                text = self.subtitles_queue.get(timeout=1)
                self.change_text(self.dialogue_dyn, text)
                window['subtitles'].update(value=text)
                time.sleep(5)
            except queue.Empty:
                pass
    
    def _write_settings(self, ip, port, password):
        with open('obs_settings.txt', 'w') as f:
            f.write(f'{ip} {port} {password}')

    def _read_obs_settings_from_file(self):
        with open('obs_settings.txt', 'r') as f:
            ip, port, password= f.read().split(' ')
            return self.connect(ip, port, password)
            
    def connect(self, ip, port, password):
        print("Connecting to OBS... at ip:", ip, "port:", port, "password:", password)
        connected = False
        message = ""
        print("ip", ip, self.ip)
        try:
            self.cl = obs.ReqClient(ip=ip, port=port, password=password)
            self.ip = ip
            self.port = port 
            self.password = password
            self.connected = True
            connected, message = True, "Connected to OBS at " + ip + ":" + port
        except ConnectionRefusedError:
            self.ip = ip if not self.ip else self.ip
            self.port = port if not self.port else self.port
            self.password = password if not self.password else self.password
            connected, message = False, "Failed to connect to OBS at " + ip + ":" + port 

        return connected, message

    def queue_subtitles(self, lines):
        sent = False
        print("lines", lines)
        if self.connected:
            print("connected", self.connected)
            # text = "\n".join(lines)
            for line in lines:
                self.subtitles_queue.put(line)

            # n = len(lines)
            # text = "\n".join(lines)
            # text = text.strip()
            # text, too_big = self.split(text)
            # new = self.dialogue_static #  if too_big else self.dialogue_dyn
            # old = self.dialogue_dyn if too_big else self.dialogue_static
            # self.change_text(old, "")
            
            sent = True
            message = "Subtitles sent to OBS"
        else:
            message = "Error: OBS Controller not connected"
        return sent, message

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
        connected, message = self.connect(ip, port, password)
        if connected:
            self._write_settings(ip, port, password)
            
        window['connected'].update(message)
        return connected, message

    def change_text(self, name, new_text):
        try:
            settings = self.cl.get_input_settings(name).input_settings
            settings['text'] = new_text
            self.cl.set_input_settings(name, settings, False)
            return f"'{name}' changed to '{new_text}'."
        except:
            msg = f"Failed to change '{name}' to '{new_text}'.\n"
            msg += "Available text sources: " + " ".join(show_texts())

class Scenes:
    def __init__(self, obs_state):
        self.i = 0
        self.obsc = obs_state

    def cycle(self):
        self.i -= 1
        resp = self.obsc.cl.get_scene_list()
        scenes = resp.scenes
        n = len(scenes)

        cur_scene = self.obsc.cl.get_current_program_scene()
        scene = cur_scene.current_program_scene_name

        new = scenes[self.i % n]
        print("Switching to new scene:", new)
        if new != scene:
            self.obsc.cl.set_current_program_scene(new['sceneName'])
            return f"Switching to new scene {new}"
        else:
            return None
        
obsc = OBSController()
connected, obs_connected_init_message = obsc._read_obs_settings_from_file()
scenes = Scenes(obsc)

def is_text(item):
    return 'text' in item['inputKind']


def show_items():
    cur_scene = obsc.cl.get_current_program_scene().current_program_scene_name
    items = obsc.cl.get_scene_item_list(cur_scene).scene_items
    return items


def show_inputs():
    inputs = obsc.cl.get_input_list().inputs
    return inputs


def show_texts():
    inputs = obsc.cl.get_input_list().inputs
    print(inputs)
    texts = [i for i in inputs if 'text' in i['inputKind']]
    texts = [source['inputName'] for source in texts]
    return texts

# def update_drvier():
#     uid = window["uid"].get()
#     return f"New Driver UID: {uid}"

# def toggle_enabled(name, nothing):
#     enabled = cl.get_scene_item_enabled()

# Buttons
def cycle_scenes():
    scenes.cycle()


def send_subtitles(lines):
    return obsc.queue_subtitles(lines)

def connect_to_obs():
    ip = window['ip'].get()
    port = window['port'].get()
    password = window['password'].get()
    connected, message = obsc.connect(ip, port, password)
    window['connected'].update(message)
    return 'connected', message

# def update_driver(values):
#     global uid
#     driver_uid = window['driver_uid'].get()
#     event_queue.put("update_driver", values)
#     return 


# Automatically generate buttons based on available functions
function_buttons = []
not_clickable = ["is_text", "update_output", "debug"]
available_functions = [(name, func) for name, func in globals().items() if
                       callable(func) and not name.startswith("_") and name not in not_clickable] 
for name, func in available_functions:
    function_buttons.append(sg.Button(name, key=name, pad=((5, 5), (0, 5))))


print(obsc.ip)
layout = [
    [sg.Text(obs_connected_init_message, key="connected"), sg.Button("Connect", key="connect_to_obs")],
    [sg.Text("IP Address"), sg.InputText(obsc.ip, key="ip")],
    [sg.Text("Port"), sg.InputText(obsc.port, key="port")],
    [sg.Text("Password"), sg.InputText(obsc.password, key="password")],
    # timer
    [sg.Text("Timer"), sg.Text("15:00", key="timer")],
    [sg.Text("Status"), sg.Multiline(key="output", disabled=True)],
    # [sg.Text("Field:"), sg.InputText("", key="field")],
    # [sg.Text("Value:"), sg.Multiline("", key="value")],
    [sg.Text("Subtitles:"), sg.InputText("", key="subtitles")],
    [sg.Text("Driver:"), sg.InputText("test@test.com", key="driver_uid"), sg.Button("Set Driver", key="update_driver")],
    function_buttons[: len(function_buttons) // 2],
    function_buttons[len(function_buttons) // 2:],
    [sg.Button("Exit", key="exit", pad=((0, 0), (0, 5)))],
]

window = sg.Window("BeetleMania OBS Control", layout, resizable=True)

def update_output(window, content):
    if content:
        if isinstance(content, tuple):
            content = content[1]
        print("content", str(content))
        window["output"].update(str(content))

def secret():
    return obsc.password

def actions():
    return [x[0] for x in available_functions]

def event_loop(window):
    while True:
        event, values = event_queue.get()
        if event == "update_driver":
            window['driver_uid'].update(values["driver_uid"])
        elif event in actions():
            function = globals()[event]
            num_params = len(inspect.signature(function).parameters)
            if num_params == 2:
                result = function(values["field"], values["value"])
            elif num_params == 1:
                result = function(values["value"])
            else:
                result = function()

            update_output(window, result)
            # Send the result back to the main thread
            event_queue.put(("update_output", result))
        elif event == sg.WIN_CLOSED:
            break
        elif event == sg.WIN_MAXIMIZED:
            window.finalize()
            window.TKroot.resizable(True, True)
        elif event == sg.WIN_NORMAL:
            window.finalize()
            window.TKroot.resizable(False, False)
        elif event == sg.WIN_FULLSCREEN:
            window.set_full_screen(True)

        # try:
        #     for button, _ in available_functions:
        #         window[button].update(disabled=not connected)
        # except Exception as e:
        #     print(e)
        # except Exception as e:
        #     # Send the exception back to the main thread
        #     print('fail', e)
        #     event_queue.put(("update_output", e))
        # print('bye')