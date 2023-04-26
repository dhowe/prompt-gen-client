import obs_control
import socketio_control
import threading

if __name__ == '__main__':
    window = obs_control.window
    event_queue = obs_control.event_queue
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
        elif event in obs_control.actions():
            # Send the event to the background thread
            event_queue.put((event, values))
            # print the items in the queu
            print(event_queue.qsize())

        # Check if there are any updates from the background thread
        # while not event_queue.empty():
        #     event, content = event_queue.get()
        #     if event == "update_output":
        #         obs_control.update_output(window, content)
        #     else: 
        #         event_queue.put((event, content))
            


    # Stop the background thread
    event_queue.put(("stop", None))
    gui_thread.join()
    listen_thread.join()
    window.close()