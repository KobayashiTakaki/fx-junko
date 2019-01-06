import db.db as db
import api.twitter_api as twitter_api
import api.tweet_messages as tweet_messages
import pandas as pd
import datetime
import random
import emoji

conn = db.conn
time_format = db.time_format

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
            start_side = 'buy' if int(trade['initialUnits']) > 0 else 'sell'
            start_price = format(float(trade['price']), '.3f')
            Kunits = format(abs(trade['initialUnits'])/1000, '.1f')
            emoji_head = tweet_messages.get_emoji('neutral')
            info = "【エントリー" + emoji_head + "】\n"\
                + start_side + " " + instrument + "@" + start_price\
                + "×" + Kunits + "units"
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
            start_side = 'buy' if int(trade['initialUnits']) > 0 else 'sell'
            start_price = format(float(trade['price']), '.3f')
            Kunits = format(abs(trade['initialUnits'])/1000, '.1f')
            end_side = 'buy' if start_side == 'sell' else 'sell'
            end_price = format(float(trade['averageClosePrice']), '.3f')
            pips = float(trade['realizedPL'])
            money = format(abs(trade['initialUnits']) * pips /100, '.1f')
            plus = "+" if trade['realizedPL'] > 0 else ""

            action = 'take_profit' if pips > 0 else 'losscut'
            feeling = 'positive' if pips > 0 else 'negative'
            emoji_head = tweet_messages.get_emoji('neutral')
            info = "【トレード終了" + emoji_head + "】\n"\
                + start_side + " " + instrument + "@" + start_price\
                + "×" + Kunits + "Kunits\n"\
                + end_side + " " + instrument + "@" + end_price\
                + "×" + Kunits + "Kunits\n"\
                + plus + money + "円(" + plus +format(pips, '.1f') + " pips)"
            if pips > 0:
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

def post_pl_tweet():
    span = datetime.timedelta(weeks=1)
    date_from = (datetime.datetime.now() - span).strftime(time_format)
    trades = pd.read_sql_query(
        'select * from trades '
        + 'where openTime > \'' + date_from + '\' '
        + 'and state = \'CLOSED\';'
        , conn
    )

    pips_total = 0
    money_total = 0

    for i, row in trades.iterrows():
        pips = float(row['realizedPL'])
        amount = abs(float(row['initialUnits']))
        money = pips * amount / 100
        pips_total += pips
        money_total += money

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

    twitter_api.tweet(content)
