import datetime
import pandas as pd
import db.db  as db
import api.oanda_api as oanda_api
import util.price_util as price_util

conn = db.conn
time_format = db.time_format

trades_header = [
    'tradeId',
    'instrument',
    'price',
    'openTime',
    'state',
    'initialUnits',
    'realizedPL',
    'unrealizedPL',
    'averageClosePrice',
    'closeTime',
    'stopLossOrderState',
    'trailingStopLossOrderState',
    'trailingStopLossOrderDistance'
]

price_header = [
    'datetime',
    'open',
    'high',
    'low',
    'close',
    'macd',
    'macd_signal',
    'macd2',
    'macd_direction',
    'boll_upper',
    'boll_mid',
    'boll_lower'
]

def add_trade_record(trade, table_name):
    create_trades_table(table_name)

    records = conn.execute('select * from ' + table_name + ' '
        + 'where tradeId = ' + trade['tradeId'] + ';').fetchall()
    if len(records) == 0:
        df = pd.DataFrame(trade, index=[1])
        df.to_sql(table_name, conn, if_exists="append", index=False)

def update_trade_data(table_name):
    create_trades_table(table_name)

    #tradesテーブルからOPENのtrade_idを取得
    open_ids = list(pd.read_sql_query(
        'select tradeId from ' + table_name + ' '
        + 'where state=\'OPEN\''
        ,conn
    )['tradeId'])

    if len(open_ids) > 0:
        #リストの中身を文字列型に変換(joinするため)
        open_ids = list(map(str, open_ids))

        #APIからopen_idのtradeを取得し、DataFrameに追加していく
        fetched_trades = pd.DataFrame(columns=trades_header)
        for id in open_ids:
            trade = oanda_api.get_trade(id)
            s = pd.Series(trade)
            fetched_trades = fetched_trades.append(s,ignore_index=True)

        #open_idのレコードをtradesテーブルから削除
        conn.execute(
            'delete from '+ table_name + ' where tradeId in ('
            + ','.join(open_ids) + ');'
        )
        conn.commit()

        #APIから取得したデータをtradesテーブルに追加
        fetched_trades.to_sql(table_name, conn, if_exists="append", index=False)

def update_price_data(granularity='M5', count=60):
    table_name = 'prices_{}'.format(granularity)
    create_prices_table(table_name)

    granularity = '{}'.format(granularity)
    params = {
        'granularity': granularity,
        'count': count
    }

    #APIから取得してDFに入れる
    candles = pd.DataFrame(oanda_api.get_candles(params=params))\
        .sort_values('datetime')

    #DBから最新のレコードを取得
    last_record = pd.read_sql_query(
            'select * from ' + table_name + ' '
            'order by datetime desc limit 1;'
            ,conn
        )

    if not (last_record.empty):
        #DBの最新レコードより古いcandleは削除
        while not (candles.empty):
            last_record_datetime = \
                datetime.datetime.strptime(last_record.iloc[0]['datetime'], time_format)
            candle_datetime = \
                datetime.datetime.strptime(candles.iloc[0]['datetime'], time_format)
            if candle_datetime <= last_record_datetime:
                #一番最初の行を削除
                candles = candles.drop(candles.head(1).index, axis=0)
            else:
                break

    #DBに書き込み
    candles.reindex(columns=price_header) \
        .to_sql(table_name, conn, if_exists="append", index=False)

def update_macd(table_name):
    df = pd.read_sql_query(
        'select * from ' + table_name + ';'
        ,conn
    )
    df = price_util.calc_macd(df)
    df.reindex(columns=price_header) \
        .to_sql(table_name, conn, if_exists="replace", index=False)

def create_trades_table(table_name):
    conn.execute(
        'create table if not exists ' + table_name + '('
        + 'tradeId integer primary key, '
        + 'instrument text, '
        + 'price real, '
        + 'openTime text, '
        + 'state text, '
        + 'initialUnits real, '
        + 'realizedPL real, '
        + 'unrealizedPL real, '
        + 'averageClosePrice real, '
        + 'closeTime text,'
        + 'stopLossOrderState text, '
        + 'trailingStopLossOrderState  text, '
        + 'trailingStopLossOrderDistance real'
        + ');'
    )

def create_prices_table(table_name):
    conn.execute(
        'create table if not exists ' + table_name + '('
        + 'datetime text primary key, '
        + 'open real, '
        + 'high real, '
        + 'low real, '
        + 'close real, '
        + 'macd real, '
        + 'macd_signal real, '
        + 'macd2 real, '
        + 'macd_direction integer, '
        + 'boll_upper real,'
        + 'boll_mid real, '
        + 'boll_lower real '
        + ');'
    )
