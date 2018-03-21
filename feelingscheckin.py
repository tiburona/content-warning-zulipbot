import datetime
from typing import Any
import pytz
import time
import json

RC_TIMEZONE = pytz.timezone('US/Eastern')


# todo: check if there's something special you have to do to at currently @ RC


class FeelingsCheckinBot(object):
    def usage(self):
        return '''
        I am the Feelings Checkin bot.  I remind everyone about Feelings Checkin and collect requests for 
        content warnings. There are two ways to request content warnings. You can submit topics between 9am and 3pm 
        on Thursday for that day's Feelings Checkin, or, any day of the week, you can associate a pseudonymous ID with a 
        content warning request, and mark that ID as attending between 9am and 3pm on Thursday.  Use `list-commands` to 
        show a list of available commands.
        '''

    def initialize(self, bot_handler: Any) -> None:
        self.bot_handler = bot_handler

        initialized_data = json.dumps({'attending': [], 'requests': [], 'ids': {}})

        self.bot_handler.storage.put('cw', initialized_data)

        self.commands = ['help',
                         'list-commands',
                         'make-id <id>'
                         'cw-request [options] <topic1> [<topic2> ...]\n\toptions: -id <id>',
                         'will-attend <id>',
                         'will-not-attend <id>']

        self.descriptions = ['Display bot info', 'Display the list of available commands', 'Make a new ID',
                             'Request content warnings (if called with the -id option, will overwrite previous requests '
                             'for that id)', 'Mark an ID as attending', 'Mark an ID as not attending']
        self.main()

    def get_data(self):
        return json.loads(self.bot_handler.storage.get('cw'))

    def put_data(self, cw_data):
        self.bot_handler.storage.put('cw', json.dumps(cw_data))

    def main(self):
        while True:
            self.check_time()
            time.sleep(30)

    @property
    def time(self):
        current_time = datetime.datetime.now(pytz.utc)
        localized_current_time = current_time.astimezone(RC_TIMEZONE)
        current_hour = localized_current_time.hour
        current_day = localized_current_time.weekday()
        return current_time, current_day, current_hour

    def check_time(self):
        current_time, current_day, current_hour = self.time
        if current_day == 3:
            if current_hour == 9 and (current_time - self.thurs_am_msg_sent).day > 1:
                self.initialize_thursday(current_time)
            if current_hour == 14 and (current_time - self.one_hour_msg_sent).day > 1:
                self.send_one_hour_notice(current_time)
            if current_hour == 15 and (current_time - self.fc_starting_msg_sent).day > 1:
                self.send_fc_starting_message(current_time)

    def initialize_thursday(self, time):
        cw_data = self.get_data()
        cw_data['attending'] = []
        cw_data['requests'] = []
        cw_data = self.clean_old_ids(cw_data, time)
        self.put_data(cw_data)
        content = "Happy Thursday! Feelings Checkin will take place at 3pm in Babbage. If you plan to attend and would " \
                  "like to request a content warning for a particular topic, I am the bot for you.  Send me a message " \
                  "with the word 'help' to hear about the things I can do."
        self.send_message_to_stream(content)
        self.thurs_am_msg_sent = time

    def clean_old_ids(self, cw_data, current_time):
        for id in cw_data['ids']:
            if (current_time - cw_data['ids'][id]['last_accessed']).month > 6:
                del cw_data['ids'][id]
        return cw_data

    def send_one_hour_notice(self, time):
        content = "@Currently at RC Feelings checking starts in an hour."
        self.send_message_to_stream(content)
        self.one_hour_msg_sent = time

    def send_fc_starting_message(self, time):
        content = "Feelings checkin is starting. These were the topics for which attendees requested content warnings."
        cw_data = self.get_data()
        for id in cw_data['attending']:
            cw_data['requests'].extend(cw_data['ids'][id]['requests'])

        for topic in cw_data['requests']:
            content += "\n{}".format(topic)
        self.send_message_to_stream(content)
        self.fc_starting_msg_sent = time

    def send_message_to_stream(self, content):
        self.bot_handler.send_message({
            "type": "stream",
            "to": '455 Broadway',
            "subject": "Feelings Checkin",
            "content": content
        })

    def handle_message(self, message: Any, bot_handler: Any) -> None:
        message['content'] = message['content'].strip()

        if message['content'] == '':
            bot_handler.send_reply(message, 'No command specified')
            return

        if message['content'].lower() == 'help':
            bot_handler.send_reply(message, self.usage())
            return

        if message['content'].lower() == 'list-commands':
            response = '**Available Commands:** \n'
            for command, description in zip(self.commands, self.descriptions):
                response += ' - {} : {}\n'.format(command, description)
            bot_handler.send_reply(message, response)
            return

        response = self.generate_response(message['content'])
        self.bot_handler.send_reply(message, response)


    def generate_response(self, command: str) -> str:

        part_commands = command.split()

        try:

            if part_commands[0].lower() == 'make-id':
                return self.make_id(part_commands[1])

            if part_commands[0].lower() == 'cw-request':
                if part_commands[1] == '-id':
                    id = part_commands[2]
                    requests = part_commands[3:]
                else:
                    id = 'feelings-checkin-bot'
                    requests = part_commands[2:]
                return self.add_to_todays_cws(id, requests, self.time[0])

            if part_commands[0].lower() == 'will-attend':
                return self.mark_attendance(part_commands[1], True, self.time[0])

            if part_commands[0].lower() == 'will-not-attend':
                return self.mark_attendance(part_commands[1], False, self.time[0])

        except IndexError:
            return "Looks like you didn't give me enough arguments."

    def make_id(self, id, time):
        cw_reqs = self.get_data()
        if id == 'feelings-checkin-bot':
            return "You can't use that ID!"
        if id not in cw_reqs['ids']:
            cw_reqs['ids'][id] = {'last_accessed': time, 'requests': []}
            self.put_data(cw_reqs)
            return 'made id ' + id
        else:
            return "I already know that ID."

    def add_to_cw_reqs(self, id, cw_reqs, time):
        cw_data = self.get_data
        if id == 'feelings-checkin-bot':
            cw_data['requests'].extend(cw_reqs)
            return_string = "The following topics were added to today's content warnings: {}".format(
                [' '.join(cw_reqs)])
        else:
            cw_data['ids'][id]['requests'] = cw_reqs
            cw_data['ids'][id]['last_accessed'] = time
            return_string = "I set the following topics as {}'s content warnings: {}".format(id, [' '.join(cw_reqs)])
        self.put_data(cw_data)
        return return_string


    def mark_attendance(self, id, attending, time):
        cw_data = self.get_data
        if id not in cw_data['ids']:
            return "I don't know {}".format(id)
        cw_data['ids'][id]['last_accessed'] = time
        if attending:
            cw_data['attending'].append(id)
            return_string = 'attending'
        else:
            try:
                cw_data['attending'].remove(id)
            except:
                pass
            return_string = 'not attending'
        self.put_data(cw_data)
        return 'I marked {} as {}.'.format(return_string)


handler_class = FeelingsCheckinBot
