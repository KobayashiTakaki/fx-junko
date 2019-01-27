import configparser
from requests_oauthlib import OAuth1Session
import db.db as db
import time
import logger

config = configparser.ConfigParser()
config.read('api/twitter_conf.ini')
CK = config['DEFAULT']['CONSUMER_KEY']
CS = config['DEFAULT']['CONSUMER_SECRET']
AT = config['DEFAULT']['ACCESS_TOKEN']
ATS = config['DEFAULT']['ACCESS_TOKEN_SECRET']
logger = logger.get_logger('tweeter')

def tweet(content):
    session = OAuth1Session(CK, CS, AT, ATS)
    url = 'https://api.twitter.com/1.1/statuses/update.json'
    params = {
        'status': content
    }
    logger.debug('content: ' + content)

    done = False
    retry = 0
    max_retry = 2
    while (not done) and (retry <= max_retry):
        try:
            response = session.post(url, params=params)
            if response.status_code != 200:
                raise Exception('tweet failed')
            else:
                logger.debug('tweet scceeded')
                done = True
        except Exception as e:
            logger.debug(str(e))
            # 高速連投を避けるためのsleep
            time.sleep(5)
            continue
        finally:
            retry +=1

    if not done:
        raise Exception('tweet failed')
