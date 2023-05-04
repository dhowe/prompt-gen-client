import obs_control
from obs_control import obsc_stream, obsc_background

import dashboard_socket
import threading
import config
import shows
import gui

window = gui.window
event_queue = gui.event_queue
dashboard_socket.update_driver(gui.default_driver, gui.default_driver_pass)
schedule = shows.schedule

# Set the GUI callback for updating the subtitles
def on_subtitles(text):
    window['subtitles'].update(value=text)
obsc_stream.on_subtitles_update = on_subtitles

gui_thread = threading.Thread(target=gui.event_loop, args=(window,))
listen_thread = threading.Thread(target=dashboard_socket.listen)
show_thread = threading.Thread(target=shows.check_for_shows, args=(event_queue,))
gui_thread.start()
show_thread.start()

# Main event loop for listening to GUI events
while True:
    event, values = window.read(timeout=100)

    if event != "__TIMEOUT__":
        # print('event', event, values)
        pass
    if event == gui.sg.WIN_CLOSED:
        break
    elif event == "update_driver":
        dashboard_socket.manual_disconnect()
        result = dashboard_socket.update_driver(values['driver_uid'], values['driver_password'])
        config.write_config_value("dashboard_user", values['driver_uid'])
        config.write_config_value("dashboard_password", values['driver_password'])
        gui.message(result)
        listen_thread = threading.Thread(target=dashboard_socket.listen)
        listen_thread.start()
    elif event == "update_sheet":
        config.write_config_value("google_sheet_show_sheet_name", values["sheet"])
        shows.do_show_check_and_generate_event(event_queue)
    elif event == "set_sleep_time":
        result = obsc_stream.set_subtitle_sleep_time(values["sleep_time"])
        gui.message(result)
    elif event == "set_rand_delay":
        result = obsc_stream.set_subtitle_max_rand_delay(values["max_rand"])
        gui.message(result)
    elif event == "set_blank_hold":
        result = obsc_stream.set_subtitle_blank_hold(values["blank_hold"])
        gui.message(result)
    elif event == "start_stop_schedule":
        on = schedule.toggle()
        if on and schedule.next_show:
            window['start_stop_schedule'].update(text=gui.stop_message, button_color='red')
        else:
            window['start_stop_schedule'].update(text=gui.start_message, button_color=gui.sg.theme_button_color())
        
        if schedule.next_show:
            message = f"{'Start' if on else 'Stopp'}ing schedule. Next show: {schedule.next_show}"
        else:
            message = "No shows scheduled."
        gui.message(message)
        # event_queue.put(("")) # change GUI TOOD
    elif event == gui.dashboard_event:
        gui.dashboard_action()
    elif event == gui.shows_event:
        gui.shows_action()
    elif event in gui.actions():
        event_queue.put((event, values))

    
# Stop the background thread
event_queue.put(("stop", None))
gui_thread.join()
listen_thread.join()
show_thread.join()
window.close()