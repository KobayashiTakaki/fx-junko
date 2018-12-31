import schedule
import time
import trader
import analizer

trader = trader.Trader()

def trader_loop():
    trader.loop()


def analizer_loop():
    analizer.loop()

schedule.every(60).seconds.do(trader_loop)
schedule.every(120).seconds.do(analizer_loop)

while True:
    try:
        schedule.run_pending()
        time.sleep(1)
    except Exception as e:
        print(e)
        continue
