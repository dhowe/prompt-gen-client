import gspread
import pandas as pd
import config
import pytz
import threading
import gui
import obs_control
import drive_files
import time
from dashboard_socket import start_show, dashboard_load_scene_counter

pd.options.mode.use_inf_as_na = True
TIMEZONE = config.get_value("timezone")


class Show:
    def __init__(self, data, get_json_data=True):
        self.data = data
        self.name = data.get("ShowName", "ShowName missing")
        self.artist = data.get("ArtistName", "ArtistName missing")
        self.date = data.get("Date", "Date missing")
        self.time = data.get("Time", "Time missing")
        self.obs_scene_changes = {
            "stream": data.get("Stream Scene"),
            "background": data.get("Background Scene"),
            "interstitial": data.get("Interstitial Scene"),
            "starting_soon": config.get_value("starting_soon_scene"),
        }
        self.link = data.get('Link')

        self.json = None
        self.json_file_name = None
        if get_json_data:
            self._update_json()

        self.did_start = False
        self.did_interstitial = False
        self.did_starting_soon = False
        self.did_load_to_dashboard = False

    def __repr__(self):
        content = f"{self.name} at {self.time}"
        content += f" Stream: {self.obs_scene_changes['stream']}"
        content += f" Background: {self.obs_scene_changes['background']}"
        content += f" Interstitial: {self.obs_scene_changes['interstitial']}"
        # content += f" Title Card: {self.obs_scene_changes['starting_soon']}"
        content += f" Scene File: {self.json_file_name}" if self.json_file_name else ""
        return content

    def _update_json(self, do_message=False):
        if do_message:
            gui.message(f"Updating json for {self.link}")

        if self.link:
            self.json, self.json_file_name, message = drive_files.get_json_data(self.link)
        else:
            self.json, self.json_file_name = None, None
            message = "No show link"

        if do_message:
            gui.message(f"{message} for {self.link}")

    def load_scene_to_dashboard(self):
        """
        Send the json on to the dashboard to begin generation
        """
        self.did_load_to_dashboard = True
        self._update_json(do_message=True)  # Just in case it changed
        if self.json:
            gui.update_timer(f"Loading show: {self.name}...")
            tmp_count = dashboard_load_scene_counter
            name = (self.name or "Untitled") + " " + (self.json_file_name or "")
            start_show(self.json, name)
            time.sleep(1)  # wait for the dashboard to respond
            if dashboard_load_scene_counter > tmp_count:
                message = f"Started {self.name}: {self.json_file_name}"
            else:
                message = f"Failed to start {self.name}: {self.json_file_name}"
        else:
            message = f"No json found for {self.link}"

        obs_control.obsc_stream.clear_subtitles_queue()
        gui.clear_subtitles()
        obs_control.obsc_stream.pause_subtitles()
        obs_control.obsc_stream.bypass_queue_write_empty_subtitles()

        gui.message(message)

    def start(self):
        if not self.did_load_to_dashboard:
            self.load_scene_to_dashboard()

        self.did_start = True

        if self.json:
            # Cut to the scene
            gui.do_scene_cut(
                stream=self.obs_scene_changes["stream"],
                background=self.obs_scene_changes["background"]
            )
            # Resume the subtitles (which should have a queue by now)
            obs_control.obsc_stream.play_subtitles()
            gui.message(f"!Show started!")
        else:
            gui.message(f"Not cutting to {self.name} because no json was found.")

    def interstitial(self):
        self.did_interstitial = True
        scene = self.obs_scene_changes["interstitial"]
        gui.do_scene_cut(interstitial=scene)

        self.load_scene_to_dashboard()
        gui.message(f"!Interstitial!")

    def starting_soon(self):
        if not self.did_load_to_dashboard:
            self.load_scene_to_dashboard()

        self.did_starting_soon = True
        obs_control.obsc_stream.populate_text_boxes(
            self.data)  # any of the rows in the sheet can be used as a source of text
        time.sleep(0.05)
        gui.do_scene_cut(stream=self.obs_scene_changes["starting_soon"])
        gui.message(f"!Starting soon!")


class ShowSchedule:
    def __init__(self) -> None:
        self.on = False
        self.upcoming_shows = None
        self.next_show = None

        self.timer_thread = None
        self._time_until_next_show = None

        self.countdown_actions = {}

    def toggle(self):
        if not self.on:
            self.begin_schedule()
        else:
            self.stop_schedule()
        return self.on

    def set_next_show(self, nextshow: Show, upcoming_shows=None):
        self.next_show = nextshow
        if upcoming_shows:
            self.upcoming_shows = upcoming_shows

    def add_countdown_action(self, name, advance_time, action):
        self.countdown_actions[name] = (advance_time, action)

    def remove_countdown_action(self, name):
        del self.countdown_actions[name]

    def get_time_until_next_show(self):
        if self.next_show is None:
            return None, None, None
        now = pd.Timestamp.now(tz=TIMEZONE)

        time_until_interstitial = self.next_show.data['show_sequence_start'] - now
        time_until_title = time_until_interstitial + pd.Timedelta(
            seconds=float(obs_control.obsc_stream.interstitial_time))
        self._time_until_next_show = time_until_title + pd.Timedelta(
            seconds=float(obs_control.obsc_stream.starting_soon_time))

        return self._time_until_next_show, time_until_title, time_until_interstitial

    def begin_schedule(self):
        self.timer_thread = threading.Thread(target=self.timer_loop)
        self.on = True
        self.timer_thread.start()

    def stop_schedule(self):
        # terminate timer thread
        if self.timer_thread:
            self.on = False
            self.timer_thread.join()
            self.clear()

    def clear(self):
        gui.update_timer(None)
        obs_control.obsc_stream.clear_subtitles_queue()

    def timer_loop(self):
        start_time = time.time()
        time_until_show, time_until_title, time_until_interstitial = self.get_time_until_next_show()

        gui.update_shows(next=self.next_show, upcoming=self.upcoming_shows)  # update the GUI
        while self.on:
            if time_until_show is None:
                return

            time_until_show, time_until_title, time_until_interstitial = self.get_time_until_next_show()
            # clamp to 0
            time_until_show = pd.Timedelta(seconds=0) if time_until_show < pd.Timedelta(seconds=0) else time_until_show
            time_until_title = pd.Timedelta(seconds=0) if time_until_title < pd.Timedelta(
                seconds=0) else time_until_title
            time_until_interstitial = pd.Timedelta(seconds=0) if time_until_interstitial < pd.Timedelta(
                seconds=0) else time_until_interstitial

            start_thresh = 1

            # Do the things that need to get done before or at the show
            if time_until_show <= pd.Timedelta(seconds=start_thresh):
                if not self.next_show.did_start:  # if the show hasn't been attempted to start yet
                    self.next_show.start()
                    # Not sure that these should go here...
                    gui.clear_subtitles()
                    obs_control.obsc_stream.clear_subtitles_queue()
                    obs_control.obsc_stream.play_subtitles()
                    self.update_shows_gui()

                    result, error = do_show_check()
                    if result:
                        nextshow, upcoming_shows = result
                        schedule.set_next_show(nextshow, upcoming_shows)
                        gui.update_shows(next=nextshow, upcoming=upcoming_shows)
                    elif error:
                        gui.update_shows(next=nextshow, upcoming=upcoming_shows)
                    else:
                        gui.update_shows(None, [])

            elif time_until_title <= pd.Timedelta(seconds=start_thresh):
                if not self.next_show.did_starting_soon:
                    self.next_show.starting_soon()
            elif time_until_interstitial <= pd.Timedelta(seconds=start_thresh):
                if not self.next_show.did_interstitial:
                    self.next_show.interstitial()

            gui.update_timer(time_until_show, time_until_title, time_until_interstitial)

            # for name, (advance_time, action) in self.countdown_actions.items():
            #     print(name, advance_time)
            #     if countdown <= pd.Timedelta(seconds=advance_time):
            #         action()

            time.sleep(1 - ((time.time() - start_time) % 1))  # sleep until the next second

    def update_shows_gui(self):
        gui.update_shows(
            current=self.next_show,
            next=self.upcoming_shows[1] if self.upcoming_shows is not None and len(self.upcoming_shows) > 1 else None,
            upcoming=self.upcoming_shows[2:] if self.upcoming_shows is not None and len(
                self.upcoming_shows) > 2 else None,
        )


schedule = ShowSchedule()


def get_all_shows():
    try:
        sheet_id = config.get_value("google_sheet_show_id")
        sheet_name = config.get_value("google_sheet_show_sheet_name")
        gc = gspread.service_account('google_sheets_access.json')
        spreadsheet = gc.open_by_key(sheet_id)
        worksheet = spreadsheet.worksheet(sheet_name)
        rows = worksheet.get_all_values()
        # print the number of rows and each of the ShowName cells
        df = pd.DataFrame(rows[2:], columns=rows[1])  # Use the second row as headers and skip the first row
        df = df[df['Date'].notna() & df['Time'].notna()]
        df = df[df['Date'].str.strip() != ""]
        df = df[df['Time'].str.strip() != ""]
        datetime_str = df['Date'] + ' ' + df['Time']
        df['datetime'] = pd.to_datetime(datetime_str, errors='coerce')
        df = df[df['datetime'].notna()]

        return df
    except Exception as e:
        # print the stack trace
        gui.message(f"Error parsing sheet: {e}")
        return None


def get_upcoming_shows():
    all_shows_df = get_all_shows()

    if all_shows_df is None or all_shows_df.empty:
        return None

    now = pd.Timestamp.now(tz=TIMEZONE)

    # TODO the current problem is that the Time is needed for deciding which show is next
    # but we just changed it to represent the interstitial time
    # SO we should delay it here by the interstitial + the starting soon time, or do something smarter over there

    # Add a 'local_datetime' field for each show
    all_shows_df['local_datetime'] = all_shows_df.apply(localize_show_datetime, axis=1)
    # The actual time the show will start, accounting for the interstitial and title card sequence
    all_shows_df['show_sequence_start'] = all_shows_df.apply(calculate_show_sequence_start, axis=1)

    upcoming_shows = all_shows_df[all_shows_df['show_sequence_start'] > now].sort_values('show_sequence_start')
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


def calculate_show_sequence_start(row):
    """
    Returns the time that the show sequence should start.
    This is the time that the interstitial should start.
    """
    interstitial_time = float(obs_control.obsc_stream.interstitial_time)
    starting_soon_time = float(obs_control.obsc_stream.starting_soon_time)

    return row['local_datetime'] - pd.Timedelta(seconds=(interstitial_time + starting_soon_time))


def get_next_show(upcoming_shows):
    if upcoming_shows is None:
        return None
    try:
        nextshow = upcoming_shows.iloc[0]
        return Show(nextshow.to_dict())
    except (KeyError, ValueError):
        return None


def do_show_check():
    prev_next_show = None
    result = None
    try:
        upcoming_shows = get_upcoming_shows()
        nextshow = get_next_show(upcoming_shows)

        if (nextshow and not prev_next_show) or \
                (prev_next_show and nextshow and prev_next_show['datetime'] != nextshow['datetime']):
            upcoming_shows_objects = \
                upcoming_shows.apply(lambda row: Show(row, get_json_data=False), axis=1).tolist()
            result = (nextshow, upcoming_shows_objects)
        prev_next_show = nextshow
        return result, None
    except Exception as e:
        return None, e


def do_show_check_and_set_next_show():
    result, error = do_show_check()
    if result:
        nextshow, upcoming_shows = result
        schedule.set_next_show(nextshow, upcoming_shows)
        gui.update_shows(next=nextshow, upcoming=upcoming_shows)
    elif error:
        # gui.update_shows(next=nextshow, upcoming=upcoming_shows)
        gui.update_shows(next=None, upcoming=None) # updated: DCH 5/25
    else:
        gui.update_shows(None, [])


# def check_for_shows(event_queue):
#     """
#     Function to run in a separate thread to check for upcoming shows
#     """
#     while True:
#         do_show_check_and_set_next_show()
#         time.sleep(8)

if __name__ == "__main__":
    print("all_shows", get_all_shows())
    upcoming = get_upcoming_shows()
    print("upcoming_shows", upcoming)
    next_show = get_next_show(upcoming)
    print(next_show)
