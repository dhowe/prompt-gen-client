import PySimpleGUI as sg # https://python.libhunt.com/pysimplegui-alternatives
import webbrowser
import queue
import inspect
from obs_control import obsc_stream, obsc_background, available_functions, available_function_dict, cut_to_scenes
import config
import time

default_driver = config.get_config_value("dashboard_user")
default_driver_pass = config.get_config_value("dashboard_password", "")
default_sheet_name = config.get_config_value("google_sheet_show_sheet_name", "Test")

# Create a queue to communicate between threads
event_queue = queue.Queue()

status = ""

def create_link(text, url):
    link_text = sg.Text(text, enable_events=True, text_color='blue')
    def open_link():
        webbrowser.open(url)
    return link_text, open_link


def update_timer(time_until_show, time_until_title=None, time_until_interstitial=None):    
    if not time_until_show:
        window['show_timer'].update("")
        window['show_timer_label'].update("")
        window['title_timer'].update("")
        window['title_timer_label'].update("")
        window['interstitial_timer'].update("")
        window['interstitial_timer_label'].update("")
        return
    
    if isinstance(time_until_show, str):
        window['timer_label'].update(time_until_show)
        window['show_timer'].update("")
        window['show_timer_label'].update("")
        window['title_timer'].update("")
        window['title_timer_label'].update("")
        window['interstitial_timer_label'].update("")
        window['interstitial_timer'].update("")
    else:
        time_until_show = format_timer(time_until_show)
        time_until_title = format_timer(time_until_title)
        time_until_interstitial = format_timer(time_until_interstitial)
    
        window['show_timer_label'].update("Show")
        window['show_timer'].update(time_until_show)
        window['title_timer_label'].update("Title Card")
        window['title_timer'].update(time_until_title)
        window['interstitial_timer_label'].update("Interstitial")
        window['interstitial_timer'].update(time_until_interstitial)
    

def format_timer(timer):
    try:
        days, remainder = divmod(timer.seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        # Create the timer string
        timer_str = ''
        if timer.days > 0:
            timer_str += f'{timer.days} day'
            if timer.days > 1:
                timer_str += 's'
            timer_str += ' '
        if hours > 0:
            timer_str += f'{hours:02d}:'
        if minutes > 0:
            timer_str += f'{minutes:02d}:'
        timer_str += f'{seconds:02d}'
    except Exception as e:
        timer_str = str(timer)
    return timer_str


def connect_to_obs_stream():
    window['stream_connected'].update("Connecting...")
    stream_ip       = window['stream_ip'].get()
    stream_port     = window['stream_port'].get()
    stream_password = window['stream_password'].get()
    connected, message = obsc_stream.update_obs_connection(stream_ip, stream_port, stream_password)
    window['stream_connected'].update(message)
    return 'connected', message

def connect_to_obs_background():
    window['background_connected'].update("Connecting...")
    background_ip       = window['background_ip'].get()
    backgorund_port     = window['background_port'].get()
    backgorund_password = window['background_password'].get()
    connected, message = obsc_background.update_obs_connection(background_ip, backgorund_port, backgorund_password)
    window['background_connected'].update(message)
    return 'connected', message


sg.theme("LightGray1")
sg.set_options(font=("Helvetica", 16))
try:
    sg.set_options(font=("Kailasa", 16))
except:
    pass

number = (5, 1)
timer = (8, 1)
small_label = (9, 1)
small2_label = (22, 1)
label_size = (22, 1)
input_size = (40, 2)
full_size = size =(label_size[0] + input_size[0], label_size[1])
biggest_size = (45, 4)
subtitles_size = (50, 3)
column_element = (40, 2)
column_size = (40, 7)

data_font = ("Helvetica", 14)

start_message, stop_message = "Start Schedule", "Stop Schedule"
pause_message, resume_message = "Pause Subtitles", "Resume Subtitles"

# Automatically generate buttons based on available functions
function_buttons = []
for name, func in available_functions:
    function_buttons.append(sg.Button(name, key=name, pad=((5, 5), (0, 5))))


# Links
dashboard_event = "Dashboard"
dashboard_link, dashboard_action = create_link(dashboard_event, "http://192.241.209.27:5050/")
shows_event = "Shows Spreadsheet"
shows_link, shows_action = create_link(shows_event, "https://docs.google.com/spreadsheets/d/1lXononLyDu7_--xHODvQwB_h9LywvctLCdbzYRNVZRc/edit#gid=0")

links = [
    [dashboard_link, sg.Text("Warning: opening a second dashboard instance will break things")], 
    [shows_link],
]

main_tab = [
    [
        sg.Text("Driver (Disconnected)", key="driver_label", size=label_size, expand_x=True), 
        sg.InputText(default_driver, key="driver_uid", size=input_size, expand_x=True), 
        sg.InputText(default_driver_pass, key="driver_password",size=input_size, expand_x=True, password_char="*"), 
        sg.Button("Set Driver", key="update_driver")
    ],
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
        sg.Text("Sheet Name", size=label_size), 
        sg.InputText(default_sheet_name, key="sheet", size=small_label, expand_x=True), 
        sg.Button("Update Shows", key="update_sheet"),
        sg.Button(start_message, key="start_stop_schedule", pad=((5, 5), (0, 5))),
        sg.Checkbox("Automode", True, key="automode", enable_events=True, ),
    ],
    # function_buttons,
]

subtitle_settings = [
    [
        sg.Text("Reading Speed (words/sec)", size=label_size, expand_x=True), 
        sg.InputText(obsc_stream.words_per_second, key="sleep_time", size=number, expand_x=True), 
        sg.Button("Set reading speed", key="set_sleep_time"),
    ],
    [
        sg.Text("Max Random Delay (sec)", size=label_size, expand_x=True), 
        sg.InputText(obsc_stream.max_rand, key="max_rand", size=number, expand_x=True), 
        sg.Button("Set random delay range", key="set_rand_delay")
    ],
    [
        sg.Text("Minimum subtitle duration (sec)", size=label_size, expand_x=True), 
        sg.InputText(obsc_stream.min_delay, key="min_delay", size=number, expand_x=True), 
        sg.Button("Set minimum", key="set_min_delay"),
    ],
    [
        sg.Text("Hold between new messages (sec)", size=label_size, expand_x=True), 
        sg.InputText(obsc_stream.blank_hold, key="blank_hold", size=number, expand_x=True), 
        sg.Button("Set hold time", key="set_blank_hold"),
    ],
]

scene_settings = [
    [sg.Text("Warning, don't change these while a schedule is running. First stop the schedule, update, wait 8 seconds, and restart.")],
    [
        sg.Text("Interstitial scene duration", size=label_size, expand_x=True),
        sg.InputText(config.get_config_value("interstitial_time"), key="interstitial_time", size=small_label, expand_x=True),
        sg.Button("Set interstitial duration", key="set_interstitial_time")
    ],
    [
        sg.Text("Starting soon / title scene duration", size=label_size, expand_x=True),
        sg.InputText(config.get_config_value("starting_soon_time"), key="starting_soon_time", size=small_label, expand_x=True),
        sg.Button("Set title duration", key="set_starting_soon_time")
    ],
]

timer_font = ('Helvetica', 17)
layout = [
    [
        sg.TabGroup([[
            sg.Tab('Connections', main_tab),
            sg.Tab('Subtitle Settings', subtitle_settings),
            sg.Tab('Scene Settings', scene_settings),
            sg.Tab('Links', links),
        ]])
    ],
    [
        sg.Text("No dasboard connected", key="timer_label", size=small_label, expand_x=True), 
        sg.Text("", key="show_timer_label", size=small_label), 
        sg.Text("", key="show_timer", size=timer, font=timer_font), 
        sg.Text("", key="title_timer_label", size=small_label), 
        sg.Text("", key="title_timer", size=timer, font=timer_font),
        sg.Text("", key="interstitial_timer_label", size=small_label), 
        sg.Text("", key="interstitial_timer", size=timer, font=timer_font)
    ],
    # [
    #     sg.Column([
    #         [sg.Text("Current Show")],
    #         [sg.Text(key="current_show", font=data_font, size=label_size, expand_x=True)]
    #     ], expand_x=True),
    #     sg.Column([
    #         [sg.Text("Next show")],
    #         [sg.Text(key="next_show", font=data_font, size=label_size, expand_x=True)]
    #         ,
    #     ], expand_x=True),
    # ],
    [
        [sg.Text("Current Show")],
        [sg.Text(key="current_show", font=data_font, size=label_size, expand_x=True)],
    ],
    [
        [sg.Text("Next show")],
        [sg.Text(key="next_show", font=data_font, size=label_size, expand_x=True)],
    ],
    [
        sg.Column([
            [sg.Text("Upcoming Shows")],
            [sg.Text("", key='upcoming_shows', font=data_font, size=column_size, expand_x=True, expand_y=True)],
        ], expand_x=True, expand_y=True, scrollable=True,  vertical_scroll_only=True),
        sg.Column([
            [
                sg.Button("Clear Subtitles", key="clear_subtitles", pad=((5, 5), (0, 5))),
                sg.Button(pause_message, key="toggle_subtitles", pad=((5, 5), (0, 5))),
             ],
            [sg.Text("", key="subtitles", size=column_element, expand_x=True, expand_y=True, font=('Helvetica', 15))],
            [sg.Text("", key="upcoming_subtitles", size=column_size, expand_x=True, expand_y=True, font=('Helvetica', 12))],
        ], expand_x=True, expand_y=True, scrollable=True,  vertical_scroll_only=True),
    ],
    [sg.Text("Current OBS Scenes", size=label_size), sg.Text(key="current_scene", size=input_size, expand_x=True)],
    [
        # sg.Button("Preroll", key="preroll", pad=((5, 5), (0, 5))),
        sg.Button("Technical Difficulties", key="technical", pad=((5, 5), (0, 5))),
        sg.Button("Off Air", key="off_air", pad=((5, 5), (0, 5))),
        sg.Button("Starting Soon", key="starting_soon", pad=((5, 5), (0, 5))),
    ],
    [sg.Text("Status", size=label_size, expand_x=True), sg.Text(key="output", font=data_font, size=biggest_size, expand_x=True, expand_y=True)],
]

window = sg.Window("BeetleChat Stream", layout, resizable=True)


def update_output(window, content):
    # Display content in output window
    if content:
        if isinstance(content, tuple):
            content = content[1]
        print("content", str(content))
        window["output"].update(str(content))

def toggle_subtitles(on):
    window['toggle_subtitles'].update(text=pause_message if on else resume_message)

def message(content):
    global status
    status = content + "\n" + status
    update_output(window, status)

def current_obs_scene(message):
    window["current_scene"].update(message)

def update_shows(current=None, next=None, upcoming=list()):
    if current:
        window["current_show"].update(current)
    if next:
        window["next_show"].update(next)
    else:
        window["next_show"].update("No shows scheduled")

    if upcoming:
        text = ""
        for show in upcoming:
                text += str(show) + "\n"
        window["upcoming_shows"].update(text)
    else:
        window["upcoming_shows"].update("No upcoming shows")

def update_driver(connected, driver_name=None):
    message = "Driver" if connected else "Driver (Not Connected)"
    window["driver_label"].update(message)

    uid = "to " + driver_name if driver_name else default_driver
    window["timer_label"].update("No dashboard connection" if not connected else f"Connected {uid}")


# TODO these two functions really shouldn't go here
def connect_to_obs_stream():
    window['stream_connected'].update("Connecting...")
    stream_ip       = window['stream_ip'].get()
    stream_port     = window['stream_port'].get()
    stream_password = window['stream_password'].get()
    connected, message = obsc_stream.update_obs_connection(stream_ip, stream_port, stream_password)
    window['stream_connected'].update(message)
    return 'connected', message

def connect_to_obs_background():
    window['background_connected'].update("Connecting...")
    background_ip       = window['background_ip'].get()
    backgorund_port     = window['background_port'].get()
    backgorund_password = window['background_password'].get()
    connected, message = obsc_background.update_obs_connection(background_ip, backgorund_port, backgorund_password)
    window['background_connected'].update(message)
    return 'connected', message

def automode():
    auto = window['automode'].get()
    config.write_config_value("automode", auto)
    msg = f"Automode: {auto}"
    message(msg)

def do_scene_cut(stream=None, background=None, interstitial=None):
    # Not sure this should go here
    scene_message = cut_to_scenes(
        stream,
        background,
        interstitial
    )
    current_obs_scene(scene_message)
    message(scene_message)

def clear_subtitles():
    window['subtitles'].update(value="")
    window['upcoming_subtitles'].update(value="")


def main_loop_gui(window):
    while True:
        event, values = window.read(timeout=100)
        if event == "__TIMEOUT__":
            continue
        elif event == sg.WIN_CLOSED:
            break
        if event in available_function_dict.keys():
            function = available_function_dict[event]
            num_params = len(inspect.signature(function).parameters)
            if num_params == 2:
                result = function(values["field"], values["value"])
            elif num_params == 1:
                result = function(values["value"])
            else:
                result = function()
            update_output(window, result)
        elif event == "new_next_show":
            # TODO move this somewhere
            next = values[0]
            upcoming = values[1]
            upcoming = upcoming[1:] if len(upcoming) > 1 else []
            update_shows(next=next, upcoming=values[1])
        else:
            event_queue.put((event, values))