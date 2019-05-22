import oanda.client
import db.sqlite
import db.table_defs
import pandas as pd
import datetime

class Prices():
    def __init__(self):
        self.oanda_client = oanda.client.Client()
        self.conn = db.sqlite.Sqlite().get_conn()
        self.time_format = '%Y-%m-%d %H:%M:%S%z'

    def update_price_data(self, time_unit='M', time_count=5, count=60):
        table_name = 'prices_{0}{1}'.format(time_unit, time_count)
        self.create_prices_table(table_name)

        granularity = '{0}{1}'.format(time_unit, time_count)
        params = {
            'granularity': granularity,
            'count': count
        }

        # APIから取得してDFに入れる
        try:
            candles = pd.DataFrame(self.oanda_client.get_candles(option_params=params))\
                .sort_values('datetime')
        except Exception as e:
            raise PricesError('getting candles by api failed.')

        # DBから最新のレコードを取得
        last_record = pd.read_sql_query(
                'select * from ' + table_name + ' '
                'order by datetime desc limit 1;'
                ,self.conn
            )

        # DBにレコードがある時
        if not (last_record.empty):
            # DBの最新レコードより古いcandleは削除
            while not (candles.empty):
                last_record_datetime = \
                    datetime.datetime.strptime(last_record.iloc[0]['datetime'], self.time_format)
                candle_datetime = \
                    datetime.datetime.strptime(candles.iloc[0]['datetime'], self.time_format)
                if candle_datetime <= last_record_datetime:
                    # 一番最初の行を削除
                    candles = candles.drop(candles.head(1).index, axis=0)
                else:
                    break

        # DBに書き込み
        header = db.table_defs.get_columns('prices')
        candles.reindex(columns=header) \
            .to_sql(table_name, self.conn, if_exists="append", index=False)

        # macdを計算
        self.update_macd(table_name)
        # bollinger bandを計算
        self.update_bollinger(table_name)

    def update_macd(self, table_name):
        max_records = 60
        df = pd.read_sql_query(
            'select * from ' + table_name + ' '
            + 'order by datetime desc '
            + 'limit ' + str(max_records) + ';'
            , self.conn
        ).sort_values('datetime')
        df = self.calc_macd(df)

        header = db.table_defs.get_columns('prices')
        df.reindex(columns=header) \
            .to_sql(table_name, self.conn, if_exists="replace", index=False)

    def update_bollinger(self, table_name):
        max_records = 60
        df = pd.read_sql_query(
            'select * from ' + table_name + ' '
            + 'order by datetime desc '
            + 'limit ' + str(max_records) + ';'
            , self.conn
        ).sort_values('datetime')
        df = self.calc_bollinger(df)

        header = db.table_defs.get_columns('prices')
        df.reindex(columns=header) \
            .to_sql(table_name, self.conn, if_exists="replace", index=False)

    def create_prices_table(self, table_name):
        sql = db.table_defs.get_create_table_sql('prices', table_name)
        self.conn.execute(sql)

    def calc_macd(self, df):
        macd = pd.DataFrame()
        macd['ema12'] = df['close'].ewm(span=12).mean()
        macd['ema26'] = df['close'].ewm(span=26).mean()
        macd['macd'] = macd['ema12'] - macd['ema26']
        macd['signal'] = macd['macd'].ewm(span=9).mean()
        df['macd'] = macd['macd'].round(6)
        df['macd_signal'] = macd['signal'].round(6)
        df['macd2'] = (macd['macd'] - macd['signal']).round(6)

        return df

    def calc_bollinger(self, df):
        window = 14
        sigma = 2
        boll = pd.DataFrame()
        boll['mean'] = df['close'].rolling(window=window).mean()
        boll['std'] = df['close'].rolling(window=window).std()
        boll['upper'] = boll['mean'] + (boll['std'] * sigma)
        boll['lower'] = boll['mean'] - (boll['std'] * sigma)

        # dfに代入
        df['boll_mid'] = boll['mean'].round(3)
        df['boll_upper'] = boll['upper'].round(3)
        df['boll_lower'] = boll['lower'].round(3)

        return df

class PricesError(Exception):
    pass
