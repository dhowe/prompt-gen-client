import obsws_python as obs
import PySimpleGUI as sg # https://python.libhunt.com/pysimplegui-alternatives

import inspect
import multiprocessing as mp
import queue, threading, time
import config

# Create a queue to communicate between threads
event_queue = queue.Queue()

default_driver = config.get_config_value("dashboard_user")

def debug(text):
    # make colorful and styled text
    print(f'\033[92m{text}\033[0m')


def split_new_lines(lines):
    # ["a\nb", "c" "d"] -> ["a", "b", "c" "d"]
    split = []
    for line in lines:
        split += line.split("\n")
    return split

# Custom theme
sg.theme("LightGray1")
sg.set_options(font=("Helvetica", 16))

class OBSController:
    def __init__(self) -> None:
        self.dialogue_dyn = 'Dialogue Dynamic'
        self.dialogue_static = 'Dialogue Normal'
        self.topic = "Topic"
        self.ip = config.get_config_value("obs_ip")
        self.port = config.get_config_value("obs_ip")
        self.password = config.get_config_value("obs_password")
        self.cl = None
        self.connected = False

        self.subtitles_queue = queue.Queue()
        self.words_per_second = 3
        self.min_delay = 2
        self.subtitles_thread = threading.Thread(target=self.subtitles_process)
        self.subtitles_thread.start()

        self.max_line_chars = 60

    def set_subtitle_sleep_time(self, words_per_second):
        try:
            self.words_per_second = min(3000, float(words_per_second))
            return f"Subtitle delay set to {self.words_per_second}s"
        except ValueError:
            return "Unable to set sleep time. Please enter a number."
        
    def subtitles_process(self):
        while True:
            try:
                text, delay = self.subtitles_queue.get(timeout=1)
                self.change_text(self.dialogue_dyn, text)
                window['subtitles'].update(value=text)
                time.sleep(delay)
            except queue.Empty:
                pass
    
    def _write_settings(self, ip, port, password):
        config.write_config_value("obs_ip", ip)
        config.write_config_value("obs_port", port)
        config.write_config_value("obs_password", password)

    def _read_obs_settings_from_file(self):
        self.ip = config.get_config_value("obs_ip")
        self.port = config.get_config_value("obs_port")
        self.password = config.get_config_value("obs_password")
        return self.connect(self.ip, self.port, self.password)
            
    def connect(self, ip, port, password):
        print("Connecting to OBS... at ip:", ip, "port:", port, "password:", password)
        connected = False
        message = ""
        try:
            self.cl = obs.ReqClient(ip=ip, port=port, password=password)
            self.ip = ip
            self.port = port 
            self.password = password
            self.connected = True
            connected, message = True, "Connected to OBS at " + ip + ":" + port
        except Exception as e:
            self.ip = ip if not self.ip else self.ip
            self.port = port if not self.port else self.port
            self.password = password if not self.password else self.password
            connected, message = False, "Failed to connect to OBS at " + ip + ":" + port 

        return connected, message

    def queue_subtitles(self, lines):
        sent = False
        if self.connected:
            print("connected", self.connected)
            # text = "\n".join(lines)
            for line in split_new_lines(lines):
                broken_lines = self.split_long_lines(line)
                for broken_line in broken_lines:
                    reading_time = self.get_reading_speed(broken_line)
                    self.subtitles_queue.put((broken_line, reading_time))
            
            sent = True
            message = "Subtitles sent to OBS"
        else:
            message = "Error: OBS Controller not connected"
        return sent, message
    
    def get_reading_speed(self, text):
        return min(self.min_delay, len(" ".split(text)) / self.words_per_second)

    def split_long_lines(self, text):
        # Split the into a max character length by word
        words = text.split()
        lines = []
        current_line = ""

        for word in words:
            if len(current_line + " " + word) <= self.max_line_chars:
                current_line += " " + word
            else:
                lines.append(current_line.strip())
                current_line = word
        lines.append(current_line.strip())

        def iterate_by_two(lines):
            combined = []
            for i in range(0, len(lines), 2):
                if i + 1 < len(lines):
                    combined.append(lines[i] + "\n" + lines[i+1])
                else:
                    combined.append(lines[i])
            return combined
        
        return iterate_by_two(lines)


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

    def change_scene(self, name):
        pass # TODO

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


# Buttons
def cycle_scenes():
    scenes.cycle()


def send_subtitles(lines):
    return obsc.queue_subtitles(lines)

def connect_to_obs():
    ip = window['ip'].get()
    port = window['port'].get()
    password = window['password'].get()
    obsc.update_obs_connection(ip, port, password)
    connected, message = obsc.connect(ip, port, password)
    window['connected'].update(message)
    return 'connected', message


# Automatically generate buttons based on available functions
function_buttons = []
not_clickable = ["is_text", "update_output", "debug"]
available_functions = [(name, func) for name, func in globals().items() if
                       callable(func) and not name.startswith("_") and name not in not_clickable] 
for name, func in available_functions:
    function_buttons.append(sg.Button(name, key=name, pad=((5, 5), (0, 5))))


label_size = (22, 1)
input_size = (40, 2)
full_size = size=(label_size[0] + input_size[0], label_size[1])

layout = [
    [sg.Text(obs_connected_init_message, key="connected", size=full_size), sg.Button("Connect", key="connect_to_obs")],
    [sg.Text("Display User:", size=label_size), sg.InputText(default_driver, key="driver_uid", size=input_size), sg.Button("Set Driver", key="update_driver")],
    # [sg.Break()],  # Doesn't actually exist
    [sg.Text("IP Address", size=label_size), sg.InputText(obsc.ip, key="ip", size=input_size)],
    [sg.Text("Port", size=label_size), sg.InputText(obsc.port, key="port", size=input_size)],
    [sg.Text("Password", size=label_size), sg.InputText(obsc.password, key="password", size=input_size)],
    [sg.Text("Timer", size=label_size), sg.Text("15:00", key="timer", size=input_size)],
    [sg.Text("Reading Speed (words/sec)", size=label_size), sg.InputText(obsc.words_per_second, key="sleep_time", size=input_size), sg.Button("Set subtitles delay", key="set_sleep_time")],
    [
        sg.Button("We'll be right back", key="right_back", pad=((5, 5), (0, 5))),
        sg.Button("Starting Soon", key="starting_soon", pad=((5, 5), (0, 5))),
        sg.Button("Preroll", key="preroll", pad=((5, 5), (0, 5))),
        sg.Button("Play Schedule", key="stream_ending", pad=((5, 5), (0, 5))),
    ],
    [sg.Text("Next Show", size=label_size), sg.Text(key="next_show", size=input_size)],
    [sg.Text("Status", size=label_size), sg.Text(key="output", size=input_size)],
    [sg.Text("", key="subtitles", size=full_size)],
    # [sg.Button("Exit", key="exit", pad=((0, 0), (0, 5)))],
]

window = sg.Window("BeetleMania OBS Control", layout, resizable=True)

def update_output(window, content):
    # Display content in output window
    if content:
        if isinstance(content, tuple):
            content = content[1]
        print("content", str(content))
        window["output"].update(str(content))

def update_next_show(window, content):
    if content:
        window["next_show"].update(str(content))


def secret():
    return obsc.password

def actions():
    return [x[0] for x in available_functions]

def event_loop(window):
    while True:
        event, values = event_queue.get()
        if event in actions():
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
        elif event == "new_show":
            update_next_show(window, values)
        elif event == sg.WIN_CLOSED:
            break

        print(event, values)