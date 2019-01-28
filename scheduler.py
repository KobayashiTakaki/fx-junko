import schedule
import time
import trader
import tweeter
import recorder
import db.db as db
import api.oanda_api as oanda_api
import logger

trader = trader.Trader()
logger = logger.get_logger('scheduler')

def trader_loop():
    trader.loop()

def update_trade_data():
    recorder.update_trade_data('trades')

def update_price_data():
    recorder.update_price_data()

def tweeter_loop():
    tweeter.trade_tweet()

def delete_old_records():
    recorder.delete_old_trade_data()
    tweeter.delete_old_records()

def sleep_trader():
    trader.is_sleeping = True

def wakeup_trader():
    trader.is_sleeping = False

def activate():
    # 最初にfxタグのスケジュールをクリアする
    schedule.clear('fx')
    if oanda_api.is_market_open():
        # fxタグのスケジュールを登録
        schedule.every(10).seconds.do(trader_loop).tag('fx')
        schedule.every(30).seconds.do(update_trade_data).tag('fx')
        schedule.every(20).seconds.do(update_price_data).tag('fx')
        schedule.every(60).seconds.do(tweeter_loop).tag('fx')

def deactivate():
    trader.exit()
    schedule.clear('fx')

def delete_old_log():
    db.delete_old_log()

def pl_tweet():
    tweeter.pl_tweet()

# このファイル最初の実行時にprice data更新とactivateを実行
recorder.update_price_data()
activate()

# 毎日04:00UTC(13:00JST)に古いレコード削除
schedule.every().day.at('04:00').do(delete_old_records)

# 日〜木23:00UTC(月〜金08:00JST)にactivateを実行
schedule.every().sunday.at('23:00').do(activate)
schedule.every().monday.at('23:00').do(activate)
schedule.every().tuesday.at('23:00').do(activate)
schedule.every().wednesday.at('23:00').do(activate)
schedule.every().thursday.at('23:00').do(activate)

# 毎日03:00-12:00UTC(12:00-19:00JST)はsleep
schedule.every().day.at('03:00').do(sleep_trader)
schedule.every().day.at('12:00').do(wakeup_trader)

# 金曜21:00UTC(土曜06:00JST)にdeactivateを実行
schedule.every().friday.at('21:00').do(deactivate)

# 土曜00:00UTC(土曜09:00JST)に損益ツイート
schedule.every().saturday.at('00:00').do(pl_tweet)

while True:
    try:
        schedule.run_pending()
        time.sleep(1)
    except Exception as e:
        logger.debug(str(e))
        schedule.clear('fx')
        recorder.update_price_data()
        activate()
        continue
