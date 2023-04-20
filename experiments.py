
# # start a 15 min timer
# # when timer is done, switch to a scene
# def go_to_show_timer():
#     print("Starting timer for 15 minutes...")
#     p = mp.Process(target=_timer)
#     p.start()

# def _timer():
#     # set the countdown every second
#     for i in range(15 * 60):
#         time.sleep(1)
#         display = f"{15 - i // 60}:{60 - i % 60}"
#         window['timer'].update(display)
#         print(display)
#     cl.set_current_program_scene("Scene")
#     time.sleep(0.1 * 60)
#     cl.set_current_program_scene("Cutscene")


def animate_text():
    cur_scene = cl.get_current_program_scene().current_program_scene_name
    items = cl.get_scene_item_list(cur_scene).scene_items
    texts = [i for i in items if i['inputKind'] == 'text_ft2_source_v2']

    name = texts[1]['sourceName']
    id = texts[1]['sceneItemId']

    transform = cl.get_scene_item_transform("Scene", id).scene_item_transform
    
    print(str(transform))
    x = transform['positionX']

    for i in range(50):
        x += 1
        transform['positionX'] = x
        cl.set_scene_item_transform("Scene", id, transform)
        time.sleep(0.1)

    return items 