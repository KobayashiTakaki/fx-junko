import datetime
from time import sleep
import pandas as pd
import numpy as np
import db.db  as db
import api.oanda_api as oanda_api
import util.price_util as price_util

conn = db.conn
db_time_format = db.time_format

def is_macd_crossed(within=1, time_unit='M', time_count=5):
    table_name = 'prices_{0}{1}'.format(time_unit, time_count)

    # 最新のpriceをwithin+1件取得(datetimeの降順)
    df = pd.read_sql_query(
        'select * from ' + table_name + ' '
        + 'order by datetime desc limit ' + str(within+1) + ';'
        , conn)

    # 最新のレコードのdatetimeが古くないか確認
    time_now = datetime.datetime.now(datetime.timezone.utc)
    time_last_price = datetime.datetime.strptime(df.iloc[0]['datetime'], db_time_format)
    time_unit_full = 'minutes'
    time_args = {
        time_unit_full: time_count*5
    }
    max_time = datetime.timedelta(**time_args)

    if time_now - time_last_price > max_time:
        raise Exception('is_macd_crossed: price data too old for is_macd_crossed.')

    offset = 0.001
    # withinの件数、クロスを判定
    for i in range(0, within):
        price_newer = df.iloc[i]
        price_older = df.iloc[i+1]
        # シグナルを上向きにクロス
        # macd2がマイナス→プラス
        if price_older['macd2'] - offset < 0 \
        and price_newer['macd2'] > 0:
            return True, 1

        # シグナルを下向きにクロス
        # macd2がプラス→マイナス
        if price_older['macd2'] + offset > 0 \
        and price_newer['macd2'] < 0:
            return True, -1

    return False, 0

def is_candle_over_bollinger(toward='up', within=1, time_unit='M', time_count=5):
    table_name = 'prices_{0}{1}'.format(time_unit, time_count)

    # 最新のpriceをwithin+1件取得(datetimeの降順)
    df = pd.read_sql_query(
        'select * from ' + table_name + ' '
        + 'order by datetime desc limit '
        + str(within) + ';'
        , conn)

    # 最新のレコードのdatetimeが古くないか確認
    time_now = datetime.datetime.now(datetime.timezone.utc)
    time_last_price = datetime.datetime.strptime(df.iloc[0]['datetime'], db_time_format)
    time_unit_full = 'minutes'
    time_args = {
        time_unit_full: time_count*5
    }
    max_time = datetime.timedelta(**time_args)

    if time_now - time_last_price > max_time:
        raise Exception('is_candle_over_bollinger: price data too old for is_candle_over_bollinger.')

    for i in range(0, within):
        # bollinger bandの幅が十分でなければチェックしない
        if not df.iloc[i]['boll_upper'] \
            - df.iloc[i]['boll_lower'] > 0.05:
            continue

        if toward == 'down':
            # 終値がbollinger bandの下側を下回った
            if df.iloc[i]['close'] < df.iloc[i]['boll_lower']:
                return True

        else:
            # 終値がbollinger bandの上側を超えた
            if  df.iloc[i]['close'] > df.iloc[i]['boll_upper']:
                return True

    return False

def is_candle_closed_over_middle(toward='up', time_unit='M', time_count=5):
    table_name = 'prices_{0}{1}'.format(time_unit, time_count)

    # 最新のレコードを1件取得
    df = pd.read_sql_query(
        'select * from ' + table_name + ' '
        + 'order by datetime desc limit 1;'
        , conn)

    # 最新のレコードのdatetimeが古くないか確認
    time_now = datetime.datetime.now(datetime.timezone.utc)
    time_last_price = datetime.datetime.strptime(df.iloc[0]['datetime'], db_time_format)
    time_unit_full = 'minutes'
    time_args = {
        time_unit_full: time_count*5
    }
    max_time = datetime.timedelta(**time_args)

    if time_now - time_last_price > max_time:
        raise Exception('is_candle_over_middle: price data too old for is_candle_over_middle.')

    if toward == 'down':
        # 中値を下回った
        if df.iloc[0]['close'] < df.iloc[0]['boll_mid']:
            return True
    else:
        # 中値を超えた
        if df.iloc[0]['close'] > df.iloc[0]['boll_mid']:
            return True

    return False

def is_current_price_over_middle(toward='up', time_unit='M', time_count=5):
    table_name = 'prices_{0}{1}'.format(time_unit, time_count)
    # 最新のレコードを1件取得
    last_candle = pd.read_sql_query(
        'select * from ' + table_name + ' '
        + 'order by datetime desc limit 1;'
        , conn)

    # 最新のレコードのdatetimeが古くないか確認
    time_now = datetime.datetime.now(datetime.timezone.utc)
    time_last_price = datetime.datetime.strptime(last_candle.iloc[0]['datetime'], db_time_format)
    time_unit_full = 'minutes'
    time_args = {
        time_unit_full: time_count*5
    }
    max_time = datetime.timedelta(**time_args)
    if time_now - time_last_price > max_time:
        raise Exception('is_candle_over_middle: price data too old for is_candle_over_middle.')

    # APIからpriceを取得
    current_candle = oanda_api.get_current_candle()

    if toward == 'down':
        # bollinger band の中値と下バンドの間1/5
        border = last_candle.iloc[0]['boll_mid'] \
            - abs(last_candle.iloc[0]['boll_mid']-last_candle.iloc[0]['boll_lower'])/5
        # borderを下回った
        if current_candle[0]['close'] < border:
            return True
    else:
        # bollinger band の中値と上バンドの間1/5
        border = last_candle.iloc[0]['boll_mid'] \
            + abs(last_candle.iloc[0]['boll_mid']-last_candle.iloc[0]['boll_upper'])/5
        # borderを上回った
        if current_candle[0]['close'] > border:
            return True

    return False

def is_candle_keeping(direction='up', count=3, time_unit='M', time_count=5):
    table_name = 'prices_{0}{1}'.format(time_unit, time_count)
    candles = pd.read_sql_query(
        'select * from ' + table_name + ' '
        + 'order by datetime desc limit '
        + str(count) + ';'
        , conn)

    offset = 0.001
    for i, row in candles.iterrows():
        if direction == 'up':
            # closeがopenより高いことを想定
            # close - open が0以下になってたらFalse
            if (row['close'] - offset - row['open'] <= 0):
                return False
        else:
            # openがcloseより高いことを想定
            # open - close が0以下になってたらFalse
            if (row['open'] - offset - row['close'] <= 0):
                return False

    return True
