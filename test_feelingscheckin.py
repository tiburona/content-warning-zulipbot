from zulip_bots.test_lib import BotTestCase

class FeelingsCheckinBotTest(BotTestCase):
    bot_name = "feelingscheckin"  # type: str

    def test_bot_responds_to_subscription(self) -> None:
        dialog = [
            ('subscribe', 'I updated your subscription for these notifications: 9am 2pm 3pm')
        ]

        self.bot_name = "feelingscheckin"

        self.verify_dialog(dialog)
