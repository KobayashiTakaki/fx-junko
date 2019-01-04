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
    #ids = list(state_records['trade_id'])

    trades = pd.read_sql_query(
        'select tradeId, state from trades;'
        ,conn
    )

    #tradesテーブルにあるデータから、すでにstatesに存在するものを取得
    exist_trades = pd.read_sql_query(
        'select tradeId, state from trades '
        + 'where exists ('
        + 'select * from ' + table_name + ' as states '
        + 'where trades.tradeId = states.trade_id '
        + ');'
        , conn
    )

    new_trades = pd.read_sql_query(
        'select tradeId, openTime, state from trades '
        + 'where not exists ('
        + 'select * from ' + table_name + ' as states '
        + 'where trades.tradeId = states.trade_id '
        + ');'
        , conn
    )

    merge_exist = pd.merge(state_records, exist_trades,
        left_on='trade_id', right_on='tradeId')

    #既にstatesテーブルにあるtrade_stateの値を
    #tradeテーブルから取得したstateで上書き
    for i, row in merge_exist.iterrows():
        row['trade_state'] = row['state']

    #結合したtradeの列を削除して代入
    state_records = merge_exist.drop(['tradeId', 'state'], axis=1)

    #statesテーブルにないtradeの行を追加する
    for i, row in new_trades.iterrows():
        new_record = pd.Series()
        new_record['trade_id'] = row['tradeId']
        new_record['open_time'] = row['openTime']
        new_record['trade_state'] = row['state']
        new_record['tweeted_state'] = ''
        #行をappend
        state_records = state_records.append(new_record, ignore_index=True)

    #ソートして、DBに書き込み
    state_records.sort_values('trade_id').reset_index(drop=True)\
    .to_sql(table_name, conn, if_exists='replace')

    db.write_log('tweeter', 'trade state updated')

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
        )
        if len(trade) > 0:
            trade = trade.iloc[0]
        else:
            continue

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
