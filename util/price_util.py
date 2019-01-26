import pandas as pd

def calc_macd(df):
    macd = pd.DataFrame()
    macd['ema12'] = df['close'].ewm(span=12).mean()
    macd['ema26'] = df['close'].ewm(span=26).mean()
    macd['macd'] = macd['ema12'] - macd['ema26']
    macd['signal'] = macd['macd'].ewm(span=9).mean()
    df['macd'] = macd['macd'].round(6)
    df['macd_signal'] = macd['signal'].round(6)
    df['macd2'] = (macd['macd'] - macd['signal']).round(6)

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
    df['boll_mid'] = boll['mean'].round(3)
    df['boll_upper'] = boll['upper'].round(3)
    df['boll_lower'] = boll['lower'].round(3)

    return df
