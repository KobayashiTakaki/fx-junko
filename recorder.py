import datetime
import pandas as pd
import db.db  as db
import api.oanda_api as oanda_api
import util.price_util as price_util
import db.table_defs as table_defs

class RecorderError(Exception):
    pass

conn = db.conn
time_format = db.time_format

def add_trade_record(trade, table_name):
    create_trades_table(table_name)

    records = conn.execute('select * from ' + table_name + ' '
        + 'where tradeId = ' + trade['tradeId'] + ';').fetchall()
    if len(records) == 0:
        df = pd.DataFrame(trade, index=[1])
        df.to_sql(table_name, conn, if_exists="append", index=False)

def update_trade_data(table_name):
    create_trades_table(table_name)

    # tradesテーブルからOPENのtrade_idを取得
    open_ids = list(pd.read_sql_query(
        'select tradeId from ' + table_name + ' '
        + 'where state=\'OPEN\''
        ,conn
    )['tradeId'])

    # 1件も無ければreturn
    if len(open_ids) < 1:
        return

    # リストの中身を文字列型に変換(joinするため)
    open_ids = list(map(str, open_ids))

    # APIからopen_idのtradeを取得し、DataFrameに追加していく
    header = table_defs.get_columns('trades')
    fetched_trades = pd.DataFrame(columns=header)
    for id in open_ids:
        try:
            trade = oanda_api.get_trade(id)
        except Exception as e:
            raise RecorderError(e)

        s = pd.Series(trade)
        fetched_trades = fetched_trades.append(s,ignore_index=True)

    # open_idのレコードをtradesテーブルから削除
    conn.execute(
        'delete from '+ table_name + ' where tradeId in ('
        + ','.join(open_ids) + ');'
    )
    conn.commit()

    # APIから取得したデータをtradesテーブルに追加
    fetched_trades.to_sql(table_name, conn, if_exists="append", index=False)

def update_price_data(time_unit='M', time_count=5, count=60):
    table_name = 'prices_{0}{1}'.format(time_unit, time_count)
    create_prices_table(table_name)

    granularity = '{0}{1}'.format(time_unit, time_count)
    params = {
        'granularity': granularity,
        'count': count
    }

    # APIから取得してDFに入れる
    try:
        candles = pd.DataFrame(oanda_api.get_candles(params=params))\
            .sort_values('datetime')
    except Exception as e:
        raise RecorderError(e)

    # DBから最新のレコードを取得
    last_record = pd.read_sql_query(
            'select * from ' + table_name + ' '
            'order by datetime desc limit 1;'
            ,conn
        )

    # DBにレコードがある時
    if not (last_record.empty):
        # DBの最新レコードより古いcandleは削除
        while not (candles.empty):
            last_record_datetime = \
                datetime.datetime.strptime(last_record.iloc[0]['datetime'], time_format)
            candle_datetime = \
                datetime.datetime.strptime(candles.iloc[0]['datetime'], time_format)
            if candle_datetime <= last_record_datetime:
                # 一番最初の行を削除
                candles = candles.drop(candles.head(1).index, axis=0)
            else:
                break

    # DBに書き込み
    header = table_defs.get_columns('prices')
    candles.reindex(columns=header) \
        .to_sql(table_name, conn, if_exists="append", index=False)

    # macdを計算
    update_macd(table_name)
    # bollinger bandを計算
    update_bollinger(table_name)

def update_macd(table_name):
    max_records = 60
    df = pd.read_sql_query(
        'select * from ' + table_name + ' '
        + 'order by datetime desc '
        + 'limit ' + str(max_records) + ';'
        ,conn
    ).sort_values('datetime')
    df = price_util.calc_macd(df)

    header = table_defs.get_columns('prices')
    df.reindex(columns=header) \
        .to_sql(table_name, conn, if_exists="replace", index=False)

def update_bollinger(table_name):
    max_records = 60
    df = pd.read_sql_query(
        'select * from ' + table_name + ' '
        + 'order by datetime desc '
        + 'limit ' + str(max_records) + ';'
        ,conn
    ).sort_values('datetime')
    df = price_util.calc_bollinger(df)

    header = table_defs.get_columns('prices')
    df.reindex(columns=header) \
        .to_sql(table_name, conn, if_exists="replace", index=False)

def delete_old_trade_data():
    table_name = 'trades'
    keep_span = datetime.timedelta(weeks=1)
    keep_from = (datetime.datetime.now(datetime.timezone.utc)
        - keep_span).strftime(time_format)
    conn.execute(
        'delete from ' + table_name + ' '
        'where openTime < \'' + keep_from + '\';'
    )
    conn.commit()

def create_trades_table(table_name):
    sql = table_defs.get_create_table_sql('trades', table_name)
    conn.execute(sql)

def create_prices_table(table_name):
    sql = table_defs.get_create_table_sql('prices', table_name)
    conn.execute(sql)
