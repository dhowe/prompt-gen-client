import obsws_python as obs
import PySimpleGUI as sg # https://python.libhunt.com/pysimplegui-alternatives

import inspect
import multiprocessing as mp
import queue, threading, time
import config

# Create a queue to communicate between threads
event_queue = queue.Queue()

default_driver = config.get_config_value("dashboard_user")
default_driver_pass = config.get_config_value("dashboard_password", "")

def debug(text):
    # make colorful and styled text
    print(f'\033[92m{text}\033[0m')


def split_new_lines(lines):
    # ["a\nb", "c" "d"] -> ["a", "b", "c" "d"]
    split = []
    for line in lines:
        split += line.split("\n")
    return split


class OBSController:
    def __init__(self, name) -> None:
        self.dialogue_text_field = config.get_config_value("subtitle_layer_name", "Subtitle Layer")
        self.topic               = "Topic"
        self.name                = name
        self.ip                  = None
        self.port                = None
        self.password            = None
        self.message             = None
        self._read_obs_settings_from_file(connect=False)

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
                self.change_text(self.dialogue_text_field, text)
                window['subtitles'].update(value=text)
                time.sleep(delay)
            except queue.Empty:
                pass
    
    def _write_settings(self, ip, port, password):
        config.write_config_value(f"{self.name}_obs_ip", ip)
        config.write_config_value(f"{self.name}_obs_port", port)
        config.write_config_value(f"{self.name}_obs_password", password)

    def _read_obs_settings_from_file(self, connect=True):
        self.ip         = config.get_config_value(f"{self.name}_obs_ip")
        self.port       = config.get_config_value(f"{self.name}_obs_port")
        self.password   = config.get_config_value(f"{self.name}_obs_password")
        if connect:
            connected, self.message = self.connect(self.ip, self.port, self.password)
            return connected
        return False
            
    def connect(self, ip, port, password):
        print("Connecting to OBS... at host:", ip, "port:", port, "password:", password)
        try:
            self.cl = obs.ReqClient(host=ip, port=port, password=password)
            self.ip = ip
            self.port = port 
            self.password = password
            self.connected, self.message = True, "Connected to OBS at " + ip + ":" + port
        except Exception as e:
            self.ip = ip if not self.ip else self.ip
            self.port = port if not self.port else self.port
            self.password = password if not self.password else self.password
            self.connected, self.message = False, "Failed to connect to OBS at " + ip + ":" + port 
        print(self.message)
        return self.connected, self.message

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
            
        window[f"{self.name}_connected"].update(message)
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
        
obsc_stream = OBSController("stream")
obsc_background =  OBSController("background")

scenes = Scenes(obsc_stream)



def is_text(item):
    return 'text' in item['inputKind']

def update_timer(time_until_show):    
    if not time_until_show:
        window['timer'].update("")
        return

    try:
        days, remainder = divmod(time_until_show.seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        # Create the timer string
        timer_str = ''
        if time_until_show.days > 0:
            timer_str += f'{time_until_show.days} day'
            if time_until_show.days > 1:
                timer_str += 's'
            timer_str += ' '
        if hours > 0:
            timer_str += f'{hours:02d}:'
        if minutes > 0:
            timer_str += f'{minutes:02d}:'
        timer_str += f'{seconds:02d}'
    except Exception as e:
        timer_str = str(time_until_show)
        print(e)
    window['timer'].update(timer_str)


def show_items():
    cur_scene = obsc_stream.cl.get_current_program_scene().current_program_scene_name
    items = obsc_stream.cl.get_scene_item_list(cur_scene).scene_items
    return items


def show_inputs():
    inputs = obsc_stream.cl.get_input_list().inputs
    return inputs


def show_texts():
    inputs = obsc_stream.cl.get_input_list().inputs
    print(inputs)
    texts = [i for i in inputs if 'text' in i['inputKind']]
    texts = [source['inputName'] for source in texts]
    return texts


# Buttons
def cycle_scenes():
    scenes.cycle()


def send_subtitles(lines):
    return obsc_stream.queue_subtitles(lines)

def connect_to_obs_stream():
    window['stream_connected'].update("Connecting...")
    stream_ip       = window['stream_ip'].get()
    stream_port     = window['stream_port'].get()
    stream_password = window['stream_password'].get()
    obsc_stream.update_obs_connection(stream_ip, stream_port, stream_password)
    connected, message1 = obsc_stream.connect(stream_ip, stream_port, stream_password)
    window['stream_connected'].update(message1)
    return 'connected', message1

def connect_to_obs_background():
    window['background_connected'].update("Connecting...")
    background_ip       = window['background_ip'].get()
    backgorund_port     = window['background_port'].get()
    backgorund_password = window['background_password'].get()
    obsc_background.update_obs_connection(background_ip, backgorund_port, backgorund_password)
    connected, message2 = obsc_background.connect(background_ip, backgorund_port, backgorund_password)
    window['background_connected'].update(message2)
    return 'connected', message2


# Automatically generate buttons based on available functions
function_buttons = []
not_clickable = ["is_text", "update_output", "debug"]
available_functions = [(name, func) for name, func in globals().items() if
                       callable(func) and not name.startswith("_") and name not in not_clickable] 
for name, func in available_functions:
    function_buttons.append(sg.Button(name, key=name, pad=((5, 5), (0, 5))))


sg.theme("LightGray1")
sg.set_options(font=("Helvetica", 16))
try:
    sg.set_options(font=("Kailasa", 16))
except:
    pass

small_label = (10, 1)
small2_label = (22, 1)
label_size = (22, 1)
input_size = (40, 2)
full_size = size=(label_size[0] + input_size[0], label_size[1])

start_message, stop_message = "Start Schedule", "Stop Schedule"

layout = [
    [
        sg.Frame("OBS Instances", [
            [
                sg.Column([
                    [sg.Text("Stream", size=small_label, expand_x=True)],
                    [sg.Text("IP Address", size=small_label, expand_x=True), sg.InputText(obsc_stream.ip, key="stream_ip", size=input_size, expand_x=True)],
                    [sg.Text("Port", size=small_label, expand_x=True), sg.InputText(obsc_stream.port, key="stream_port", size=input_size, expand_x=True)],
                    [sg.Text("Password", size=small_label, expand_x=True), sg.InputText(obsc_stream.password, key="stream_password", size=input_size, expand_x=True)],
                    [sg.Text("", key="stream_connected", expand_x=True), sg.Button("Connect Stream", key="connect_to_obs_stream", pad=((5, 5), (20, 5)))],
                ], pad=((0, 20), 0)),
                sg.Column([
                    [sg.Text("Background", size=small_label, expand_x=True)],
                    [sg.Text("IP Address", size=small_label, expand_x=True), sg.InputText(obsc_background.ip, key="background_ip", size=input_size, expand_x=True)],
                    [sg.Text("Port", size=small_label, expand_x=True), sg.InputText(obsc_background.port, key="background_port", size=input_size, expand_x=True)],
                    [sg.Text("Password", size=small_label, expand_x=True), sg.InputText(obsc_background.password, key="background_password", size=input_size, expand_x=True)],
                    [sg.Text("", key="background_connected", expand_x=True), sg.Button("Connect Background", key="connect_to_obs_background", pad=((5, 5), (20, 5)))],
                ], pad=((20, 0), 0)),
            ],
        ], expand_x=True),
    ],
    [
        sg.Text("Driver (Subtitle Display)", size=label_size, expand_x=True), 
        sg.InputText(default_driver, key="driver_uid", size=input_size, expand_x=True), 
        sg.InputText(default_driver_pass, key="driver_password",size=input_size, expand_x=True, password_char="*"), 
        sg.Button("Set Driver", key="update_driver")],
    
    [sg.Text("Reading Speed (words/sec)", size=label_size, expand_x=True), sg.InputText(obsc_stream.words_per_second, key="sleep_time", size=input_size, expand_x=True), sg.Button("Set subtitles delay", key="set_sleep_time")],
    [
        sg.Button("We'll be right back", key="right_back", pad=((5, 5), (0, 5))),
        sg.Button("Starting Soon", key="starting_soon", pad=((5, 5), (0, 5))),
        sg.Button("Preroll", key="preroll", pad=((5, 5), (0, 5))),
        sg.Button(start_message, key="start_stop_schedule", pad=((5, 5), (0, 5))),
    ],
    [sg.Text("Showtime in", size=label_size, expand_x=True), sg.Text("", key="timer", size=input_size, expand_x=True)],
    [sg.Text("Next Show", size=label_size, expand_x=True), sg.Text(key="next_show", size=input_size, expand_x=True)],
    [sg.Text("Status", size=label_size, expand_x=True), sg.Text(key="output", size=input_size, expand_x=True)],
    [sg.Text("", key="subtitles", size=full_size)],
    # function_buttons
]

window = sg.Window("BeetleChat Stream", layout, resizable=True)


def update_output(window, content):
    # Display content in output window
    if content:
        if isinstance(content, tuple):
            content = content[1]
        print("content", str(content))
        window["output"].update(str(content))

def update_next_show(show):
    if show:
        print(show)
        content = show.get("Name", "Name mising") + " starting at "
        content += show.get("Date", "Date missing") + " "
        content += show.get("Time", "Time missing") + " "
        window["next_show"].update(content)

def secret():
    return obsc_stream.password

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
            # update_next_show(window, values)
            pass
        elif event == sg.WIN_CLOSED:
            break

        print(event, values)