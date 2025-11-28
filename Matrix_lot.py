import pandas as pd
from MT5Service import MT5Service

def get_net_lot_matrix(accounts_df):
    """
    Generate a matrix of net lots for each login vs specified symbols.
    Net lot is calculated as sum of buy volumes minus sum of sell volumes for each symbol.
    """
    svc = MT5Service()
    all_net_positions = []
    symbols = ['XAUUSD', 'EURUSD', 'AUDUSD', 'BTCUSD', 'GBPJPY', 'GBPUSD', 'NGAS.FT', 'Tesla', 'USDCAD', 'USDCHF', 'USDJPY', 'USOil', 'XAGUSD']

    for login in accounts_df['login'].unique():
        try:
            positions = svc.get_open_positions(login)
            for p in positions:
                symbol = p.get('symbol')
                if symbol not in symbols:
                    continue  # only include specified symbols
                vol = p.get('volume', 0)
                typ = p.get('type')
                net_vol = vol if typ == 'Buy' else -vol
                all_net_positions.append({'login': login, 'symbol': symbol, 'net_vol': net_vol})
        except Exception as e:
            continue

    if not all_net_positions:
        # return empty df with columns
        df = pd.DataFrame(columns=['Login'] + symbols)
        return df

    df = pd.DataFrame(all_net_positions)
    # pivot to create matrix
    pivot_df = df.pivot_table(index='login', columns='symbol', values='net_vol', aggfunc='sum', fill_value=0)
    # reset index
    pivot_df.reset_index(inplace=True)
    pivot_df.rename(columns={'login': 'Login'}, inplace=True)
    # ensure all symbols are present, even if no data
    for sym in symbols:
        if sym not in pivot_df.columns:
            pivot_df[sym] = 0
    # reorder columns
    cols = ['Login'] + symbols
    pivot_df = pivot_df[cols]
    return pivot_df
