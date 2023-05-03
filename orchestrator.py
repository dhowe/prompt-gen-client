import obs_control
import dashboard_socket
import threading
import config
import shows

window = obs_control.window
event_queue = obs_control.event_queue
dashboard_socket.update_driver(obs_control.default_driver)
schedule = shows.schedule

gui_thread = threading.Thread(target=obs_control.event_loop, args=(window,))
listen_thread = threading.Thread(target=dashboard_socket.listen)
show_thread = threading.Thread(target=shows.check_for_shows, args=(event_queue,))
listen_thread.start()
gui_thread.start()
show_thread.start()

# Main event loop
while True:
    event, values = window.read(timeout=100)

    if event != "__TIMEOUT__":
        print('event', event, values)
    if event == obs_control.sg.WIN_CLOSED:
        break
    elif event == "update_driver":
        result = dashboard_socket.update_driver(values['driver_uid'])
        config.write_config_value("dashboard_user", values['driver_uid'])
        obs_control.update_output(window, result)
    elif event == "set_sleep_time":
        result = obs_control.obsc_stream.set_subtitle_sleep_time(values["sleep_time"])
        obs_control.update_output(window, result)
    elif event == "start_stop_shedule":
        on = schedule.toggle()
        if on and schedule.next_show:
            obs_control.update_timer(schedule.time_until_next_show())
            event_queue.put(("schedule_on", None))
            # result = dashboard_socket.start_show(schedule.next_show['JSON'])
        else:
            event_queue.put(("schedule_on", None))
            # result = dashboard_socket.stop_show()
        start_stop = 'start' if on else 'stop'
        obs_control.update_output(window, f"{start_stop}ed schedule. Next show: {schedule.next_show}")
        # event_queue.put(("")) # change GUI TOOD
    elif event in obs_control.actions():
        event_queue.put((event, values))

    
# Stop the background thread
event_queue.put(("stop", None))
gui_thread.join()
listen_thread.join()
show_thread.join()
window.close()