import datetime
import gspread
import pandas as pd
import config
import pytz
from datetime import datetime
import time

class ShowScheduleState:
    def __init__(self) -> None:
        self.on = False
        self.upcoming_shows = None
        self.next_show = None

    def toggle(self):
        self.on = not self.on
        return self.on
    
schedule = ShowScheduleState()

# https://docs.google.com/spreadsheets/d/1lXononLyDu7_--xHODvQwB_h9LywvctLCdbzYRNVZRc/edit#gid=0

TIMEZONE = config.get_config_value("timezone")

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

    now = pd.Timestamp.now(tz=TIMEZONE).to_datetime64()
    upcoming_shows = all_shows_df[all_shows_df['datetime'] > now].sort_values('datetime')

    if upcoming_shows.empty:
        return None
    
    # Add a 'local_datetime' field for each show
    upcoming_shows['local_datetime'] = upcoming_shows.apply(localize_show_datetime, axis=1)

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
    show_dt_tz = pytz.utc.localize(show_dt.to_pydatetime()).astimezone(show_tz)

    return show_dt_tz

def get_next_show(upcoming_shows):
    if upcoming_shows is None:
        return None

    try:
        # Get the next show
        next_show = upcoming_shows.iloc[0]

        # Return the entire row as a dictionary
        return next_show.to_dict()
    except (KeyError, ValueError):
        return None


def check_for_shows(event_queue):
    prev_next_show = None

    while True:
        try:
            upcoming_shows = get_upcoming_shows()
            next_show = get_next_show(upcoming_shows)
            if (next_show and not prev_next_show) or \
                (prev_next_show and next_show and prev_next_show['datetime'] != next_show['datetime']):
                event_queue.put(("new_show", next_show))

                schedule.upcoming_shows = upcoming_shows
                schedule.next_show = next_show

            prev_next_show = next_show
            
        except Exception as e:
            event_queue.put(("new_show", "Error retrieving show: " + str(e)))

        time.sleep(5)

if __name__ == "__main__":
    upcoming_shows = get_upcoming_shows()
    next_show = get_next_show(upcoming_shows)
    print(next_show)