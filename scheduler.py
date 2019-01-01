import schedule
import time
import trader
import analyzer

trader = trader.Trader()

def trader_loop():
    trader.loop()


def analyzer_loop():
    analyzer.loop()

schedule.every(60).seconds.do(trader_loop)
schedule.every(120).seconds.do(analyzer_loop)

while True:
    try:
        schedule.run_pending()
        time.sleep(1)
    except Exception as e:
        print(e)
        continue
