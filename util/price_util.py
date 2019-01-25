import pandas as pd

def calc_macd(df):
    macd = pd.DataFrame()
    macd['ema12'] = df['close'].ewm(span=12).mean()
    macd['ema26'] = df['close'].ewm(span=26).mean()
    macd['macd'] = macd['ema12'] - macd['ema26']
    macd['signal'] = macd['macd'].ewm(span=9).mean()
    df['macd'] = macd['macd']
    df['macd_signal'] = macd['signal']
    df['macd2'] = macd['macd'] - macd['signal']
    #macd_direction: macdがシグナルより上なら1, シグナル以下なら-1
    df['macd_direction'] = df['macd2'].apply(lambda v: 1 if v > 0 else -1)

    #macdのcrossを判定
    for i in range(1, len(df)):
        last_price = df.iloc[i-1]
        price = df.iloc[i]
        if last_price['macd_direction'] > price['macd_direction']:
            #1つ前のmacd_drectionが大きい->下向きにクロスした
            df.at[i, 'crossed'] = str(-1)
        elif last_price['macd_direction'] < price['macd_direction']:
            #1つ前のmacd_drectionが小さい->上向きにクロスした
            df.at[i, 'crossed'] = str(1)
        else:
            df.at[i, 'crossed'] = str(0)

    return df

def calc_bollinger(df):
    window = 14
    sigma = 2
    boll = pd.DataFrame()
    boll['mean'] = df['close'].rolling(window=window).mean()
    boll['std'] = df['close'].rolling(window=window).std()
    boll['upper'] = boll['mean'] + (boll['std'] * sigma)
    boll['lower'] = boll['mean'] - (boll['std'] * sigma)

    # dfに代入
    df['boll_mid'] = boll['mean']
    df['boll_upper'] = boll['upper']
    df['boll_lower'] = boll['lower']

    return df
