tables = {
    'trades': [
        ['tradeId', 'integer primary key'],
        ['instrument', 'text'],
        ['price', 'real'],
        ['openTime', 'text'],
        ['state', 'text'],
        ['initialUnits', 'real'],
        ['realizedPL', 'real'],
        ['unrealizedPL', 'real'],
        ['averageClosePrice', 'real'],
        ['closeTime', 'text'],
        ['stopLossOrderState', 'text'],
        ['trailingStopLossOrderState', 'text'],
        ['trailingStopLossOrderDistance', 'real']
    ],
    'prices': [
        ['datetime', 'text primary key'],
        ['open', 'real'],
        ['high', 'real'],
        ['low', 'real'],
        ['close', 'real'],
        ['macd', 'real'],
        ['macd_signal', 'real'],
        ['macd2', 'real'],
        ['boll_upper', 'real'],
        ['boll_mid', 'real'],
        ['boll_lower', 'real']
    ],
    'trade_tweet_states': [
        ['trade_id', 'integer primary key'],
        ['open_time', 'test'],
        ['trade_state', 'text'],
        ['tweeted_state', 'text']
    ]
}

def get_create_table_sql(table, table_name):
    defs_list = tables[table]
    defs_str = ', '.join([' '.join(elem) for elem in defs_list])
    return 'create table if not exists ' + table_name + '(' \
        + defs_str \
        + ');'

def get_columns(table):
    defs_list = tables[table]
    return [elem[0] for elem in defs_list]
