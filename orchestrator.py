import obs_control
from obs_control import obsc_stream, available_function_dict

import dashboard_socket
import threading
import config
import shows
import gui

# NEXT: reverse elements before putting at queue head OR keep on 'on-deck' space for sendNow msgs

window = gui.window
event_queue = gui.event_queue
dashboard_socket.update_driver(gui.default_driver, gui.default_driver_pass)
schedule = shows.schedule

# Set the GUI callback for updating the subtitles
def on_subtitles(text, upcoming_list):
    window['subtitles'].update(value=text)
    print(upcoming_list)
    if upcoming_list:
        upcoming = "\n".join(upcoming_list)
        window["upcoming_subtitles"].update(value=upcoming)
obsc_stream.on_subtitles_update = on_subtitles

def technical():
    """Cut to the technical difficulties scene"""
    print("technical difficulties")
    gui.message("Cutting to technical difficulties, pausing subtitles")
    schedule.stop_schedule()
    obs_control.obsc_stream.pause_subtitles()
    gui.toggle_subtitles(False)
    stop_schedule_gui(window)
    tech_scene = config.get_config_value("technical_difficulties_scene", "Technical Difficulties")
    response = obsc_stream.cut_to_scene(tech_scene)
    if obsc_stream.connected:
        gui.current_obs_scene(tech_scene, None)

    return response
obs_control.add_function("technical", technical)

def off_air():
    """Cut to the off_air"""
    gui.message("Cutting to off air")
    return obsc_stream.cut_to_scene(config.get_config_value("off_air_scene", "Off Air"))
obs_control.add_function("technical", technical)


def toggle_subtitles():
    """Play/pause the subtitles"""
    on = obsc_stream.toggle_subtitles_on()
    gui.toggle_subtitles(on)
    gui.message("Resuming subtitles" if on else "Pausing subtitles")
obs_control.add_function("toggle_subtitles", toggle_subtitles)

def clear_subtitles():
    """Clear the subtitles"""
    obsc_stream.clear_subtitles_queue()
    gui.clear_subtitles()
    obsc_stream.bypass_queue_write_empty_subtitles()
obs_control.add_function("clear_subtitles", clear_subtitles)

def start_schedule_gui(window):
    window['start_stop_schedule'].update(text=gui.stop_message, button_color='red')
    message = f"Starting schedule." + f" Next show: {schedule.next_show}" if schedule.next_show else  "Schedule started: No shows scheduled."
    gui.message(message)
    event_queue.put(("update_output", message))

def stop_schedule_gui(window):
    window['start_stop_schedule'].update(text=gui.start_message, button_color=gui.sg.theme_button_color())
    message = "Stopping schedule."
    event_queue.put(("update_output", message))

def start_stop_schedule(window):
    on = schedule.toggle()
    if on:
        start_schedule_gui(window)
    else:
        stop_schedule_gui(window)


def orchestrator_loop():
    listen_thread = threading.Thread(target=dashboard_socket.listen)
    # show_thread = threading.Thread(target=shows.check_for_shows, args=(event_queue,))
    listen_thread.start()
    # show_thread.start()

    # Main event loop for listening to GUI events
    while True:
        event, values = event_queue.get()
        
        if event == "update_driver":
            dashboard_socket.manual_disconnect()
            result = dashboard_socket.update_driver(values['driver_uid'], values['driver_password'])
            config.write_config_value("dashboard_user", values['driver_uid'])
            config.write_config_value("dashboard_password", values['driver_password'])
            gui.message(result)
            listen_thread = threading.Thread(target=dashboard_socket.listen)
            listen_thread.start()
        elif event == "update_sheet":
            gui.message(f"Fetching show schedule from {values['sheet']}")
            config.write_config_value("google_sheet_show_sheet_name", values["sheet"])
            shows.do_show_check_and_set_next_show()
            shows.schedule.update_shows_gui()
            gui.message("Updated schedule")
        elif event == "set_sleep_time":
            result = obsc_stream.set_subtitle_sleep_time(values["sleep_time"])
            gui.message(result)
        elif event == "set_rand_delay":
            print("setting rand delay")
            result = obs_control.obsc_stream.set_config_value_from_gui("max_rand", float(values["max_rand"]))
            print(config.get_config_value("max_rand"))
            gui.message(result)
        elif event == "set_blank_hold":
            # TODO these should get consolidated into a single function
            result = obsc_stream.set_subtitle_blank_hold(values["blank_hold"])
            gui.message(result)
        elif event == "set_interstitial_time":
            result = obs_control.obsc_stream.set_config_value_from_gui("interstitial_time", values["interstitial_time"])
            gui.message(result)
        elif event == "set_starting_soon_time":
            result = obs_control.obsc_stream.set_config_value_from_gui("starting_soon_time", values["starting_soon_time"])
            gui.message(result)
        elif event == "set_min_delay":
            result = obs_control.obsc_stream.set_config_value_from_gui("min_delay", float(values["min_delay"]))
            gui.message(result)
        elif event == "start_stop_schedule":
            start_stop_schedule(window)
        elif event == gui.dashboard_event:
            gui.dashboard_action()
        elif event == gui.shows_event:
            gui.shows_action()
        elif event == "connect_to_obs_background":
            gui.connect_to_obs_background()
        elif event == "automode":
            gui.automode()
        elif event == "connect_to_obs_stream":
            gui.connect_to_obs_stream()
        elif event in available_function_dict.keys():
            event_queue.put((event, values))

    # Stop the background thread
    event_queue.put(("stop", None))
    listen_thread.join()
    # show_thread.join()
    window.close()


if __name__ == "__main__":
    orchestrator_thread = threading.Thread(target=orchestrator_loop)
    orchestrator_thread.start()
    gui.main_loop_gui(gui.window)  # The GUI has to be on the main thread because tkinter is not thread safe
    orchestrator_thread.join()
