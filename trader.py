import datetime
from time import sleep
import api.oanda_api as oanda_api
import api.twitter_api as twitter_api
import util.trader_util as util
import db.db as db
import recorder
import logger

class Trader():
    def __init__(self):
        self.entry_amount = 10000
        self.open_trade = None
        self.time_format = db.time_format
        self.instrument = 'USD_JPY'
        self.time_unit = 'M'
        self.time_count = 5
        self.logger = logger.get_logger('trader')

    def loop(self):
        self.open_trade = oanda_api.get_open_trade()

        if self.open_trade is not None:
            self.logger.debug('i have an open trade')

            if int(self.open_trade['initialUnits']) > 0:
                #現在値が中値を1/5以上下回った
                if util.is_current_price_over_middle( \
                    time_unit=self.time_unit, time_count=self.time_count, \
                    toward='down'):
                    self.logger.debug('current price over middle toward down. exit.')
                    self.exit()

                # closeが中値を下回った
                if util.is_candle_closed_over_middle( \
                    time_unit=self.time_unit, time_count=self.time_count, \
                    toward='down'):
                    self.logger.debug('over middle toward down. exit.')
                    self.exit()
            else:
                #現在値が中値を1/5以上上回った
                if util.is_current_price_over_middle( \
                    time_unit=self.time_unit, time_count=self.time_count, \
                    toward='up'):
                    self.logger.debug('current price over middle toward up. exit.')
                    self.exit()

                # closeが中値を上回った
                if util.is_candle_closed_over_middle( \
                    time_unit=self.time_unit, time_count=self.time_count, \
                    toward='up'):
                    self.logger.debug('over middle toward up. exit.')
                    self.exit()

        else:
            #ポジションがない場合
            self.logger.debug('i dont have an open trade')
            # bollinger bandの上を超えた
            if util.is_candle_over_bollinger( \
                time_unit=self.time_unit, time_count=self.time_count, \
                within=1, toward='up'):
                self.logger.debug('over upper bollinger')

                is_macd_crossed = util.is_macd_crossed( \
                    time_unit=self.time_unit, time_count=self.time_count, \
                    within=8)

                # macdが上向きにクロス
                if is_macd_crossed[0] and is_macd_crossed[1] == 1:
                    #逆向きのbollinger bandを超えていない
                    if not util.is_candle_over_bollinger( \
                        time_unit=self.time_unit, time_count=self.time_count, \
                        within=14, toward='down'):
                        self.logger.debug('entry by buy')
                        self.entry('buy')
                        return
                    else:
                        self.logger.debug('recently overed against bollinger')
                else:
                    self.logger.debug('macd not crossed recently')

            # bollinger bandの下を超えた
            elif util.is_candle_over_bollinger( \
                time_unit=self.time_unit, time_count=self.time_count, \
                within=1, toward='down'):
                self.logger.debug('over lower bollinger')

                is_macd_crossed = util.is_macd_crossed( \
                    time_unit=self.time_unit, time_count=self.time_count, \
                    within=8)

                # macdが下向きにクロス
                if is_macd_crossed[0] and is_macd_crossed[1] == -1:
                    #逆向きのbollinger bandを超えていない
                    if not util.is_candle_over_bollinger( \
                        time_unit=self.time_unit, time_count=self.time_count, \
                        within=14, toward='up'):
                        self.logger.debug('entry by sell')
                        self.entry('sell')
                        return
                    else:
                        self.logger.debug('recently overed against bollinger')
                else:
                    self.logger.debug('macd not crossed recently')

    def entry(self, side):
        amount = self.entry_amount
        minus = -1 if side == 'sell' else 1
        units = minus*amount
        stop_loss = {
            'distance': str(0.080)
        }

        params = {
            'type': 'MARKET',
            'instrument': self.instrument,
            'units': str(units),
            'timeInForce': 'FOK',
            'stopLossOnFill': stop_loss
        }

        response = oanda_api.market_order(params)

        self.open_trade = oanda_api.get_open_trade()
        #open_tradeがAPIから取れるまでちょっと待つ
        retry = 0
        while self.open_trade is None and retry < 3 :
            sleep(0.3)
            retry += 1

        recorder.add_trade_record(self.open_trade, 'trades')
        self.logger.debug('open_trade: ' + str(self.open_trade))

    def exit(self):
        if self.open_trade is not None:
            self.logger.debug('close position')
            oanda_api.close_trade(self.open_trade['tradeId'])
            self.open_trade = oanda_api.get_open_trade()

if __name__=='__main__':
    trader = Trader()
    trader.loop()
