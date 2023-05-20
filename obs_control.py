import queue, threading, time
from random import randint

import obsws_python as obs # Reference: https://github.com/obsproject/obs-websocket/blob/master/docs/generated/protocol.md#requests
import config

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
        self.default_words_per_second = 3
        self.words_per_second = self.default_words_per_second
        self.min_delay = config.get_config_value("min_delay", 3)
        self.blank_hold = config.get_config_value("blank_hold", 0)
        self.max_rand = config.get_config_value("max_rand", 5)
        self.interstitial_time = float(config.get_config_value("interstitial_time", 30))
        self.starting_soon_time = float(config.get_config_value("starting_soon_time", 10))
        
        self.on_subtitles_update = lambda x, y: None # a callback that gets called whenver a new subtitle is displayed
        self.subtitles_thread = threading.Thread(target=self.subtitles_process)
        self.subtitles_on = True
        self.subtitles_thread.start()

        self.max_line_chars = 60

    def populate_text_boxes(self, text_box_data):
        """text_box_data: a dictionary of text box names and their values"""
        for name, value in text_box_data.items():
            self.change_text(name, value)
    
    def play_subtitles(self):
        self.subtitles_on = True

    def pause_subtitles(self):
        self.subtitles_on = False

    def toggle_subtitles_on(self):
        on = self.subtitles_on
        if on:
            self.pause_subtitles()
        else:
            self.play_subtitles()
        return self.subtitles_on

    def set_subtitle_sleep_time(self, words_per_second):
        try:
            self.words_per_second = float(words_per_second)
            return f"Reading speed set to {self.words_per_second} words per second."
        except ValueError:
            return "Unable to set sleep time. Please enter a number."
        
    def set_subtitle_max_rand_delay(self, max_rand):
        try:
            self.words_per_second = float(max_rand)
            return f"Maximum random range set to {self.words_per_second} seconds."
        except ValueError:
            return "Unable to set sleep time. Please enter a number."

    def set_subtitle_blank_hold(self, blank_hold):
        try:
            self.blank_hold = float(blank_hold)
            return f"Blank hold time set to {self.blank_hold} seconds."
        except ValueError:
            return "Unable to set random range time. Please enter a number."
        
    
    def set_subtitle_blank_hold(self, blank_hold):
        try:
            self.blank_hold = float(blank_hold)
            return f"Blank hold time set to {self.blank_hold} seconds."
        except ValueError:
            return "Unable to set random range time. Please enter a number."
        
    def set_config_value_from_gui(self, key, value):
        try:
            # see if self has a variable 'key'
            setattr(self, key, value)
            config.write_config_value(key, value)
            return f"Set {key} to {value}"
        except AttributeError:
            return f"Unable to set {key} to {value}"

    def subtitles_process(self):
        while True:
            try:
                if not self.subtitles_on:
                    continue

                if self.subtitles_queue.empty():
                    pass

                text, words = self.subtitles_queue.get()
                if text is None: 
                    text = "" # A blank hold
                    delay = words
                    rand_delay = 0
                else:
                    reading_delay = max(self.min_delay, self.get_reading_speed(words, self.words_per_second))
                    rand_delay = randint(0, self.max_rand)
                    delay = reading_delay + rand_delay

                self.change_text(self.dialogue_text_field, text)
                upcoming = [show[0] for show in list(self.subtitles_queue.queue) if show[0]]
                self.on_subtitles_update(text, upcoming) # Update the GUI
                
                time.sleep(delay + rand_delay)
            except Exception as e:
                print("Error with subtitles_process", e)

    def _add_empty_subtitles_to_queue(self):
        """
        Appends an empty subtitle to the queue
        """
        self.subtitles_queue.put((None, float(self.blank_hold)))

    def _add_empty_subtitles_to_head_of_queue(self):
        """
        Pushes an empty subtitle to the head of the queue
        """
        self.subtitles_queue.queue.insert(0, (None, float(self.blank_hold)))
    
    def bypass_queue_write_empty_subtitles(self):
        """
        Regardless of the queue state, write empty subtitles.
        You may need to pause for this to endure. 
        """
        self.change_text(self.dialogue_text_field, "")
                
    def clear_subtitles_queue(self):
        with self.subtitles_queue.mutex:
            self.subtitles_queue.queue.clear()
        
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

    def queue_subtitles_at_head(self, lines): # TODO: reverse order
        sent = False
        if self.connected:
            for line in split_new_lines(lines):
                broken_lines = self.split_long_lines(line)
                for broken_line in broken_lines:
                    words = self.get_words(broken_line)
                    self.subtitles_queue.queue.insert(0, (broken_line, words))
                    print(f"Pushing '{broken_line}' to head of queue, '{words}' words")

            # Timeout the very last subtitle at the end
            self._add_empty_subtitles_to_head_of_queue()

            sent = True
            message = "Subtitles sent to OBS"
        else:
            message = "Error: OBS Controller not connected"

        return sent, message

    def queue_subtitles(self, lines):
        sent = False
        if self.connected:
            for line in split_new_lines(lines):
                broken_lines = self.split_long_lines(line)
                for broken_line in broken_lines:
                    words = self.get_words(broken_line)
                    self.subtitles_queue.put((broken_line, words))
                    print(f"Putting '{broken_line}' in queue, '{words}' words")
            
            # Hold the last one a bit longer
            # last_extra_word_proxy = randint(*self.last_message_extra_words)
            # self.subtitles_queue.put((broken_line, last_extra_word_proxy))

            # Timeout the very last subtitle at the end
            self._add_empty_subtitles_to_queue()
            
            sent = True
            message = "Subtitles sent to OBS"
        else:
            message = "Error: OBS Controller not connected"

        return sent, message
    
    def get_words(self, text):
        if text:
            return len(text.split())
        return 0

    def get_reading_speed(self, word_count, words_per_second):
        try:
            speed = word_count / words_per_second
        except ZeroDivisionError:
            speed = word_count / self.default_words_per_second
        return speed

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
                    combined.append(lines[i] + "\n")
            return combined
        
        output = iterate_by_two(lines)
        return output


    def update_topic(self, new_topic):
        self.change_text(self.topic, new_topic.strip())
        return f"Topic: {new_topic}"

    def update_obs_connection(self, ip, port, password):
        connected, message = self.connect(ip, port, password)
        if connected:
            self._write_settings(ip, port, password)
            
        return connected, message

    def change_text(self, name, new_text):
        try:
            settings = self.cl.get_input_settings(name).input_settings
            settings['text'] = new_text
            self.cl.set_input_settings(name, settings, False)
            message = f"'{name}' changed to '{new_text}'."
        except:
            message = f"Failed to change '{name}' to '{new_text}'.\n"
            message += "Available text sources: " + " ".join(show_texts())
        return message

    def get_valid_scene_names(self):
        if self.connected:
            return [s['sceneName'] for s in self.cl.get_scene_list().scenes]
        return []

    def cut_to_scene(self, scene):
        if not self.connected:
            return f"OBS {self.name.title()}: not connected"
            
        if not scene:
            try:
                scene = self.cl.get_current_program_scene().current_program_scene_name
            except Exception as e:
                return f"OBS {self.name.title()}: errror {e}"
            return f"OBS {self.name.title()}: {scene}"

        valid = [scene.lower() for scene in self.get_valid_scene_names()]
        if scene.lower() not in valid:
            return f"{scene} must be one of: {' '.join(valid)}"
        self.cl.set_current_program_scene(scene)
        return f"OBS {self.name.title()}: {scene}"

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
        if new != scene:
            self.obsc.cl.set_current_program_scene(new['sceneName'])
            return f"Switching to new scene {new}"
        else:
            return None


obsc_stream = OBSController("stream")
obsc_background =  OBSController("background")

def is_text(item):
    return 'text' in item['inputKind']


def show_items():
    if obsc_stream.cl is not None:
        cur_scene = obsc_stream.cl.get_current_program_scene().current_program_scene_name
        items = obsc_stream.cl.get_scene_item_list(cur_scene).scene_items
        return items
    return []


def show_inputs():
    if obsc_stream.cl is not None:
        inputs = obsc_stream.cl.get_input_list().inputs
        return inputs
    return []


def show_texts():
    if obsc_stream.cl is not None:
        inputs = obsc_stream.cl.get_input_list().inputs
        texts = [i for i in inputs if 'text' in i['inputKind']]
        texts = [source['inputName'] for source in texts]
        return texts
    return []

def send_subtitles(lines):
    # TODO I think this is where we want to update the GUI also
    return obsc_stream.queue_subtitles(lines)

def send_subtitles_now(lines):
    # TODO I think this is where we want to update the GUI also
    return obsc_stream.queue_subtitles_at_head(lines)


def cut_to_scene():
    return obsc_stream.cut_to_scene("Psychedelics")

def secret():
    return obsc_stream.password

def cut_to_scenes(stream=None, background=None, interstitial=None):
    if stream and interstitial:
        print("WARNING: cut_to_scenes called with both stream and interstitial. Using stream.")
    stream_msg = obsc_stream.cut_to_scene(stream) if stream else obsc_stream.cut_to_scene(interstitial)
    background_msg = obsc_background.cut_to_scene(background)

    return stream_msg, background_msg

not_clickable = ["is_text", "update_output", "debug"]
available_functions = [(name, func) for name, func in globals().items() if
                       callable(func) and not name.startswith("_") and name not in not_clickable]
available_function_dict = dict(available_functions)
def add_function(name, func):
    available_functions.append((name, func))
    available_function_dict[name] = func