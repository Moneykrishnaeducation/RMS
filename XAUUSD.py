import pandas as pd
from mt5_utils import get_mt5_service

def get_xauusd_data():
    """Fetch and aggregate XAUUSD position data for all accounts."""
    mt5 = get_mt5_service()
    accounts = mt5.list_accounts_by_groups()  # Get all accounts

    data = []
    for account in accounts:
        login = account['login']
        name = account['name']
        group = account['group']

        # Get open positions for this account
        positions = mt5.get_open_positions(login)

        # Filter for XAUUSD symbol
        xauusd_positions = [p for p in positions if p['symbol'] == 'XAUUSD']

        if xauusd_positions:
            # Calculate net lot: buy + , sell -
            net_lot = 0.0
            usd_pnl = 0.0
            for pos in xauusd_positions:
                volume = pos['volume']
                profit = pos['profit'] or 0.0
                if pos['type'] == 'Buy':
                    net_lot += volume
                else:
                    net_lot -= volume
                usd_pnl += profit

            data.append({
                'login': login,
                'name': name,
                'group': group,
                'base_symbol': 'XAUUSD',
                'net_lot': round(net_lot, 2),
                'USD P&L': round(usd_pnl, 2)
            })

    return pd.DataFrame(data)

if __name__ == '__main__':
    df = get_xauusd_data()
    print(df)