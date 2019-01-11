import configparser
import datetime
import v20

config = configparser.ConfigParser()
config.read('api/oanda_conf.ini')

hostname = config['DEMO']['HOSTNAME']
port = int(config['DEMO']['PORT'])
token = config['DEMO']['TOKEN']

context = v20.Context(
            hostname,
            port,
            token=token
        )
account_id = context.account.list().get('accounts', 200)[0].id

instrument = 'USD_JPY'
candles_params = {
    'granularity': 'M5',
    'count': 60
}

def format_candle(candle):
    return {
        'datetime': str(datetime.datetime.strptime(
            candle.time.split('.')[0] + '+00:00',
            '%Y-%m-%dT%H:%M:%S%z')),
        'open': candle.mid.o,
        'high': candle.mid.h,
        'low':candle.mid.l,
        'close': candle.mid.c
    }

def format_trade(trade):
    tradeId = trade.id
    instrument = trade.instrument
    price = trade.price
    openTime = str(datetime.datetime.strptime(
        trade.openTime.split('.')[0] + '+00:00',
        '%Y-%m-%dT%H:%M:%S%z'))
    state = trade.state
    initialUnits = trade.initialUnits
    realizedPL = '' if trade.realizedPL is None else trade.realizedPL
    unrealizedPL = '' if trade.unrealizedPL is None else trade.unrealizedPL
    averageClosePrice = '' if trade.averageClosePrice is None else trade.averageClosePrice
    closeTime = '' if trade.closeTime is None \
        else str(datetime.datetime.strptime(
            trade.closeTime.split('.')[0] + '+00:00',
            '%Y-%m-%dT%H:%M:%S%z'))
    stopLossOrderState = '' if trade.stopLossOrder is None\
        else trade.stopLossOrder.state
    trailingStopLossOrderState = '' if trade.trailingStopLossOrder is None\
        else trade.trailingStopLossOrder.state
    trailingStopLossOrderDistance = '' if trade.trailingStopLossOrder is None\
        else trade.trailingStopLossOrder.distance
    is_scal = ''

    return {
        'tradeId': tradeId,
        'instrument': instrument,
        'price': price,
        'openTime': openTime,
        'state': state,
        'initialUnits': initialUnits,
        'realizedPL': realizedPL,
        'unrealizedPL': unrealizedPL,
        'averageClosePrice': averageClosePrice,
        'closeTime': closeTime,
        'stopLossOrderState': stopLossOrderState,
        'trailingStopLossOrderState': trailingStopLossOrderState,
        'trailingStopLossOrderDistance': trailingStopLossOrderDistance,
        'is_scal': is_scal
    }

def get_candles(instrument=instrument, params=candles_params, completed_only=True):
    candles = context.instrument.candles(instrument, **params).get("candles", 200)
    if completed_only:
        candles = [candle for candle in candles if candle.complete]

    return list(map(lambda candle: format_candle(candle), candles))

def market_order(params):
    response = context.order.market(account_id, **params)
    if response.status == 201:
        db.write_log('oanda_api', 'entry succeeded.')
        return response
    else:
        raise Exception('oanda_api: entry failed')

def get_trades(state, count):
    params = {
        'state': state,
        'instrument': instrument,
        'count': count
    }
    trades = context.trade.list(account_id, **params).get('trades', 200)

    return list(map(lambda trade: format_trade(trade), trades))

def get_trade(trade_id):
    trade = context.trade.get(account_id, str(trade_id)).get('trade', 200)
    return format_trade(trade)

def get_open_trade():
    trades = context.trade.list_open(account_id).get('trades', 200)
    if len(trades) == 0:
        return None
    elif len(trades) > 1:
        #idを取得してsort
        ids = sorted([trade.id for trade in trades])
        print(ids)
        for i in range(0, len(ids)-1):
            #複数tradeがあったら最新のtradeだけ残して全部クローズする
            close_trade(ids[i])
        #idsの一番最後に一致するtradeを返す
        last_trade = [trade for trade in trades if trade.id == ids[-1]][0]
        return format_trade(last_trade)

    return format_trade(trades[0])

def change_trade_order(trade_id, params):
    response = context.trade.set_dependent_orders(account_id, trade_id, **params)
    return response

def close_trade(trade_id):
    response = context.trade.close(account_id, str(trade_id))
    return response

def close_all_position(side):
    params = {}
    if side == 'short':
        params = {
            'shortUnits': 'ALL'
        }
    if side == 'long':
        params = {
            'longUnits': 'ALL'
        }
    response = context.position.close(
        account_id, instrument=instrument, **params
    )
    return response

def is_market_open():
    instrument = 'USD_JPY'
    candles_params = {
        'granularity': 'S5',
        'count': 1
    }
    candle = get_candles(instrument, candles_params, False)[0]

    now = datetime.datetime.now(datetime.timezone.utc)
    candle_time = datetime.datetime.strptime(
        candle['datetime'],
        '%Y-%m-%d %H:%M:%S%z'
    )

    if now - candle_time > datetime.timedelta(minutes=30):
        return False
    else:
        return True
