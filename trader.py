import datetime
from time import sleep
import api.oanda_api as oanda_api
import api.twitter_api as twitter_api
import analyzer
import db.db as db
import recorder

class Trader():
    def __init__(self):
        self.entry_amount = 10000
        self.open_trade = None
        self.time_format = db.time_format
        self.instrument = 'USD_JPY'
        self.entry_side = 'both'
        self.minutes = 5
        self.least_entry_slope = 0.002

    def loop(self):
        db.write_log('trader', 'entry_side: {}'.format(self.entry_side))
        self.open_trade = oanda_api.get_open_trade()

        if self.open_trade is not None:
            db.write_log('trader', 'i have an open trade')
            if analyzer.is_exit_interval_enough(self.open_trade, self.minutes):
                if int(self.open_trade['initialUnits']) > 0:
                    #macdが下向きになってたらexit
                    if analyzer.is_macd_trending('down', -0.002, 2, True, self.minutes):
                        self.exit()
                else:
                    #macdが上向きになってたらexit
                    if analyzer.is_macd_trending('up', 0.002, 2, True, self.minutes):
                        self.exit()

                #macdがシグナルと交差してたらexit
                if analyzer.is_macd_crossed(self.minutes)[0]:
                    self.exit()
            else:
                db.write_log('trader', 'not enough time to exit')
        else:
            #ポジションがない場合
            db.write_log('trader', 'i dont have an open trade')

            is_macd_crossed = analyzer.is_macd_crossed(self.minutes)
            if is_macd_crossed[0]:
                if analyzer.is_cross_interval_enough(self.minutes):
                    #上向きクロスだったら買いでエントリー
                    if is_macd_crossed[1] == 1:
                        if analyzer.market_trend() != -1\
                        and self.entry_side != 'sell'\
                        and analyzer.is_macd_trending('up', self.least_entry_slope, 3, True, self.minutes):
                            db.write_log('trader', 'entry by buy')
                            self.entry('buy')
                            return
                        else:
                            db.write_log('trader', 'too weak to buy')
                    #下向きクロスだったら売りでエントリー
                    else:
                        if analyzer.market_trend() != 1\
                        and self.entry_side != 'buy'\
                        and analyzer.is_macd_trending('down', -self.least_entry_slope, 3, True, self.minutes):
                            db.write_log('trader', 'entry by sell')
                            self.entry('sell')
                            return
                        else:
                            db.write_log('trader', 'too weak to sell')
                else:
                    db.write_log('trader', 'not enough cross interval')

            else:
                db.write_log('trader', 'not crossed')

    def entry(self, side):
        amount = self.entry_amount
        minus = -1 if side == 'sell' else 1
        units = minus*amount
        trailing_stop_loss = {
            'distance': str(0.150)
        }

        params = {
            'type': 'MARKET',
            'instrument': self.instrument,
            'units': str(units),
            'timeInForce': 'FOK',
            'trailingStopLossOnFill': trailing_stop_loss
        }

        response = oanda_api.market_order(params)

        self.open_trade = oanda_api.get_open_trade()
        #open_tradeがAPIから取れるまでちょっと待つ
        retry = 0
        while self.open_trade is None and retry < 3 :
            sleep(0.3)
            retry += 1

        recorder.add_trade_record(self.open_trade, 'trades')
        db.write_log('trader', 'open_trade: ' + str(self.open_trade))

    def exit(self):
        if self.open_trade is not None:
            db.write_log('trader', 'close position')
            oanda_api.close_trade(self.open_trade['tradeId'])
            self.open_trade = oanda_api.get_open_trade()

if __name__=='__main__':
    trader = Trader()
    trader.loop()
