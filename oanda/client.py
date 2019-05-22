import configparser
import datetime
import v20
from . import formatter

class OandaApiError(Exception):
    pass

class ResponseNotOkError(OandaApiError):
    pass

class Client():
    def __init__(self):
        self.context = self.get_context()
        self.account_id = self.context.account.list().get('accounts', 200)[0].id

    def get_context(self):
        config = configparser.ConfigParser()
        config.read('api/oanda_conf.ini')
        hostname = config['DEMO']['HOSTNAME']
        port = int(config['DEMO']['PORT'])
        token = config['DEMO']['TOKEN']

        retry = 0
        context = None
        while context is None and retry < 3:
            try:
                context = v20.Context(
                            hostname,
                            port,
                            token=token
                        )
            except Exception:
                retry += 1
                continue
        if context is None:
            raise OandaApiError('getting context failed')

        return context

    def get_candles(self, completed_only=True, option_params={}):
        instrument = 'USD_JPY'
        params = {
            'granularity': 'M5',
            'count': 60
        }
        if option_params:
            params.update(option_params)

        response = self.context.instrument.candles(instrument, **params)
        if response.status != 200:
            raise ResponseNotOkError('get_candles failed')

        candles = response.get("candles", 200)
        if completed_only:
            candles = [candle for candle in candles if candle.complete]

        return formatter.format_candles(candles)

    def get_current_candle(self, option_params={}):
        instrument = 'USD_JPY'
        params = {
            'granularity': 'S5',
            'count': 1
        }
        if option_params:
            params.update(option_params)
        response = self.context.instrument.candles(instrument, **params)
        if response.status != 200:
            raise ResponseNotOkError('get_current_candle failed')
        candles = response.get("candles", 200)
        return formatter.format_candle(candles[0])

    def market_order(self, units, stop_loss_distance=0.100):
        instrument = 'USD_JPY'
        stop_loss = {
            'distance': str(stop_loss_distance)
        }
        params = {
            'type': 'MARKET',
            'instrument': instrument,
            'units': str(units),
            'timeInForce': 'FOK',
            'stopLossOnFill': stop_loss
        }
        response = self.context.order.market(self.account_id, **params)
        if response.status != 201:
            raise ResponseNotOkError('market_order failed')

    def get_trade(self, trade_id):
        response = self.context.trade.get(self.account_id, str(trade_id))
        if response.status == 404:
            return None
        if response.status != 200:
            raise ResponseNotOkError('get_trade failed')
        trade = response.get('trade', 200)
        return formatter.format_trade(trade)

    def get_open_trade(self):
        response = self.context.trade.list_open(self.account_id)
        if response.status != 200:
            raise ResponseNotOkError('get_open_trade failed')
        trades = response.get('trades', 200)
        if len(trades) == 0:
            return None
        elif len(trades) == 1:
            return formatter.format_trade(trades[0])
        elif len(trades) > 1:
            return self.last_trade(trades)

    def last_trade(self, trades):
        # idを取得してsort
        ids = sorted([trade.id for trade in trades])
        for i in range(0, len(ids)-1):
            # 複数tradeがあったら最新のtradeだけ残して全部クローズする
            self.close_trade(ids[i])
        # idsの一番最後に一致するtradeを返す
        last_trade = [trade for trade in trades if trade.id == ids[-1]][0]
        return formatter.format_trade(last_trade)

    def close_trade(self, trade_id):
        response = self.context.trade.close(self.account_id, str(trade_id))
        if response.status == 404:
            return None
        if response.status != 200:
            raise ResponseNotOkError('close_trade failed')

    def is_market_open(self):
        params = {
            'granularity': 'S5',
            'count': 1
        }
        try:
            candle = self.get_candles(False)[0]
        except Exception as e:
            raise OandaApiError(e)

        now = datetime.datetime.now(datetime.timezone.utc)
        candle_time = datetime.datetime.strptime(
            candle['datetime'],
            '%Y-%m-%d %H:%M:%S%z'
        )

        if now - candle_time > datetime.timedelta(minutes=30):
            return False
        else:
            return True
