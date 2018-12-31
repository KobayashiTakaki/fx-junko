import datetime
from time import sleep
import api.oanda_api as oanda_api
import api.twitter_api as twitter_api
import analizer

class Trader():
    def __init__(self):
        self.instrument = 'USD_JPY'
        self.params = {
            'granularity': 'S5',
            'count': 1
        }
        self.open_trade = None

    def main(self):
        while True:
            try:
                self.loop()
            except Exception as e:
                print(e)
                continue
            finally:
                sleep(10)

    def loop(self):
        self.open_trade = analizer.refresh_open_trade()
        if self.open_trade is not None:
            print('i have an open trade')

            if int(self.open_trade['initialUnits']) > 0:
                if analizer.is_macd_keep_going('down'):
                    self.exit()

            else:
                if analizer.is_macd_keep_going('up'):
                    self.exit()

            candle = oanda_api.get_candles(self.instrument, self.params, False)
            print(candle)
            if analizer.is_macd_crossed(candle)[0]:
                self.exit()

        else:
            #ポジションがない場合
            print('i dont have a open position')

            candle = oanda_api.get_candles(self.instrument, self.params, False)
            is_macd_crossed = analizer.is_macd_crossed(candle)

            if is_macd_crossed[0]:
                if analizer.is_entry_interval_enough():
                    if is_macd_crossed[1] == 1:
                        #上向きクロスだったら買いでエントリー
                        print('entry by buy')
                        self.entry(100)
                    else:
                        #下向きクロスだったら売りでエントリー
                        print('entry by sell')
                        self.entry(-100)
                else:
                    print('not enough')
            else:
                print('not crossed')

    def entry(self, amount):
        tz = datetime.timezone.utc
        now = datetime.datetime.now(tz)
        print(now)

        response = oanda_api.market_order(amount)
        if response.status == 201:
            print(amount)
            print('entry')
        else:
            raise Exception('entry failed')

        analizer.update_trade_data()
        self.open_trade = analizer.refresh_open_trade()

        print(self.open_trade)
        action = 'entry'
        feeling = 'neutral'
        start_side = 'buy' if int(self.open_trade['initialUnits']) > 0 else 'sell'
        start_price = format(self.open_trade['price'], '.3f')

        info = [
            "[Entry]",
            start_side + " " + self.instrument + "@" + start_price
        ]
        twitter_api.tweet(action, feeling, info)

        #エントリーしたら5分我慢
        sleep(300)

    def exit(self):
        tz = datetime.timezone.utc
        now = datetime.datetime.now(tz)
        print(now)

        print('close position')

        oanda_api.close_trade(self.open_trade['tradeId'])
        self.open_trade = analizer.refresh_open_trade()

        last_trade = oanda_api.get_trades('CLOSED', 1)[0]

        instrument = self.instrument.replace('_', '/')
        start_side = 'buy' if int(last_trade['initialUnits']) > 0 else 'sell'
        start_price = format(last_trade['price'], '.3f')
        end_side = 'buy' if start_side == 'sell' else 'buy'
        end_price = format(last_trade['averageClosePrice'], '.3f')
        pips = float(last_trade['realizedPL'])

        action = 'take_profit' if pips > 0 else 'losscut'
        feeling = 'positive' if pips > 0 else 'negative'
        info = [
            "[Trade Close]",
            start_side + " " + instrument + "@" + start_price,
            end_side + " " + instrument + "@" + end_price,
            format(pips, '.1f') + " pips"
        ]
        if pips > 0:
            action = 'take_profit'
            feeling = 'positive'
        else:
            action = 'losscut'
            feeling = 'negative'
        twitter_api.tweet(action, feeling, info)

        #イグジットしたら5分我慢
        sleep(300)

if __name__=='__main__':
    trader = Trader()
    trader.main()
