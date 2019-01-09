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
        self.instrument = 'USD_JPY'
        self.is_scalping = False

    def loop(self):
        self.open_trade = analyzer.refresh_open_trade()

        if self.open_trade is not None:
            if self.is_scalping:
                self.deal_scalping_trade()

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

            self.shrink_stop_loss()

        else:
            #ポジションがない場合
            db.write_log('trader', 'i dont have a open position')

            self.is_scalping = False
            is_macd_crossed = analyzer.is_macd_crossed()
            if is_macd_crossed[0]:
                if analyzer.is_cross_interval_enough():
                    #上向きクロスだったら買いでエントリー
                    if is_macd_crossed[1] == 1:
                        if analyzer.market_trend() != -1:
                            db.write_log('trader', 'entry by buy')
                            self.entry('buy')
                    #下向きクロスだったら売りでエントリー
                    else:
                        if analyzer.market_trend() != 1:
                            db.write_log('trader', 'entry by sell')
                            self.entry('sell')
                else:
                    db.write_log('trader', 'not enough')
            else:
                db.write_log('trader', 'not crossed')

            if analyzer.is_macd_trending('up', 0.008, 2, True):
                db.write_log('trader', 'macd is up trend')
                db.write_log('trader', 'entry by buy')
                self.entry_scalping('buy')

            if analyzer.is_macd_trending('down', -0.008, 2, True):
                db.write_log('trader', 'macd is down trend')
                db.write_log('trader', 'entry by sell')
                self.entry_scalping('sell')

    def entry(self, side):
        amount = self.entry_amount
        minus = -1 if side == 'sell' else 1
        units = minus*amount
        stop_loss = {
            'distance': str(0.090)
        }
        trailing_stop_loss = {
            'distance': str(0.100)
        }

        params = {
            'type': 'MARKET',
            'instrument': self.instrument,
            'units': str(units),
            'timeInForce': 'FOK',
            'stopLossOnFill': stop_loss,
            'trailingStopLossOnFill': trailing_stop_loss
        }

        response = oanda_api.market_order(params)
        if response.status == 201:
            db.write_log('trader', 'entry. amount: ' + str(units))
        else:
            raise Exception('entry failed')

        self.open_trade = analyzer.refresh_open_trade()
        db.write_log('trader', 'open_trade: ' + str(self.open_trade))

    def entry_scalping(self, side):
        amount = self.entry_amount
        minus = -1 if side == 'sell' else 1
        units = minus*amount
        stop_loss = {
            'distance': str(0.020)
        }
        params = {
            'type': 'MARKET',
            'instrument': self.instrument,
            'units': str(units),
            'timeInForce': 'FOK',
            'stopLossOnFill': stop_loss
        }
        res = oanda_api.market_order(params)
        if res.status == 201:
            db.write_log('trader', 'entried by scalping. amount: ' + str(units))
            self.is_scalping = True
        else:
            raise Exception('scalping entry failed')

    def exit(self):
        db.write_log('trader', 'close position')

        oanda_api.close_trade(self.open_trade['tradeId'])
        self.open_trade = analyzer.refresh_open_trade()

    def shrink_stop_loss(self):
        distance = 0.010

        tradeId = self.open_trade['tradeId']
        trade  = oanda_api.get_trade(tradeId)

        pips = float(trade['unrealizedPL']) / abs(trade['initialUnits']) * 100
        now = datetime.datetime.now(datetime.timezone.utc)
        open_time = datetime.datetime.strptime(trade['openTime'], self.time_format)
        enough_time = datetime.timedelta(minutes=20)

        if pips > 5 \
        or now - open_time > enough_time:
            params = {
                'stopLoss': {
                    'distance': str(distance)
                }
            }
            oanda_api.change_trade_order(tradeId, params)
            db.write_log('trader', 'shrinked stop loss')

    def deal_scalping_trade(self):
        tradeId = self.open_trade['tradeId']
        trade = oanda_api.get_trade(tradeId)
        if trade['unrealizedPL'] == '':
            raise Exception('changing stoploss failed')
        pips = float(trade['unrealizedPL']) / abs(trade['initialUnits']) * 100
        if pips > 10:
            self.exit()

        margin = 0.02
        stop_loss = {
            'distance': str(margin)
        }
        params = {
            'stopLoss': stop_loss
        }

        oanda_api.change_trade_order(tradeId, params)

if __name__=='__main__':
    trader = Trader()
    trader.loop()
