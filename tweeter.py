import db.db as db
import api.twitter_api as twitter_api
import pandas as pd

conn = db.conn

def update_trade_states():
    table_name = 'trade_tweet_states'
    table_columns = [
        'trade_id',
        'open_time',
        'trade_state',
        'tweeted_state'
    ]
    conn.execute(
        'create table if not exists ' + table_name + '('
        + 'trade_id number not null primary key,'
        + 'open_time text,'
        + 'trade_state text,'
        + 'tweeted_state text'
        + ');'
    )

    state_records = pd.read_sql_query(
        'select * from ' + table_name + ';'
        , conn
    ).reindex(columns=table_columns)

    #テーブルにあるtrade_idのリスト
    ids = list(state_records['trade_id'])

    #tradesテーブルにあるデータを取得
    trades = pd.read_sql_query(
        'select tradeId, openTime, state from trades;'
        , conn
    )

    for i, trade in trades.iterrows():
        if trade['tradeId'] in ids:
            #テーブルにtradeIdがあったら、そのレコードを更新
            #既存レコードの行番号を取得
            idx = state_records.query('trade_id == {}'.format(trade['tradeId'])).index
            #行番号を指定してtrade_stateの値を変更
            state_records.at[idx, 'trade_state'] = trade['state']
        else:
            #テーブルにtradeIdが無かったら、新しいレコードを追加
            new_record = pd.Series()
            new_record['trade_id'] = trade['tradeId']
            new_record['open_time'] = trade['openTime']
            new_record['trade_state'] = trade['state']
            new_record['tweeted_state'] = ''
            state_records = state_records.append(new_record, ignore_index=True)

    #ソートして、DBに書き込み
    state_records.sort_values('trade_id').reset_index(drop=True)\
    .to_sql(table_name, conn, if_exists='replace')

def post_pending_tweets():
    update_trade_states()

    table_name = 'trade_tweet_states'
    table_columns = [
        'trade_id',
        'open_time',
        'trade_state',
        'tweeted_state'
    ]

    state_records = pd.read_sql_query(
        'select * from ' + table_name + ';'
        , conn
    ).reindex(columns=table_columns)

    unsent_records = state_records.query('trade_state != tweeted_state')
    print(unsent_records)

    for i, row in unsent_records.iterrows():
        trade = pd.read_sql_query(
            'select * from trades where tradeId = {};'.format(row['trade_id'])
            , conn
        ).iloc[0]

        if row['trade_state'] == 'OPEN':
            action = 'entry'
            feeling = 'neutral'
            instrument = trade['instrument'].replace('_', '/')
            start_side = 'buy' if int(trade['initialUnits']) > 0 else 'sell'
            start_price = format(float(trade['price']), '.3f')
            info = [
                "[Entry]",
                start_side + " " + instrument + "@" + start_price
            ]
            #tweet
            twitter_api.tweet(action, feeling, info)
            #tweeted_state更新
            state_records.at[i, 'tweeted_state'] = 'OPEN'

        if row['trade_state'] == 'CLOSED':
            instrument = trade['instrument'].replace('_', '/')
            start_side = 'buy' if int(trade['initialUnits']) > 0 else 'sell'
            start_price = format(float(trade['price']), '.3f')
            end_side = 'buy' if start_side == 'sell' else 'sell'
            end_price = format(float(trade['averageClosePrice']), '.3f')
            pips = float(trade['realizedPL'])

            action = 'take_profit' if pips > 0 else 'losscut'
            feeling = 'positive' if pips > 0 else 'negative'
            info = [
                "[Trade Close]",
                start_side + " " + instrument + "@" + start_price,
                end_side + " " + instrument + "@" + end_price,
                format(pips, '.1f') + " pips"
            ]
            if pips > 0:
                action = 'take_profit'
                feeling = 'positive'
            else:
                action = 'losscut'
                feeling = 'negative'
            #tweet
            twitter_api.tweet(action, feeling, info)
            #tweeted_state更新
            state_records.at[i, 'tweeted_state'] = 'CLOSED'

        #DBに書き込み
        state_records.to_sql(table_name, conn, if_exists='replace')

def clear_pending_tweets():
    table_name = 'trade_tweet_states'
    table_columns = [
        'trade_id',
        'open_time',
        'trade_state',
        'tweeted_state'
    ]

    state_records = pd.read_sql_query(
        'select * from ' + table_name + ';'
        , conn
    ).reindex(columns=table_columns)

    for i, row in state_records.iterrows():
        #tweeted_stateにtrade_stateの値を代入
        state_records.at[i, 'tweeted_state']\
            = state_records.iloc[i]['trade_state']

    #DBに書き込み
    state_records.to_sql(table_name, conn, if_exists='replace')

def delete_old_records():
    keep_span = datetime.timedelta(weeks=1)
    keep_from = (datetime.datetime.now() - keep_span).strftime(time_format)
    conn.execute(
        'delete from ' + table_name + ' where open_time < '
        + '\'' + keep_from + '\' ;'
    )
    conn.commit()
