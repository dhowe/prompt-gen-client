import inspect
import queue
import webbrowser

import PySimpleGUI as sg  # https://python.libhunt.com/pysimplegui-alternatives

import config
from helpers import Timer
from obs_control import obsc_stream, obsc_background, available_functions, available_function_dict, cut_to_scenes

print('Loading interface...')

app_version = 'v0.9.7'
default_driver = config.get_value("dashboard_user")
default_driver_pass = config.get_value("dashboard_password", "")
default_sheet_name = config.get_value("google_sheet_show_sheet_name", "Test")

# Create a queue to communicate between threads
event_queue = queue.Queue()
perf = Timer(text="GUI loaded in {:0.2f} secs")
perf.start()
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
    window['stream_connected'].update("Connecting to obs...")
    stream_ip = window['stream_ip'].get()
    stream_port = window['stream_port'].get()
    stream_password = window['stream_password'].get()
    connected, msg = obsc_stream.update_obs_connection(stream_ip, stream_port, stream_password)
    window['stream_connected'].update(msg)
    return 'connected', msg


def connect_to_obs_background():
    window['background_connected'].update("Connecting...")
    background_ip = window['background_ip'].get()
    backgorund_port = window['background_port'].get()
    backgorund_password = window['background_password'].get()
    connected, msg = obsc_background.update_obs_connection(background_ip, backgorund_port, backgorund_password)
    window['background_connected'].update(msg)
    return 'connected', msg


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
full_size = size = (label_size[0] + input_size[0], label_size[1])
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
shows_link, shows_action = create_link(shows_event,
                                       "https://docs.google.com/spreadsheets/d/1lXononLyDu7_--xHODvQwB_h9LywvctLCdbzYRNVZRc/edit#gid=0")

links = [
    [dashboard_link, sg.Text("Warning: opening a second dashboard instance will break things")],
    [shows_link],
]

main_tab = [
    [
        sg.Text("Driver (Disconnected)", key="driver_label", size=label_size, expand_x=True),
        sg.InputText(default_driver, key="driver_uid", size=input_size, expand_x=True),
        sg.InputText(default_driver_pass, key="driver_password", size=input_size, expand_x=True, password_char="*"),
        sg.Button("Connect", key="update_driver")
    ],
    [
        sg.Frame("OBS Instances", [
            [
                sg.Column([
                    [sg.Text("Stream", size=small_label),
                     sg.Text(key="current_stream_scene", size=input_size, expand_x=True)],
                    [sg.Text("IP Address", size=small_label, expand_x=True),
                     sg.InputText(obsc_stream.ip, key="stream_ip", size=input_size, expand_x=True)],
                    [sg.Text("Port", size=small_label, expand_x=True),
                     sg.InputText(obsc_stream.port, key="stream_port", size=input_size, expand_x=True)],
                    [sg.Text("Password", size=small_label, expand_x=True),
                     sg.InputText(obsc_stream.password, key="stream_password", size=input_size, expand_x=True)],
                    [sg.Text("", key="stream_connected", expand_x=True),
                     sg.Button("Connect Stream", key="connect_to_obs_stream", pad=((5, 5), (20, 5)))],
                ], pad=((0, 20), 0)),
                sg.Column([
                    [sg.Text("Backwall", size=small_label),
                     sg.Text(key="current_background_scene", size=input_size, expand_x=True)],
                    [sg.Text("IP Address", size=small_label, expand_x=True),
                     sg.InputText(obsc_background.ip, key="background_ip", size=input_size, expand_x=True)],
                    [sg.Text("Port", size=small_label, expand_x=True),
                     sg.InputText(obsc_background.port, key="background_port", size=input_size, expand_x=True)],
                    [sg.Text("Password", size=small_label, expand_x=True),
                     sg.InputText(obsc_background.password, key="background_password", size=input_size, expand_x=True)],
                    [sg.Text("", key="background_connected", expand_x=True),
                     sg.Button("Connect Background", key="connect_to_obs_background", pad=((5, 5), (20, 5)))],
                ], pad=((20, 0), 0)),
            ],
        ], expand_x=True),
    ],
    [
        sg.Text("Sheet Name", size=label_size),
        sg.InputText(default_sheet_name, key="sheet", size=small_label, expand_x=True),
        sg.Button("Update Shows", key="update_sheet"),
        sg.Button(start_message, key="start_stop_schedule"),
        sg.Checkbox("Automode", config.get_value("automode", True), key="automode", enable_events=True),
        sg.Checkbox("TTS", config.get_value("use_tts", True), key="use_tts", enable_events=True),
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
    [
        sg.Text("Delay after TTS before subtitle display (sec)", size=label_size, expand_x=True),
        sg.InputText(obsc_stream.blank_hold, key="post_tts_delay", size=number, expand_x=True),
        sg.Button("Set TTS delay", key="set_post_tts_delay"),
    ],
]

scene_settings = [
    [sg.Text(
        "Warning, don't change these while a schedule is running. First stop the schedule, update, wait 8 seconds, and restart.")],
    [
        sg.Text("Interstitial scene duration", size=label_size, expand_x=True),
        sg.InputText(config.get_value("interstitial_time"), key="interstitial_time", size=small_label,
                     expand_x=True),
        sg.Button("Set interstitial duration", key="set_interstitial_time")
    ],
    [
        sg.Text("Starting soon / title scene duration", size=label_size, expand_x=True),
        sg.InputText(config.get_value("starting_soon_time"), key="starting_soon_time", size=small_label,
                     expand_x=True),
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
        sg.Text("No dashboard connected", key="timer_label", size=small_label, expand_x=True),
        sg.Text("", key="show_timer_label", size=small_label),
        sg.Text("", key="show_timer", size=timer, font=timer_font),
        sg.Text("", key="title_timer_label", size=small_label),
        sg.Text("", key="title_timer", size=timer, font=timer_font),
        sg.Text("", key="interstitial_timer_label", size=small_label),
        sg.Text("", key="interstitial_timer", size=timer, font=timer_font)
    ],
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
        ], expand_x=True, expand_y=True, scrollable=True, vertical_scroll_only=True),
        sg.Column([
            [
                sg.Button("Clear Subtitles", key="clear_subtitles", pad=((5, 5), (0, 5))),
                sg.Button(pause_message, key="toggle_subtitles", pad=((5, 5), (0, 5))),
            ],
            [sg.Text("", key="subtitles", size=column_element, expand_x=True, expand_y=True, font=('Helvetica', 15))],
            [sg.Text("", key="upcoming_subtitles", size=column_size, expand_x=True, expand_y=True,
                     font=('Helvetica', 12))],
        ], expand_x=True, expand_y=True, scrollable=True, vertical_scroll_only=True),
    ],
    [
        # sg.Button("Preroll", key="preroll", pad=((5, 5), (0, 5))),
        sg.Button("Technical Difficulties", key="technical", pad=((5, 5), (0, 5))),
        sg.Button("Off Air", key="off_air", pad=((5, 5), (0, 5))),
        sg.Button("Starting Soon", key="starting_soon", pad=((5, 5), (0, 5))),
    ],
    [sg.Text("Status", size=label_size, expand_x=True),
     sg.Text(key="output", font=data_font, size=biggest_size, expand_x=True, expand_y=True)],
]

icon = b'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0'
# window = sg.Window(
#     title="BeetleChat Orchestrator " + config.get_config_value('version', ''),
#     layout=layout,
#     resizable=True,
#     finalize=True,
#     icon=icon,
#     titlebar_icon=icon,
#     use_custom_titlebar=True,
#     titlebar_font=('', 17)
# )  # mod-dch: 5/19

window = sg.Window(f"BeetleChat Orchestrator {app_version}",
                   layout, resizable=True, finalize=True, icon=icon)

def update_output(win, content):
    # Display content in output window
    if content:
        if isinstance(content, tuple):
            content = content[1]
        # print("content", str(content))
        win["output"].update(str(content))


def toggle_subtitles(on):
    window['toggle_subtitles'].update(text=pause_message if on else resume_message)


def message(content):
    global status
    status = content + "\n" + status
    update_output(window, status)


def current_obs_scene(stream, background):
    if stream:
        window["current_stream_scene"].update(stream)
    if background:
        window["current_background_scene"].update(background)


def update_shows(current=None, next=None, upcoming=list()):
    if current:
        window["current_show"].update(f"{current}")
    if next:
        window["next_show"].update(f"{next}")
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
    msg = "Driver" if connected else "Driver (Not Connected)"
    window["driver_label"].update(msg)

    uid = "to " + driver_name if driver_name else default_driver
    window["timer_label"].update("No dashboard connection" if not connected else f"Connected {uid}")


# TODO these two functions really shouldn't go here
def connect_to_obs_stream():
    window['stream_connected'].update("Connecting...")
    stream_ip = window['stream_ip'].get()
    stream_port = window['stream_port'].get()
    stream_password = window['stream_password'].get()
    try:
        connected, msg = obsc_stream.update_obs_connection(stream_ip, stream_port, stream_password)
        window['stream_connected'].update(msg)
        return 'connected', msg
    except Exception as e:
        print('ERROR (connecting to OBS-stream)', e)


def connect_to_obs_background():
    window['background_connected'].update("Connecting...")
    background_ip = window['background_ip'].get()
    background_port = window['background_port'].get()
    background_password = window['background_password'].get()
    try:
        connected, msg = obsc_background.update_obs_connection(background_ip, background_port, background_password)
        window['background_connected'].update(msg)
        return 'connected', msg
    except Exception as e:
        print('ERROR (connecting to OBS-background)', e)

def automode():
    auto = window['automode'].get()
    config.write_value("automode", auto)
    msg = f"Force automode set to: {auto}"
    message(msg)


def use_tts():
    tts_enabled = window['use_tts'].get()
    config.write_value("use_tts", tts_enabled)
    msg = f"Option tts_enabled set to: {tts_enabled}"
    message(msg)


def do_scene_cut(stream=None, background=None, interstitial=None):
    # Not sure this should go here
    stream_msg, background_msg = cut_to_scenes(
        stream,
        background,
        interstitial
    )
    current_obs_scene(stream_msg, background_msg)
    message(str(stream_msg) + "\n" + str(background_msg))


def clear_subtitles():
    window['subtitles'].update(value="")
    window['upcoming_subtitles'].update(value="")


def main_loop_gui(win):
    while True and win:
        event, values = win.read(timeout=100)
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
            update_output(win, result)
        elif event == "new_next_show":
            # TODO move this somewhere
            nxt = values[0]
            upcoming = values[1] # ??
            upcoming = upcoming[1:] if len(upcoming) > 1 else []
            update_shows(next=nxt, upcoming=values[1])
        else:
            event_queue.put((event, values))

perf.stop()
