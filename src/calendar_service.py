import os
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

load_dotenv()  # carrega o .env para os.environ

SCOPES = ["https://www.googleapis.com/auth/calendar"]

creds = service_account.Credentials.from_service_account_file(
    os.environ["GOOGLE_KEY_FILE"], scopes=SCOPES
)
calendar = build("calendar", "v3", credentials=creds, cache_discovery=False)

def ocupados(inicio_iso, fim_iso):
    cal_id = os.environ["CALENDAR_ID"]
    resp = calendar.freebusy().query(
        body={
            "timeMin": inicio_iso,
            "timeMax": fim_iso,
            "timeZone": "America/Sao_Paulo",
            "items": [{"id": cal_id}],
        }
    ).execute()
    print(resp)
    return resp["calendars"][cal_id]["busy"]


if __name__ == "__main__":
    print(ocupados("2026-10-14T00:00:00-03:00", "2026-10-15T00:00:00-03:00"))