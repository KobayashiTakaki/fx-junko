import db.db as db
import api.twitter_api as twitter_api
import api.tweet_messages as tweet_messages
import pandas as pd
import datetime
import time
import random
import emoji

conn = db.conn
time_format = db.time_format

# TODO: DataFrameを作成する際にsort=Trueを指定する
# TODO: DataFrameをDBに書き込む際にindex=Falseを指定する

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
        + 'trade_id integer not null primary key,'
        + 'open_time text,'
        + 'trade_state text,'
        + 'tweeted_state text'
        + ');'
    )

    state_records = pd.read_sql_query(
        'select * from ' + table_name + ';'
        , conn
    ).reindex(columns=table_columns)

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

    #statesテーブルから取ったレコードとtradesテーブルから取ったレコードを結合
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

def update_scal_states():
    table_name = 'scal_tweet_states'
    table_columns = [
        'trade_id',
        'open_time',
        'close_time',
        'tweeted'
    ]
    conn.execute(
        'create table if not exists ' + table_name + '('
        + 'trade_id integer not null primary key,'
        + 'open_time text,'
        + 'close_time text'
        + 'tweeted integer'
        + ');'
    )

    state_records = pd.read_sql_query(
        'select * from ' + table_name + ';'
        , conn
    ).reindex(columns=table_columns)

    #close状態のscal tradeで、statesテーブルに存在しないレコードを取得
    new_trades = pd.read_sql_query(
        'select tradeId, openTime, closeTime, state from scal_trades '
        + 'where not exists ('
        + 'select * from ' + table_name + ' as states '
        + 'where scal_trades.tradeId = states.trade_id '
        + ') and state = \'CLOSED\';'
        , conn
    )

    #statesテーブルにないtradeの行を追加する
    for i, row in new_trades.iterrows():
        new_record = pd.Series()
        new_record['trade_id'] = row['tradeId']
        new_record['open_time'] = row['openTime']
        new_record['close_time'] = row['closeTime']
        new_record['tweeted'] = ''
        #行をappend
        state_records = state_records.append(new_record, ignore_index=True)

    #ソートして、DBに書き込み
    state_records.sort_values('trade_id').reset_index(drop=True)\
    .to_sql(table_name, conn, if_exists='replace')

    db.write_log('tweeter', 'scal trade state updated')

def post_trade_tweets(test=False):
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

    for i, row in unsent_records.iterrows():
        #trade_idが一致するレコードをtradesテーブルから取得
        trade = pd.read_sql_query(
            'select * from trades where tradeId = {};'.format(row['trade_id'])
            , conn
        )
        if len(trade) > 0:
            #tradeのSeriesを代入
            #trade_idが一致するレコードは1行だけのはずなのでdfの1番目を取る
            trade = trade.iloc[0]
        else:
            #trade_idが一致するレコードが無ければcontinue
            continue

        #エントリー時のツイートを投稿
        if row['trade_state'] == 'OPEN':
            action = 'entry'
            feeling = 'neutral'
            instrument = trade['instrument'].replace('_', '/')
            start_side = '買い' if int(trade['initialUnits']) > 0 else '売り'
            start_price = format(float(trade['price']), '.3f')
            kunits = format(abs(trade['initialUnits'])/1000, '.1f')
            emoji_head = tweet_messages.get_emoji('neutral')
            info = "【エントリー" + emoji_head + "】\n"\
                + start_side + " " + instrument + "@" + start_price\
                + " ×" + kunits + "kUnits"
            #tweet
            message = tweet_messages.get_message(action)
            kaomoji = tweet_messages.get_kaomoji(feeling)
            tags = "#USDJPY #FX"
            content = (
                message + kaomoji + "\n"
                + info + "\n"
                + tags
            )
            if test:
                print(content)
            else:
                twitter_api.tweet(content)
            #tweeted_state更新
            state_records.at[i, 'tweeted_state'] = 'OPEN'

        #イグジット時のツイートを投稿
        if row['trade_state'] == 'CLOSED':
            instrument = trade['instrument'].replace('_', '/')
            start_side = '買い' if int(trade['initialUnits']) > 0 else '売り'
            start_price = format(float(trade['price']), '.3f')
            kunits = format(abs(trade['initialUnits'])/1000, '.1f')
            end_side = '買い' if start_side == '売り' else '売り'
            end_price = format(float(trade['averageClosePrice']), '.3f')
            pips = format(trade['realizedPL']/abs(trade['initialUnits'])*100, '.1f')
            money = format(trade['realizedPL'], '.1f')
            plus = "+" if trade['realizedPL'] > 0 else ""

            action = 'take_profit' if trade['realizedPL'] > 0 else 'losscut'
            feeling = 'positive' if trade['realizedPL'] > 0 else 'negative'
            emoji_head = tweet_messages.get_emoji('neutral')
            info = "【トレード終了" + emoji_head + "】\n"\
                + start_side + " " + instrument + "@" + start_price\
                + " ×" + kunits + "kUnits\n"\
                + end_side + " " + instrument + "@" + end_price\
                + " ×" + kunits + "kUnits\n"\
                + plus + money + "円(" + plus + pips + " pips)"
            if trade['realizedPL'] > 0:
                action = 'take_profit'
                feeling = 'positive'
            else:
                action = 'losscut'
                feeling = 'negative'
            #tweet
            message = tweet_messages.get_message(action)
            kaomoji = tweet_messages.get_kaomoji(feeling)
            tags = "#USDJPY #FX"
            content = (
                message + kaomoji + "\n"
                + info + "\n"
                + tags
            )
            if test:
                print(content)
            else:
                twitter_api.tweet(content)
            #tweeted_state更新
            state_records.at[i, 'tweeted_state'] = 'CLOSED'

        #高速連投を避けるためのsleep
        time.sleep(5)

    #DBに書き込み
    state_records.to_sql(table_name, conn, if_exists='replace')

def post_scal_tweet(test=False):
    update_scal_states()

    table_name = 'scal_tweet_states'
    table_columns = [
        'trade_id',
        'open_time',
        'close_time',
        'tweeted'
    ]

    state_records = pd.read_sql_query(
        'select * from ' + table_name + ' '
        + 'order by open_time;'
        , conn
    ).reindex(columns=table_columns)

    #未投稿のscal tradesを取得
    unsent_records = state_records.query('tweeted != 1')

    if len(unsent_records) > 0:
        #最新のscal tradeのclose_timeと現在を比較
        last_close_time = datetime.datetime.strptime(
            unsent_records.iloc[-1]['close_time'], time_format)
        now = datetime.datetime.now(datetime.timezone.utc)
        interval = datetime.timedelta(minutes=15)
        #一定時間以上経過していたらtweet実行
        if now - last_close_time > interval:
            #tradeIdのlistをstrに変換して、カンマ区切りの文字列にjoin
            tradeIds = ', '.join(map(str, list(unsent_records['trade_id'])))
            #tradesテーブルからtrade_idが一致するレコードを取得
            trades = pd.read_sql_query(
                'select * from scal_trades where tradeId in ({});'.format(tradeIds)
                , conn
            )
            money_toral = 0
            pips_total = 0
            for i, row in trades.iterrows():
                pips = float(row['realizedPL'])/abs(row['initialUnits'])*100
                money_toral += float(row['realizedPL'])
                pips_total += pips

            side = 'win' if pips_total > 0 else 'lose'
            feeling = 'positive' if pips_total > 0 else 'negative'
            scal_tweet = tweet_messages.get_scal_tweet(side)
            kaomoji = tweet_messages.get_kaomoji(feeling)

            content = scal_tweet[0]\
                + '{0:.0f}'.format(abs(money_toral)) + "円" + scal_tweet[1]\
                + kaomoji + "\n"\
                + "(" + '{0:+.1f}'.format(pips_total) + "pips)"

            if test:
                print(content)
            else:
                twitter_api.tweet(content)

            #tweeted_state更新
            #全レコードのtweeted=1
            state_records['tweeted'] = 1

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
    table_name = 'trade_tweet_states'
    keep_span = datetime.timedelta(weeks=1)
    keep_from = (datetime.datetime.now() - keep_span).strftime(time_format)
    conn.execute(
        'delete from ' + table_name + ' where open_time < '
        + '\'' + keep_from + '\' ;'
    )
    conn.commit()

def post_pl_tweet(test=False):
    #日付を日曜日にするために引く日数
    days_shift = datetime.datetime.now(datetime.timezone.utc).weekday() + 1
    #今日からdays_shiftを引いた日付
    start_date = (datetime.datetime.now(datetime.timezone.utc)\
        - datetime.timedelta(days=days_shift)).strftime('%Y-%m-%d')
    #時間
    start_time = '23:00'
    start_datetime = start_date + ' ' + start_time
    trades = pd.read_sql_query(
        'select * from trades '
        + 'where openTime > \'' + start_datetime + '\' '
        + 'and state = \'CLOSED\';'
        , conn
    )
    scal_trades = pd.read_sql_query(
        'select * from scal_trades '
        + 'where openTime > \'' + start_datetime + '\' '
        + 'and state = \'CLOSED\';'
        , conn
    )

    merged = pd.concat([trades, scal_trades])
    print(merged)

    pips_total = 0
    money_total = 0

    for i, row in merged.iterrows():
        pips = row['realizedPL']/abs(row['initialUnits'])*100
        pips_total += pips
        money_total += float(row['realizedPL'])

    plus = "+" if pips_total > 0 else ""
    feeling = 'positive' if pips_total > 0 else 'negative'
    kaomoji = tweet_messages.get_kaomoji(feeling)
    emojis = ""
    for i in range(random.randrange(1,3)):
        emojis += tweet_messages.get_emoji(feeling)

    info = "【今週の損益発表コーナー】\n"\
        + "今週の損益は・・・\n"\
        + plus + str(round(money_total, 1)) + "円("\
        + plus + str(format(pips_total, '.1f')) + "pips)\n"\
        + "でした"\
        + "〜"*random.randrange(1,3)\
        + "！"*random.randrange(1,3)\
        + emojis + "\n"\
        + kaomoji
    tags = "#USDJPY #FX"

    content = info + "\n"\
        + tags

    if test:
        print(content)
    else:
        twitter_api.tweet(content)
