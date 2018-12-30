import configparser
from requests_oauthlib import OAuth1Session
import api.tweet_messages as tweet_messages

class TwitterApi():
    def __init__(self):
        config = configparser.ConfigParser()
        config.read('api/twitter_conf.ini')
        CK = config['DEFAULT']['CONSUMER_KEY']
        CS = config['DEFAULT']['CONSUMER_SECRET']
        AT = config['DEFAULT']['ACCESS_TOKEN']
        ATS = config['DEFAULT']['ACCESS_TOKEN_SECRET']

        self.session = OAuth1Session(CK, CS, AT, ATS)

    def tweet(self, action, feeling, info):
        message = tweet_messages.get_message(action)
        kaomoji = tweet_messages.get_kaomoji(feeling)
        content = (
            message + kaomoji + "\n"
            + "[Entry]\n"
            + "sell USD/JPY@111.234\n"
            + "\n"
            + message + kaomoji + "\n"
            + "\n".join(info)
        )
        print(content)
