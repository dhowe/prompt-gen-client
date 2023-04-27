import obs_control
import socketio_control
import threading

if __name__ == '__main__':
    window = obs_control.window
    event_queue = obs_control.event_queue
    socketio_control.update_driver(obs_control.default_driver)

    gui_thread = threading.Thread(target=obs_control.event_loop, args=(window,))
    listen_thread = threading.Thread(target=socketio_control.listen)
    listen_thread.start()
    gui_thread.start()
    
    # Main event loop
    while True:
        event, values = window.read(timeout=100)

        if event != "__TIMEOUT__":
            print('event', event, values)
        if event == obs_control.sg.WIN_CLOSED:
            break
        elif event == "update_driver":
            result = socketio_control.update_driver(values['driver_uid'])
            obs_control.write_driver_uid(values['driver_uid'])
            obs_control.update_output(window, result)
        elif event in obs_control.actions():
            # Send the event to the background thread
            event_queue.put((event, values))
        elif event == "set_sleep_time":
            result = obs_control.obsc.set_subtitle_sleep_time(values["sleep_time"])
            obs_control.update_output(window, result)

    # Stop the background thread
    event_queue.put(("stop", None))
    gui_thread.join()
    listen_thread.join()
    window.close()