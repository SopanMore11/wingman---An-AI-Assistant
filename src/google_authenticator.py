import os.path
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# SCOPES = ['https://www.googleapis.com/auth/calendar.events']
SCOPES = ['https://www.googleapis.com/auth/calendar']



def authenticate_google_calendar():
    """Authenticates the user and returns the Google Calendar service object."""
    creds = None
    # The file token.json stores the user's access and refresh tokens
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError:
                # The refresh token is invalid/expired/revoked. Remove the
                # local token so we can run the full OAuth flow again.
                if os.path.exists('token.json'):
                    try:
                        os.remove('token.json')
                    except OSError:
                        pass
                creds = None
        if not creds:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            with open('token.json', 'w') as token:
                token.write(creds.to_json())

    # Build and return the service object
    service = build('calendar', 'v3', credentials=creds)
    return service