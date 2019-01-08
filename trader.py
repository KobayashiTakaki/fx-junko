import datetime
from time import sleep
import api.oanda_api as oanda_api
import api.twitter_api as twitter_api
import analyzer
import db.db as db

class Trader():
    def __init__(self):
        self.entry_amount = 10000
        self.open_trade = None
        self.time_format = db.time_format

    def loop(self):
        self.open_trade = analyzer.refresh_open_trade()
        if self.open_trade is not None:
            db.write_log('trader', 'i have an open trade')
            if analyzer.is_exit_interval_enough():
                if int(self.open_trade['initialUnits']) > 0:
                    if analyzer.is_macd_trending('down', -0.005):
                        self.exit()
                else:
                    if analyzer.is_macd_trending('up', 0.005):
                        self.exit()

                if analyzer.is_macd_crossed()[0]:
                    self.exit()
            else:
                db.write_log('trader', 'not enough time to exit')

            self.shrink_trailing_stop()

        else:
            #ポジションがない場合
            db.write_log('trader', 'i dont have a open position')

            is_macd_crossed = analyzer.is_macd_crossed()
            if is_macd_crossed[0]:
                if analyzer.is_cross_interval_enough():
                    #上向きクロスだったら買いでエントリー
                    if is_macd_crossed[1] == 1:
                        if analyzer.market_trend() != -1 \
                        and not analyzer.is_close_last_stop_loss('buy'):
                            db.write_log('trader', 'entry by buy')
                            self.entry(self.entry_amount)
                    #下向きクロスだったら売りでエントリー
                    else:
                        if analyzer.market_trend() != 1 \
                        and not analyzer.is_close_last_stop_loss('sell'):
                            db.write_log('trader', 'entry by sell')
                            self.entry(-self.entry_amount)
                else:
                    db.write_log('trader', 'not enough')
            else:
                db.write_log('trader', 'not crossed')

            if analyzer.is_macd_trending('up', 0.008, 2, True):
                db.write_log('trader', 'macd is up trend')
                db.write_log('trader', 'entry by buy')
                self.entry(self.entry_amount)

            if analyzer.is_macd_trending('down', -0.008, 2, True):
                db.write_log('trader', 'macd is down trend')
                db.write_log('trader', 'entry by sell')
                self.entry(-self.entry_amount)

    def entry(self, amount):
        response = oanda_api.market_order(amount)
        if response.status == 201:
            db.write_log('trader', 'entry. amount: ' + str(amount))
        else:
            raise Exception('entry failed')

        self.open_trade = analyzer.refresh_open_trade()
        db.write_log('trader', 'open_trade: ' + str(self.open_trade))

    def exit(self):
        db.write_log('trader', 'close position')

        oanda_api.close_trade(self.open_trade['tradeId'])
        self.open_trade = analyzer.refresh_open_trade()

    def shrink_trailing_stop(self):
        min_distance = 0.050
        if float(self.open_trade['trailingStopLossOrderDistance']) > min_distance:
            tradeId = self.open_trade['tradeId']
            trade  = oanda_api.get_trade(tradeId)

            pips = float(trade['unrealizedPL']) / abs(trade['initialUnits']) * 100
            now = datetime.datetime.now(datetime.timezone.utc)
            open_time = datetime.datetime.strptime(trade['openTime'], self.time_format)
            enough_time = datetime.timedelta(minutes=20)

            if pips > 5 \
            or now - open_time > enough_time:
                params = {
                    'trailingStopLoss': {
                        'distance': str(min_distance)
                    }
                }
                oanda_api.change_trade_order(tradeId, params)
                db.write_log('trader', 'shrinked trailing stop')

if __name__=='__main__':
    trader = Trader()
    trader.loop()
