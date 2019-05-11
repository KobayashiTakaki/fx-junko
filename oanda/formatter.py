import datetime

def format_candles(candles):
    return list(map(lambda candle: format_candle(candle), candles))

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

def format_trades(trades):
    return list(map(lambda trade: format_trade(trade), trades))

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
        'trailingStopLossOrderDistance': trailingStopLossOrderDistance
    }
