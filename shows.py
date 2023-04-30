import datetime
import gspread
import pandas as pd
import config
import pytz
from datetime import datetime

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
    
def get_next_show():
    all_shows_df = get_all_shows()

    if all_shows_df is None or all_shows_df.empty:
        return None

    try:
        now = pd.Timestamp.now(tz=TIMEZONE).to_datetime64()
        next_shows = all_shows_df[all_shows_df['datetime'] > now].sort_values('datetime')

        if next_shows.empty:
            return None

        # Get the next show
        next_show = next_shows.iloc[0]

        # Determine the timezone for the next show
        timezone = next_show['Timezone']
        if not pd.isna(timezone):
            try:
                next_show_tz = pytz.timezone(timezone)
            except pytz.UnknownTimeZoneError:
                next_show_tz = TIMEZONE
        else:
            next_show_tz = TIMEZONE

        # Convert the datetime object to the timezone for the next show
        next_show_dt = next_show['datetime']
        next_show_dt_tz = pytz.utc.localize(next_show_dt.to_pydatetime()).astimezone(next_show_tz)

        # Update the 'datetime' field with the localized datetime
        next_show['datetime'] = next_show_dt_tz

        # Return the entire row as a dictionary
        return next_show.to_dict()
    except (KeyError, ValueError):
        return None




print(get_next_show())