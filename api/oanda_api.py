import configparser
import datetime
import v20

class OandaApi():
    instrument = 'USD_JPY'
    candles_params = {
        'granularity': 'M5',
        'count': 60
    }

    def __init__(self):
        config = configparser.ConfigParser()
        config.read('api/oanda_conf.ini')

        hostname = config['DEMO']['HOSTNAME']
        port = int(config['DEMO']['PORT'])
        token = config['DEMO']['TOKEN']

        self.context = v20.Context(
                    hostname,
                    port,
                    token=token
                )

        self.account_id = self.context.account.list().get('accounts', 200)[0].id

    @staticmethod
    def format_candle(candle):
        return {
            'datetime': str(datetime.datetime.strptime(
                candle.time.split('.')[0],
                '%Y-%m-%dT%H:%M:%S')),
            'open': candle.mid.o,
            'high': candle.mid.h,
            'low':candle.mid.l,
            'close': candle.mid.c
        }

    @staticmethod
    def format_trade(trade):
        return {
            'tradeId': trade.id,
            'instrument': trade.instrument,
            'price': trade.price,
            'openTime': trade.openTime,
            'state': trade.state,
            'initialUnits': trade.initialUnits,
            'realizedPL': trade.realizedPL,
            'unrealizedPL': trade.unrealizedPL,
            'averageClosePrice': trade.averageClosePrice,
            'closeTime': trade.closeTime
        }

    def get_candles(self, instrument=instrument, params=candles_params, completed_only=True):
        candles = self.context.instrument.candles(instrument, **params).get("candles", 200)
        if completed_only:
            candles = [candle for candle in candles if candle.complete]

        return list(map(lambda candle: self.format_candle(candle), candles))

    def market_order(self, units):
        stop_loss = {
            'distance': str(0.200)
        }

        params = {
            'type': 'MARKET',
            'instrument': self.instrument,
            'units': str(units),
            'timeInForce': 'FOK',
            'stopLossOnFill': stop_loss
        }

        response = self.context.order.market(self.account_id, **params)
        return response

    # def get_open_positions(self):
    #     response = self.context.position.list_open(self.account_id)
    #     return response.get('positions', 200)
    #
    # def get_last_closed_position(self):
    #     response = self.context.position.list(self.account_id)
    #     #positions = response.get('positions', 200)
    #     #positions = [position for position in positions if position.pl !== '']
    #     return response

    def get_trades(self, state, count):
        params = {
            'state': state,
            'instrument': self.instrument,
            'count': count
        }
        trades = self.context.trade.list(self.account_id, **params).get('trades', 200)

        return list(map(lambda trade: self.format_trade(trade), trades))

    def close_trade(self, trade_id):
        response = self.context.trade.close(self.account_id, str(trade_id))
        return response

    def close_all_position(self, side):
        params = {}
        if side == 'short':
            params = {
                'shortUnits': 'ALL'
            }
        if side == 'long':
            params = {
                'longUnits': 'ALL'
            }
        response = self.context.position.close(
            self.account_id, instrument=self.instrument, **params
        )
        return response
