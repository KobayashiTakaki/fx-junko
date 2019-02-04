import datetime
from time import sleep
import api.oanda_api as oanda_api
import api.twitter_api as twitter_api
import util.trader_util as util
import db.db as db
import recorder
import logger
import traceback

class TraderError(Exception):
    pass

class Trader():
    def __init__(self):
        self.entry_amount = 10000
        self.open_trade = None
        self.time_format = db.time_format
        self.instrument = 'USD_JPY'
        self.time_unit = 'M'
        self.time_count = 5
        self.logger = logger.get_logger('trader')
        self.is_sleeping = False

    def loop(self):
        try:
            self.open_trade = oanda_api.get_open_trade()

            if self.open_trade is not None:
                if int(self.open_trade['initialUnits']) > 0:
                    # 現在値が中値を1/5以上下回った
                    if util.is_current_price_over_middle('down'):
                        self.logger.debug('[exit] current price over middle toward down')
                        self.exit()

                    # closeが中値を下回った
                    if util.is_candle_closed_over_middle('down'):
                        self.logger.debug('[exit] over middle toward down')
                        self.exit()

                    # 連続して陰線
                    if util.is_candle_keeping('down', 3):
                        self.logger.debug('[exit] candle continuously decreasing')
                        self.exit()

                else:
                    # 現在値が中値を1/5以上上回った
                    if util.is_current_price_over_middle('up'):
                        self.logger.debug('[exit] current price over middle toward up')
                        self.exit()

                    # closeが中値を上回った
                    if util.is_candle_closed_over_middle('up'):
                        self.logger.debug('[exit] over middle toward up')
                        self.exit()

                    # 連続して陽線
                    if util.is_candle_keeping('up', 3):
                        self.logger.debug('[exit] candle continuously increasing')
                        self.exit()

            else:
                # ポジションがない場合
                # bollinger bandの上を超えた
                if util.is_candle_over_bollinger('up', 1):
                    self.logger.debug('over upper bollinger')

                    is_macd_crossed = util.is_macd_crossed(8)

                    # macdが上向きにクロス
                    if is_macd_crossed[0] and is_macd_crossed[1] == 1:
                        # 逆向きのbollinger bandを超えていない
                        if not util.is_candle_over_bollinger('down', 14):
                            self.logger.debug('[entry] by buy')
                            self.entry('buy')
                            return
                        else:
                            self.logger.debug('recently overed opposite bollinger')
                    else:
                        self.logger.debug('macd not crossed recently')

                # bollinger bandの下を超えた
                elif util.is_candle_over_bollinger('down', 1):
                    self.logger.debug('over lower bollinger')

                    is_macd_crossed = util.is_macd_crossed(8)

                    # macdが下向きにクロス
                    if is_macd_crossed[0] and is_macd_crossed[1] == -1:
                        # 逆向きのbollinger bandを超えていない
                        if not util.is_candle_over_bollinger('up', 14):
                            self.logger.debug('[entry] by sell')
                            self.entry('sell')
                            return
                        else:
                            self.logger.debug('recently overed opposite bollinger')
                    else:
                        self.logger.debug('macd not crossed recently')

        except Exception as e:
            self.logger.debug(traceback.format_exc())
            raise TraderError(e)

    def entry(self, side):
        if self.is_sleeping:
            self.logger.debug('sleeping. not entry.')
            return

        amount = self.entry_amount
        minus = -1 if side == 'sell' else 1
        units = minus*amount
        stop_loss = {
            'distance': str(0.100)
        }

        params = {
            'type': 'MARKET',
            'instrument': self.instrument,
            'units': str(units),
            'timeInForce': 'FOK',
            'stopLossOnFill': stop_loss
        }

        try:
            response = oanda_api.market_order(params)

            self.open_trade = oanda_api.get_open_trade()
            # open_tradeがAPIから取れるまでちょっと待つ
            retry = 0
            while self.open_trade is None and retry < 3 :
                sleep(0.3)
                retry += 1

        except Exception as e:
            self.logger.debug(traceback.format_exc())
            raise TraderError(e)

        recorder.add_trade_record(self.open_trade, 'trades')
        self.logger.debug('open_trade: ' + str(self.open_trade))

    def exit(self):
        if self.open_trade is None:
            return

        self.logger.debug('close position')
        try:
            oanda_api.close_trade(self.open_trade['tradeId'])
            self.open_trade = oanda_api.get_open_trade()

        except Exception as e:
            self.logger.debug(traceback.format_exc())
            raise TraderError(e)

if __name__=='__main__':
    trader = Trader()
    trader.loop()
