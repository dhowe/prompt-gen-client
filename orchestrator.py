import obs_control
import socketio_control
import threading

if __name__ == '__main__':
    window = obs_control.window
    gui_thread = threading.Thread(target=obs_control.event_loop, args=(window,))
    listen_thread = threading.Thread(target=socketio_control.listen)
    listen_thread.start()
    gui_thread.start()

    
    # Main event loop
    while True:
        event, values = window.read(timeout=100)

        if event == obs_control.sg.WIN_CLOSED:
            break
        elif event in obs_control.actions():
            print('put', event)
            # Send the event to the background thread
            obs_control.queue.put((event, values))
            # print the items in the queu
            print(obs_control.queue.qsize())

        # Check if there are any updates from the background thread
        while not obs_control.queue.empty():
            event, content = obs_control.queue.get()
            if event == "update_output":
                obs_control.update_output(window, content)

    # Stop the background thread
    obs_control.queue.put(("stop", None))
    gui_thread.join()
    listen_thread.join()
    window.close()