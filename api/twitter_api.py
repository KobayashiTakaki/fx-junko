import configparser
from requests_oauthlib import OAuth1Session
import api.tweet_messages as tweet_messages

config = configparser.ConfigParser()
config.read('api/twitter_conf.ini')
CK = config['DEFAULT']['CONSUMER_KEY']
CS = config['DEFAULT']['CONSUMER_SECRET']
AT = config['DEFAULT']['ACCESS_TOKEN']
ATS = config['DEFAULT']['ACCESS_TOKEN_SECRET']

session = OAuth1Session(CK, CS, AT, ATS)


def tweet(action, feeling, info):
    url = 'https://api.twitter.com/1.1/statuses/update.json'
    message = tweet_messages.get_message(action)
    kaomoji = tweet_messages.get_kaomoji(feeling)
    tags = "#USDJPY #FX"
    content = (
        message + kaomoji + "\n"
        + "\n".join(info) + "\n"
        + tags
    )
    params = {
        'status': content
    }
    response = session.post(url, params=params)

    if response.status_code !== 200:
        raise Exception('tweet failed')
