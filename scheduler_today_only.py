import schedule
import datetime
import time
import trader
import analyzer
import db.db as db

trader = trader.Trader()
start_time = (datetime.datetime.now(datetime.timezone.utc)
    + datetime.timedelta(minutes=1)).strftime('%H:%M')
is_active = True

def trader_loop():
    trader.loop()

def analyzer_loop():
    analyzer.loop()

def activate():
    schedule.clear(tag='fx')
    schedule.every(60).seconds.do(trader_loop).tag('fx')
    schedule.every(60).seconds.do(analyzer_loop).tag('fx')

def deactivate():
    schedule.clear()
    is_active = False

schedule.every().day.at(start_time).do(deactivate)
schedule.every().day.at('23:00').do(deactivate)

while is_active:
    try:
        schedule.run_pending()
        time.sleep(1)
    except Exception as e:
        db.write_log('exception', str(e))
        continue
