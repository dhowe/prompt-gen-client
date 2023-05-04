from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import io
from googleapiclient.http import MediaIoBaseDownload

# Authenticate using the same service account as before
creds = Credentials.from_service_account_file('google_sheets_access.json')

# Create a Drive API client
drive_service = build('drive', 'v3', credentials=creds)

def get_file_id_from_url(file_url):
    """
    Given a Google Drive file URL, returns the file ID.
    """
    split_url = file_url.split("/")
    file_id = split_url[5]
    return file_id


def get_json_data(filename):
    """
    return (content, message)
        content: bytes object
        message: string
    """
    content = None
    try:
        file_id = get_file_id_from_url(filename)
    except Exception as e:
        print(e)
        return None, "Unable to retrieve Scene JSON."

    print(file_id)
    try:
        # Use the Drive API client to download the file
        file = drive_service.files().get(fileId=file_id).execute()
        file_name = file['name']
        file_content = io.BytesIO()
        request = drive_service.files().get_media(fileId=file_id)
        media = MediaIoBaseDownload(file_content, request)
        done = False
        while done is False:
            _, done = media.next_chunk()
        content = file_content.getvalue()
        try:
            content = content.decode("utf-8")
        except UnicodeDecodeError:
            content = content
    except Exception as e:
        message = e

    message = f"Successfully downloaded"
    return content, message

# https://drive.google.com/file/d/119s7vwybLpmjMgffnyOlBrv7aH3R1ncU/view?usp=sharing
get_json_data("https://drive.google.com/file/d/119s7vwybLpmjMgffnyOlBrv7aH3R1ncU/view?usp=share_link")