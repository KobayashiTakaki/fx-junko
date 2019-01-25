import datetime
from time import sleep
import pandas as pd
import numpy as np
import db.db  as db
import api.oanda_api as oanda_api
import util.price_util as price_util

conn = db.conn
db_time_format = db.time_format

def is_macd_crossed(time_unit='M', time_count=5, within=1):
    table_name = 'prices_{0}{1}'.format(time_unit, time_count)

    # 最新のpriceをwithin+1件取得(datetimeの降順)
    df = pd.read_sql_query(
        'select * from ' + table_name + ' '
        + 'order by datetime desc limit ' + str(within+1) + ';'
        , conn)

    # 最新のレコードのdatetimeが古くないか確認
    time_now = datetime.datetime.now(datetime.timezone.utc)
    time_last_price = datetime.datetime.strptime(df.iloc[0]['datetime'], db_time_format)
    max_time = datetime.timedelta(minutes=minutes*5)

    if time_now - time_last_price > max_time:
        raise Exception('is_macd_crossed: price data too old for is_macd_crossed.')

    # withinの件数、クロスを判定
    for i in range(0, within):
        price_newer = df.iloc[i]
        price_older = df.iloc[i+1]
        #シグナルを上向きにクロス
        if price_older['macd_direction'] < price_newer['macd_direction']:
            return True, 1

        #シグナルを下向きにクロス
        elif price_older['macd_direction'] > price_newer['macd_direction']:
            return True, -1

    return False, 0

def is_candle_over_bollinger(time_unit='M', time_count=5):
    table_name = 'prices_{0}{1}'.format(time_unit, time_count)

    # 最新のレコードを1件取得
    df = pd.read_sql_query(
        'select * from ' + table_name + ' '
        + 'order by datetime desc limit 1;'
        , conn)

    # 最新のレコードのdatetimeが古くないか確認
    time_now = datetime.datetime.now(datetime.timezone.utc)
    time_last_price = datetime.datetime.strptime(df.iloc[0]['datetime'], db_time_format)
    max_time = datetime.timedelta(minutes=minutes*5)

    if time_now - time_last_price > max_time:
        raise Exception('is_candle_over_bollinger: price data too old for is_candle_over_bollinger.')

    # candleの終値がbollinger bandを超えているか判定
    if df.iloc[0]['close'] > df.iloc[0]['boll_upper']:
        # 終値がbollinger bandの上側を超えた
        return True, 1
    elif df.iloc[0]['close'] < df.iloc[0]['boll_lower']:
        # 終値がbollinger bandの下側を下回った
        return True, -1

    return False, 0

def is_candle_over_middle(time_unit='M', time_count=5, toward):
    table_name = 'prices_{0}{1}'.format(time_unit, time_count)

    # 最新のレコードを1件取得
    df = pd.read_sql_query(
        'select * from ' + table_name + ' '
        + 'order by datetime desc limit 1;'
        , conn)

    # 最新のレコードのdatetimeが古くないか確認
    time_now = datetime.datetime.now(datetime.timezone.utc)
    time_last_price = datetime.datetime.strptime(df.iloc[0]['datetime'], db_time_format)
    max_time = datetime.timedelta(minutes=minutes*5)

    if time_now - time_last_price > max_time:
        raise Exception('is_candle_over_middle: price data too old for is_candle_over_middle.')

    if toward == 'down':
        #中値を下回った
        if df.iloc[0]['close'] < df.iloc[0]['boll_mid']:
            return True
    else:
        #中値を超えた
        if df.iloc[0]['close'] > df.iloc[0]['boll_mid']:
            return True

    return False
