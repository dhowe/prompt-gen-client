import PySimpleGUI as sg # https://python.libhunt.com/pysimplegui-alternatives
import webbrowser
import queue
import inspect
from obs_control import obsc_stream, obsc_background, available_functions, available_function_dict
import config

default_driver = config.get_config_value("dashboard_user")
default_driver_pass = config.get_config_value("dashboard_password", "")
default_sheet_name = config.get_config_value("google_sheet_show_sheet_name", "Shows")

# Create a queue to communicate between threads
event_queue = queue.Queue()

def create_link(text, url):
    link_text = sg.Text(text, enable_events=True, text_color='blue')
    def open_link():
        webbrowser.open(url)
    return link_text, open_link


def update_timer(time_until_show):    
    if not time_until_show:
        window['timer'].update("")
        return
    
    if isinstance(time_until_show, str):
        timer_str = time_until_show
    else:
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
    
    window['timer'].update(timer_str)


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

small_label = (10, 1)
small2_label = (22, 1)
label_size = (22, 1)
input_size = (40, 2)
full_size = size =(label_size[0] + input_size[0], label_size[1])
biggest_size = (45, 4)

start_message, stop_message = "Start Schedule", "Stop Schedule"

# Automatically generate buttons based on available functions
function_buttons = []
for name, func in available_functions:
    function_buttons.append(sg.Button(name, key=name, pad=((5, 5), (0, 5))))


# Links
dashboard_event = "Dashboard"
dashboard_link, dashboard_action = create_link(dashboard_event, "http://192.241.209.27:5050/")
shows_event = "Shows Spreadsheet"
shows_link, shows_action = create_link(shows_event, "https://docs.google.com/spreadsheets/d/1lXononLyDu7_--xHODvQwB_h9LywvctLCdbzYRNVZRc/edit#gid=0")

links = [sg.Text("Links"), dashboard_link, shows_link]

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
        sg.Button("Check for shows", key="update_sheet"),
        # sg.Button("We'll be right back", key="right_back", pad=((5, 5), (0, 5))),
        # sg.Button("Starting Soon", key="starting_soon", pad=((5, 5), (0, 5))),
        # sg.Button("Preroll", key="preroll", pad=((5, 5), (0, 5))),
        sg.Button(start_message, key="start_stop_schedule", pad=((5, 5), (0, 5))),
    ],
    function_buttons
]

subtitle_settings = [
    [
        sg.Text("Reading Speed (words/sec)", size=label_size, expand_x=True), 
        sg.InputText(obsc_stream.words_per_second, key="sleep_time", size=small_label, expand_x=True), 
        sg.Button("Set reading speed", key="set_sleep_time"),
        sg.Text("Max Random Delay (sec)", size=label_size, expand_x=True), 
        sg.InputText(obsc_stream.max_rand, key="max_rand", size=small_label, expand_x=True), 
        sg.Button("Set max delay", key="set_rand_delay")
    ],
    [
        sg.Text("Time between new messasges (sec)", size=label_size, expand_x=True), 
        sg.InputText(obsc_stream.blank_hold, key="blank_hold", size=small_label, expand_x=True), 
        sg.Button("Set hold time", key="set_blank_hold")
    ],
    [
        sg.Text("Interstitial Time", size=label_size, expand_x=True),
        sg.InputText(config.get_config_value("interstitial_time"), key="interstitial_time", size=small_label, expand_x=True),
        sg.Button("Set Interstitial Time", key="set_interstitial_scene")
    ],
]

layout = [
    links,
    [
        sg.TabGroup([[
            sg.Tab('Connections', main_tab),
            sg.Tab('Subtitle Settings', subtitle_settings),
            # sg.Tab('', tab2)
        ]])
    ],
    [
        sg.Frame("Upcoming Shows", [
            [sg.Text("No dashboard connected", key="timer_label", size=small_label), sg.Text("", key="timer", size=small_label, expand_x=True)],
            [sg.Text("Current Show", size=label_size), sg.Text(key="current_show", size=input_size, expand_x=True)],
            [sg.Text("Next Show", size=label_size), sg.Text(key="next_show", size=input_size, expand_x=True)],
            [sg.Multiline("", key='upcoming_shows', size=biggest_size, expand_x=True)],
        ], expand_x=True, expand_y=True),
    ],
    
    # [sg.Text("Next Show", size=label_size, expand_x=True), sg.Text(key="next_show", size=input_size, expand_x=True)],
    [sg.Text("Status", size=label_size, expand_x=True), sg.Text(key="output", size=biggest_size, expand_x=True, expand_y=True)],
    [sg.Text("", key="subtitles", size=biggest_size, expand_x=True, expand_y=True)],
   ]

window = sg.Window("BeetleChat Stream", layout, resizable=True)


def update_output(window, content):
    # Display content in output window
    if content:
        if isinstance(content, tuple):
            content = content[1]
        print("content", str(content))
        window["output"].update(str(content))

def message(content):
    update_output(window, content)

def update_shows(current=None, next=None, upcoming=list()):
    if current:
        window["current_show"].update(current)
    if next:
        window["next_show"].update(next)

    text = ""
    if upcoming:
        for show in upcoming:
                text += str(show) + "\n"
    window["upcoming_shows"].update(text)

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

def event_loop(window):
    while True:
        event, values = event_queue.get()
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
            # Send the result back to the main thread
            event_queue.put(("update_output", result))
        elif event == "new_next_show":
            next = values[0]
            upcoming = values[1]
            upcoming = upcoming[1:] if len(upcoming) > 1 else []
            update_shows(next=values[0], upcoming=values[1])
        elif event == sg.WIN_CLOSED:
            break

        # print(event, values)