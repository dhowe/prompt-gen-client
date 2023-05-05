import gspread
import pandas as pd
import config
import pytz
import time, threading
import gui
import obs_control
import drive_files
from dashboard_socket import start_show, responses

TIMEZONE = config.get_config_value("timezone")

class Show:
    def __init__(self, data, get_json_data=True):
        self.data = data
        self.name = data.get("Name", "Name missing")
        self.date = data.get("Date", "Date missing")
        self.time = data.get("Time", "Time missing")
        self.obs_scene_changes = {
            "stream": data.get("Stream Scene"),
            "background": data.get("Background Scene"),
            "interstitial": data.get("Interstitial Scene"),
        }
        self.link = data['Link']

        self.json = None
        if get_json_data:
            self.json = self._update_json()

        self.started = False

    def __repr__(self):
        content = f"{self.name} starting at {self.time} {self.date}"
        content += f" Cutting to scene: {self.obs_scene_changes['stream']}"
        content += f", background: {self.obs_scene_changes['background']}"
        return content
    
    def _update_json(self):
        if self.link:
            self.json, message = drive_files.get_json_data(self.link)
        else:
            self.json = None
            message = "No show link"

        gui.message(message + f" for {self.link}")

    def start(self):
        if not self.json:
            print("no json")
            self._update_json()
        
        if self.json:
            print("yess json")
            gui.update_timer(f"Starting show {self.name}")
            count = responses['load_scene_recieved']
            start_show(self.json)
            self.started = True
            time.sleep(2)
            if responses['load_scene_recieved'] > count:
                message = f"Started {self.data['Name']}"
            else:
                message = f"Failed to start {self.data['Name']}"
        else:
            message = "No json found for", self.link

        print("cut to scenes")
        obs_control.cut_to_scenes(
            self.obs_scene_changes["stream"], 
            self.obs_scene_changes["background"]
        )
        
        print(message)
        gui.message(message)

        

class ShowScheduleState:
    def __init__(self) -> None:
        self.on = False
        self.upcoming_shows = None
        self.next_show = None

        self.timer_thread = None
        self._time_until_next_show = None

        self.countdown_actions = {}

    def toggle(self):
        self.on = not self.on
        if self.on:
            self.begin_schedule()
        else:
            self.end_schedule()
        return self.on
    
    def set_next_show(self, next_show, upcoming_shows=None):
        self.next_show = next_show
        if upcoming_shows:
            self.upcoming_shows = upcoming_shows
    
    def add_countdown_action(self, name, advance_time, action):
        self.countdown_actions[name] = (advance_time, action)
    
    def remove_countdown_action(self, name):
        del self.countdown_actions[name]
    
    def get_time_until_next_show(self):
        if self.next_show is None:
            return None
        now = pd.Timestamp.now(tz=TIMEZONE)
        self._time_until_next_show = self.next_show.data['local_datetime'] - now
        return self._time_until_next_show
    
    def begin_schedule(self):
        self.timer_thread = threading.Thread(target=self.start_timer)
        self.timer_thread.start()

    def end_schedule(self):
        # terminate timer thread
        self.timer_thread.join()
        gui.update_timer(None)

    def start_timer(self):
        countdown = self.get_time_until_next_show()
        gui.update_next_show(self.next_show, self.upcoming_shows) # update the GUI
        i = 0
        while self.on:
            if countdown is None:
                return
            countdown -= pd.Timedelta(seconds=1)

            # check if it is less than a second until the next show
            if countdown <= pd.Timedelta(seconds=1):
                self.next_show.start()

            if (i % 60) == 0:
                countdown = self.get_time_until_next_show()
            gui.update_timer(countdown)

            for name, (advance_time, action) in self.countdown_actions.items():
                if countdown <= advance_time:
                    action()

            time.sleep(1)

schedule = ShowScheduleState()

def get_all_shows():
    sheet_id = config.get_config_value("google_sheet_show_id")
    sheet_name = config.get_config_value("google_sheet_show_sheet_name")
    gc = gspread.service_account('google_sheets_access.json')
    spreadsheet = gc.open_by_key(sheet_id)
    worksheet = spreadsheet.worksheet(sheet_name)
    rows = worksheet.get_all_records()
    try:
        df = pd.DataFrame(rows)
        df['datetime'] = pd.to_datetime(df['Date'] + ' ' + df['Time'])
        return df
    except (KeyError, ValueError):
        return None
    

def get_upcoming_shows():
    all_shows_df = get_all_shows()

    if all_shows_df is None or all_shows_df.empty:
        return None

    now = pd.Timestamp.now(tz=TIMEZONE)

    # Add a 'local_datetime' field for each show
    all_shows_df['local_datetime'] = all_shows_df.apply(localize_show_datetime, axis=1)
    upcoming_shows = all_shows_df[all_shows_df['local_datetime'] > now].sort_values('local_datetime')
    if upcoming_shows.empty:
        return None
    
    return upcoming_shows


def localize_show_datetime(row):
    timezone = row['Timezone']

    if not pd.isna(timezone):
        try:
            show_tz = pytz.timezone(timezone)
        except pytz.UnknownTimeZoneError:
            show_tz = TIMEZONE
    else:
        show_tz = TIMEZONE
    show_dt = row['datetime']
    # encode the datetime, which is already in show_tz as a time aware datetime
    show_dt_tz = show_tz.localize(show_dt)

    return show_dt_tz


def get_next_show(upcoming_shows):
    if upcoming_shows is None:
        return None
    try:
        next_show = upcoming_shows.iloc[0]
        return Show(next_show.to_dict())
    except (KeyError, ValueError):
        return None
    
def do_show_check():
    prev_next_show = None
    result = None
    try:
        upcoming_shows = get_upcoming_shows()
        next_show = get_next_show(upcoming_shows)

        if (next_show and not prev_next_show) or \
            (prev_next_show and next_show and prev_next_show['datetime'] != next_show['datetime']):
            upcoming_shows_objects = \
                  upcoming_shows.apply(lambda row: Show(row, get_json_data=False), axis=1).tolist()
            result = (next_show, upcoming_shows_objects)
        prev_next_show = next_show
        return result, None
    except Exception as e:
        return None, e
    
def do_show_check_and_generate_event(event_queue):
    event_queue.put(("update_output", "Checking for new shows"))
    result, error = do_show_check()
    if result:
        next_show, upcoming_shows = result
        schedule.set_next_show(next_show, upcoming_shows)
        event_queue.put(("new_show", result))
    elif error:
        event_queue.put(("new_show", "Error retrieving show: " + str(error)))
    
def check_for_shows(event_queue):
    """
    Function to run in a separate thread to check for upcoming shows
    """
    while True:
        do_show_check_and_generate_event(event_queue)
        time.sleep(8)

if __name__ == "__main__":
    print("all_shows", get_all_shows())
    upcoming_shows = get_upcoming_shows()
    print("upcoming_shows", upcoming_shows)
    next_show = get_next_show(upcoming_shows)
    print(next_show)