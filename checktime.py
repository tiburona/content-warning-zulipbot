import datetime
import pytz
import zulip
from .private_vars import zulip_api_key
from .private_vars import zulip_username

RC_TIMEZONE = pytz.timezone('US/Eastern')

def check_time():
    current_time = datetime.datetime.now(pytz.utc)
    localized_current_time = current_time.astimezone(RC_TIMEZONE)
    current_hour = localized_current_time.hour
    current_day = localized_current_time.weekday()
    return current_hour, current_day

def send_message(to, message):
    client = zulip.Client(zulip_username, zulip_api_key, site="https://recurse.zulipchat.com/api")

    message_data = {
        "type": "private",
        "content": message,
        "subject": message,
        "to": to,
    }

    client.send_message(message_data)


def main():
    hour, day = check_time()
    to = "feelings-checkin-bot@recurse.zulipchat.com"
    if day == 3:
        if hour == 9:
            send_message(to, '9am')
        if hour == 14:
            send_message(to, '2pm')
        if hour == 15:
            send_message(to, '3pm')

if __name__ == "__main__":
    main()
