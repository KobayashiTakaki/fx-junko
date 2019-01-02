import datetime
from time import sleep
import api.oanda_api as oanda_api
import api.twitter_api as twitter_api
import analyzer
import db.db as db

class Trader():
    def __init__(self):
        self.instrument = 'USD_JPY'
        self.params = {
            'granularity': 'S5',
            'count': 1
        }
        self.open_trade = None

    def loop(self):
        self.open_trade = analyzer.refresh_open_trade()
        if self.open_trade is not None:
            db.write_log('trader', 'i have an open trade')
            if analyzer.is_exit_interval_enough():
                if int(self.open_trade['initialUnits']) > 0:
                    if analyzer.is_macd_trending('down'):
                        self.exit()
                else:
                    if analyzer.is_macd_trending('up'):
                        self.exit()

                if analyzer.is_macd_crossed()[0]:
                    self.exit()
            else:
                db.write_log('trader', 'not enough time to exit')

        else:
            #ポジションがない場合
            db.write_log('trader', 'i dont have a open position')

            is_macd_crossed = analyzer.is_macd_crossed()
            if is_macd_crossed[0]:
                if analyzer.is_entry_interval_enough():
                    if is_macd_crossed[1] == 1:
                        if analyzer.market_trend() != -1:
                            #上向きクロスだったら買いでエントリー
                            db.write_log('trader', 'entry by buy')
                            self.entry(100)
                    else:
                        if analyzer.market_trend() != 1:
                            #下向きクロスだったら売りでエントリー
                            db.write_log('trader', 'entry by sell')
                            self.entry(-100)
                else:
                    db.write_log('trader', 'not enough')
            else:
                db.write_log('trader', 'not crossed')

        analyzer.is_macd_trending('up')

    def entry(self, amount):
        response = oanda_api.market_order(amount)
        if response.status == 201:
            db.write_log('trader', 'entry. amount: ' + str(amount))
        else:
            raise Exception('entry failed')

        analyzer.update_trade_data()
        self.open_trade = analyzer.refresh_open_trade()

        db.write_log('trader', 'open_trade' + str(self.open_trade))
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
        db.write_log('trader', 'close position')

        oanda_api.close_trade(self.open_trade['tradeId'])
        self.open_trade = analyzer.refresh_open_trade()

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

if __name__=='__main__':
    trader = Trader()
    trader.loop()
