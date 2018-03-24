import datetime
from typing import Any
import pytz
import time
import json

RC_TIMEZONE = pytz.timezone('US/Eastern')

TEXT_REPOSITORY = {
    'usage':
        "I am the Feelings Checkin bot. I remind everyone about Feelings Checkin and collect requests for content "
        "warnings. There are two ways to request content warnings. You can submit topics between 9am and 3pm on "
        "Thursday for that day's Feelings Checkin, or, any day of the week, you can associate a persistent pseudonymous "
        "ID with a content warning request, and mark that ID as attending between 9am and 3pm on Thursday. You can also "
        "subscribe to reminders so you never miss a chance to express your feelings. Use `list-commands` for more "
        "information about what I can do.",
    'stream9am':
        "Good morning! Feelings Checkin will take place at 3pm in Babbage. I'm Feelings Checkin Bot.Send me a message "
        "with the word `help` to find out about the things I can do.",
    'subscribers9am':
        "Happy* Thursday! If you have any requests for content warnings, you can submit them today, or you can activate "
        "any requests associated with an ID by marking yourself as attending Feelings Checkin.\n\n*or disappointed or "
        "enraged or ambivalent -- all feelings about and on Thursdays are valid!",
    'wrong_time':
        "You can only do that between 9am and 3pm on Thursdays. Type `help` for more information."
}

def date_tup_to_obj(date_tup):
    return datetime.date(*date_tup)

class FeelingsCheckinBot(object):
    def usage(self):
        return TEXT_REPOSITORY['usage']

    def initialize(self, bot_handler: Any) -> None:
        self.bot_handler = bot_handler

        initialized_data = json.dumps({'attending': [], 'requests': [], 'ids': {},
                                       'subscriptions': {'9': [], '2': [], '3':[]}})

        self.bot_handler.storage.put('cw', initialized_data)

        self.commands = ['help',
                         'list-commands',
                         'make-id <id> ',
                         'cw-request [options] -r <topic1> [-r <topic2> ...]\n\toptions: -id <id>',
                         'subscribe [9] [2] [3]',
                         'unsubscribe [9] [2] [3]',
                         'will-attend <id>',
                         'will-not-attend <id>']

        self.descriptions = ["Display bot info",
                             "Display the list of available commands","Make a new ID",
                             "Request content warnings (if called with -id, will overwrite previous requests for that id).",
                             "Subscribe to FC reminders (all reminders by default, or a subset with opt. args.)\n\t9: "
                             "the 9am reminder\n\t2: the 2pm reminder\n\t3: the 3pm "
                                             "reminder and content warning request report",
                             "Unsubscribe from FC reminders (all reminders by default, or a subset with opt. args.)",
                             "Mark an ID as attending",
                             "Mark an ID as not attending (only necessary if you previously marked the ID attending)"]

    def get_data(self):
        self.data = json.loads(self.bot_handler.storage.get('cw'))
        return self.data

    def put_data(self, cw_data):
        self.bot_handler.storage.put('cw', json.dumps(cw_data))

    def main(self):
        while True:
            self.check_time()
            time.sleep(60)

    @property
    def time(self):
        current_time = datetime.datetime.now(pytz.utc)
        localized_current_time = current_time.astimezone(RC_TIMEZONE)
        current_hour = localized_current_time.hour
        current_day = localized_current_time.weekday()
        current_date = (localized_current_time.year, localized_current_time.month, localized_current_time.day)
        return {'time': current_time, 'day': current_day, 'hour': current_hour, 'date': current_date}

    def check_time(self):
        current_day = self.time['day']
        current_time = self.time['time']
        current_hour = self.time['hour']
        if current_day == 3:
            if current_hour == 9 and (current_time - self.thurs_am_msg_sent).day > 1:
                self.initialize_thursday(current_time)
            if current_hour == 14 and (current_time - self.one_hour_msg_sent).day > 1:
                self.send_one_hour_notice(current_time)
            if current_hour == 15 and (current_time - self.fc_starting_msg_sent).day > 1:
                self.send_fc_starting_message(current_time)

    def initialize_thursday(self, time):
        cw_data = self.clear_data()
        self.send_message_to_stream(TEXT_REPOSITORY['stream9am'])
        for user in cw_data['subscribers']['9']:
            self.send_private_message(user, TEXT_REPOSITORY['subscribers9am'])
        self.thurs_am_msg_sent = time

    def clear_data(self):
        cw_data = self.get_data()
        cw_data['attending'] = []
        cw_data['requests'] = []
        cw_data = self.clean_old_ids(cw_data, datetime.date(self.time['time']))
        self.put_data(cw_data)
        return cw_data

    def clean_old_ids(self, cw_data, current_date):
        for id in cw_data['ids']:
            last_accessed = date_tup_to_obj(cw_data['ids'][id]['last_accessed'])
            if (current_date - last_accessed).month > 3:
                del cw_data['ids'][id]
        return cw_data

    def send_one_hour_notice(self, time):
        cw_data = self.get_data()
        content = "Feelings Checkin starts in an hour."
        self.send_message_to_stream(content)
        content = "T minus one hour to Feelings Checkin!"
        for user in cw_data['subscribers']['2']:
            self.send_private_message(user, content)
        self.one_hour_msg_sent = time

    def send_fc_starting_message(self, time):
        content = "Feelings checkin is starting."
        self.send_fc_starting_message(time)
        cw_data = self.get_data()
        content += "  These were the topics for which attendees requested content warnings."
        for id in cw_data['attending']:
            cw_data['requests'].extend(cw_data['ids'][id]['requests'])
        for topic in cw_data['requests']:
            content += "\n{}".format(topic)
        for user in cw_data['subscribers']['3']:
            self.send_private_message(user, content)
        self.fc_starting_msg_sent = time

    def send_message_to_stream(self, content):
        self.bot_handler.send_message({
            "type": "stream",
            "to": '455 Broadway',
            "subject": "Feelings Checkin",
            "content": content
        })

    def send_private_message(self, to, content):
        """
        Parameters:
        -----------
        to: string
            Email address of message recipient
        content: string
            Body of message.
        """
        self.send_message({
            "type": "private",
            "to": to,
            "content": content
        })

    def handle_message(self, message: Any, bot_handler: Any) -> None:
        message['content'] = message['content'].strip()

        if message['content'] == '':
            bot_handler.send_reply(message, 'No command specified')
            return

        if message['content'].lower == 'start':
            self.main()
            bot_handler.send_reply(message, 'starting Feelings Checkin bot')

        if message['content'].lower() == 'help':
            bot_handler.send_reply(message, self.usage())
            return

        if message['content'].lower() == 'list-commands':
            response = '**Available Commands:** \n'
            for command, description in zip(self.commands, self.descriptions):
                response += ' - {} : {}\n'.format(command, description)
            bot_handler.send_reply(message, response)
            return

        print(message)
        response = self.generate_response(message['content'], message['sender_email'])
        self.bot_handler.send_reply(message, response)

    def generate_response(self, command, user):
        self.get_data()
        date = self.time['date']
        part_commands = command.split()

        try:

            if part_commands[0].lower() == 'make-id':
                return self.make_id(part_commands[1], date)

            if part_commands[0].lower() == 'cw-request':
                if part_commands[1] == '-id':
                    id = part_commands[2]
                    requests = part_commands[3:]
                else:
                    id = 'feelings-checkin-bot'
                    requests = part_commands[1:]
                return self.add_to_cw_reqs(id, requests, date)

            if part_commands[0].lower() == 'will-attend':
                return self.mark_attendance(part_commands[1], True, date)

            if part_commands[0].lower() == 'will-not-attend':
                return self.mark_attendance(part_commands[1], False, date)

            if part_commands[0].lower() == 'subscribe':
                if len(part_commands) == 1:
                    notifications = ['9', '2', '3']
                else:
                    notifications = part_commands[1:]
                return self.subscribe_user(notifications, user)

        except IndexError:
            return "Looks like you didn't give me enough arguments."

        else:
            pass

        return "I don't know what you mean. Type `list-commands` to find out about the words I understand."

    def make_id(self, id, date):
        if id == 'feelings-checkin-bot':
            return "You can't use that ID!"
        if id not in self.data['ids']:
            self.data['ids'][id] = {'last_accessed': date, 'requests': []}
            self.put_data(self.data)
            return 'Made ID `{}`'.format(id)
        else:
            return "I already know that ID."

    def add_to_cw_reqs(self, id, cw_reqs, date):
        if id not in self.data['ids']:
            return "I don't know {}".format(id)
        if id == 'feelings-checkin-bot':
            if not self.before_fc_on_Thursday:
                return TEXT_REPOSITORY['wrong_time']
            self.data['requests'].extend(cw_reqs)
            return_string = "The following topics were added to today's content warnings: {}".format(
                ', '.join(cw_reqs))
            print(self.data['requests'])
        else:
            cw_reqs = self.process_cw_reqs(cw_reqs)
            self.data['ids'][id]['requests'] = cw_reqs
            self.data['ids'][id]['last_accessed'] = date
            return_string = "I set the following topics as {}'s content warnings: {}".format(id, ', '.join(cw_reqs))
        self.put_data(self.data)
        return return_string

    def process_cw_reqs(self, raw_request):
        cws = []
        cw_req = []
        for i, word in enumerate(raw_request):
            if (i and word == '-r'):
                cw_string = ' '.join(cw_req)
                cws.append(cw_string)
                cw_req = []
            else:
                if word != '-r':
                    cw_req.append(word)
        cw_string = ' '.join(cw_req)
        cws.append(cw_string)
        return cws

    @property
    def before_fc_on_Thursday(self):
        if self.time['day'] == 3 and 8 < self.time['hour'] < 16:
            return True
        else:
            return False

    def mark_attendance(self, id, attending, date):
        if not self.before_fc_on_Thursday:
            return "You can only do that between 9am and 3pm on Thursdays."
        if id not in self.data['ids']:
            return "I don't know {}".format(id)
        self.data['ids'][id]['last_accessed'] = date
        if attending:
            self.data['attending'].append(id)
            return_string = 'attending'
        else:
            if id in self.data['attending']:
                self.data['attending'].remove(id)
            else:
                return "You weren't marked as attending to start with."
            return_string = 'not attending'
        self.put_data(self.data)
        return 'I marked {} as {}.'.format(id, return_string)

    def manage_subscriptions(self, notifications, user, sub=True):
        ret_str = ''
        changed_notifs = []
        for notification in notifications:
            if notification == '9':
                tod = 'am'
            else:
                tod = 'pm'
            if notification not in ['9', '2', '3']:
                return "{} isn't in the list of notifications I understand. Type `list-commands` for more information " \
                       "and try again!".format(notification)
            if sub:
                ret_string, changed_notifications = self.sub_proc(user, notification, tod, ret_str, changed_notifs)
            else:
                ret_string, changed_notifications = self.unsub_proc(user, notification, tod, ret_str, changed_notifs)
            self.put_data(self.data)
            ret_str += "I updated your subscription for these notifications: {}".format(' '.join(changed_notifications))

    def sub_proc(self, user, notification, tod, ret_str, changed_notifications):
        if user in self.data['subscriptions'][notification]:
            ret_str += "You're already subscribed to a notification for {}{}. ".format(notification, tod)
        else:
            changed_notifications.append(notification + tod)
            self.data['subscriptions'][notification].append(user)
        return ret_str, changed_notifications

    def unsub_proc(self, user, notification, tod, ret_str, changed_notifications):
        if user not in self.data['subscriptions'][notification]:
            ret_str += "You're not subscribed to a notification for {}{}. ".format(notification, tod)
        else:
            changed_notifications.append(user)
            self.data['subscriptions'][notification].remove(user)
        return ret_str, changed_notifications


handler_class = FeelingsCheckinBot
