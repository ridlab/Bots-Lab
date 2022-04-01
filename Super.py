
import uuid
import botslib.bots_api as ba
import ccxt
import config
from sys import set_coroutine_origin_tracking_depth
import ta
import time
import numpy as np
from datetime import datetime
import binance.client
import pandas as pd
import json
from ta.volatility import BollingerBands, AverageTrueRange


import warnings

warnings.filterwarnings('ignore')
import schedule
import pandas as pd
pd.set_option('display.max_rows', None)
bots_platform = ba.BEM_API('https://signal.revenyou.io/paper/api/signal/v2/')


exchange = ccxt.binanceus({
    "apiKey": config.API_KEY,
    "secret": config.SECRET
})

def tr(data):
    data['previous_close'] = data['close'].shift(1)
    data['high-low'] = abs(data['high'] - data['low'])
    data['high-pc'] = abs(data['high'] - data['previous_close'])
    data['low-pc'] = abs(data['low'] - data['previous_close'])

    tr = data[['high-low', 'high-pc', 'low-pc']].max(axis=1)

    return tr

def atr(data, period):
    data['tr'] = tr(data)
    atr = data['tr'].rolling(period).mean()

    return atr

def supertrend(df, period=7, atr_multiplier=3):
    hl2 = (df['high'] + df['low']) / 2
    df['atr'] = atr(df, period)
    df['upperband'] = hl2 + (atr_multiplier * df['atr'])
    df['lowerband'] = hl2 - (atr_multiplier * df['atr'])
    df['in_uptrend'] = True

    for current in range(1, len(df.index)):
        previous = current - 1

        if df['close'][current] > df['upperband'][previous]:
            df['in_uptrend'][current] = True
        elif df['close'][current] < df['lowerband'][previous]:
            df['in_uptrend'][current] = False
        else:
            df['in_uptrend'][current] = df['in_uptrend'][previous]

            if df['in_uptrend'][current] and df['lowerband'][current] < df['lowerband'][previous]:
                df['lowerband'][current] = df['lowerband'][previous]

            if not df['in_uptrend'][current] and df['upperband'][current] > df['upperband'][previous]:
                df['upperband'][current] = df['upperband'][previous]
        
    return df


in_position = False

def check_buy_sell_signals(df):
    global in_position

    print("checking for buy and sell signals")
    print(df.tail(5))
    last_row_index = len(df.index) - 1
    previous_row_index = last_row_index - 1

    if not df['in_uptrend'][previous_row_index] and df['in_uptrend'][last_row_index]:
        print("changed to uptrend, buy")
        if not in_position:
            order = ba.OrderParameters(signalProvider='TrendMaster',
                                       signalProviderKey='PDC6V7X7TYFB5KZF',
                                       extId=str(uuid.uuid4()),
                                       exchange='binance',
                                       baseAsset='BTC',
                                       quoteAsset='USDT',
                                       side='buy',
                                       limitPrice='48000',
                                       qtyPct='100',
                                       ttlType='secs',
                                       ttlSecs=str(40))
            print(json.loads(bots_platform.placeOrder(order)))
            in_position = True
        else:
            print("already in position, nothing to do")
    
    if df['in_uptrend'][previous_row_index] and not df['in_uptrend'][last_row_index]:
        if in_position:
            print("changed to downtrend, sell")
            order = print('chnaged to downtrend,sell')
            order = ba.OrderParameters(signalProvider='TrendMaster',
                                       signalProviderKey='PDC6V7X7TYFB5KZF',
                                       extId=str(uuid.uuid4()),
                                       exchange='binance',
                                       baseAsset='BTC',
                                       quoteAsset='USDT',
                                       side='sell',
                                       limitPrice='43000',
                                       qtyPct='100',
                                       ttlType='secs',
                                       ttlSecs=str(40))
            print(json.loads(bots_platform.placeOrder(order)))
            in_position = False
        else:
            print("You aren't in position, nothing to sell")

def run_bot():
    print(f"Fetching new bars for {datetime.now().isoformat()}")
    bars = exchange.fetch_ohlcv('BTCUSDT', timeframe='15m', limit=100)
    df = pd.DataFrame(bars[:-1], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

    supertrend_data = supertrend(df)
    
    check_buy_sell_signals(supertrend_data)


schedule.every(10).seconds.do(run_bot)


while True:
    schedule.run_pending()
    time.sleep(1)
