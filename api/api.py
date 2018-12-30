import configparser
import datetime
import v20

class Api():
    instrument = 'USD_JPY'
    candles_params = {
        'granularity': 'M5',
        'count': 60
    }

    def __init__(self):
        config = configparser.ConfigParser()
        config.read('conf.ini')

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
            'datetime':str(datetime.datetime.strptime(
                candle.time.split('.')[0],
                '%Y-%m-%dT%H:%M:%S')),
            'open': candle.mid.o,
            'high': candle.mid.h,
            'low':candle.mid.l,
            'close': candle.mid.c
        }

    def get_candles(self, instrument=instrument, params=candles_params, completed_only=True):
        candles = self.context.instrument.candles(instrument, **params).get("candles", 200)
        if completed_only:
            candles = [candle for candle in candles if candle.complete]

        return list(map(lambda candle: self.format_candle(candle), candles))

    def market_order(self, units):
        stop_loss = {
            'distance': 0.200
        }

        params = {
            'type': 'MARKET',
            'instrument': self.instrument,
            'units': units,
            'timeInForce': 'FOK',
            'stopLossOnFill': stop_loss
        }

        response = self.context.order.market(self.account_id, **params)
        return response

    def close_all_positions(self):
        params = {
            'shortUnits': 'ALL',
            'longUnits': 'ALL'
        }
        response = self.context.position.close(
            self.account_id, instrument=self.instrument, **params
        )
        return response
