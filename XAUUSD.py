import pandas as pd
import streamlit as st
from MT5Service import MT5Service
def get_xauusd_data():
    """
    Returns a table of:
    login, name, group, base_symbol (XAUUSD), net_lot, use_pnl
    including both profit and loss (open + closed).
    """
    BASE_SYMBOL = "XAUUSD"

    mt5 = MT5Service()
    accounts = mt5.list_accounts_by_groups()
    results = []

    for acc in accounts:
        login_id = acc["login"]
        name = acc["name"]
        group = acc["group"]

        # ---- OPEN POSITIONS (BUY / SELL) ----
        positions = mt5.get_open_positions(login_id)
        buy_lot = 0.0
        sell_lot = 0.0
        open_pnl = 0.0

        for p in positions:
            if p["symbol"] == BASE_SYMBOL:
                volume = float(p["volume"])
                if p["type"] == "Buy":
                    buy_lot += volume
                else:
                    sell_lot += volume

                open_pnl += float(p["profit"])

        # ---- CLOSED DEALS (PROFIT / LOSS) ----
        deals = mt5.list_deals_by_login(login_id)
        closed_pnl = 0.0

        for d in deals:
            if d["Symbol"] == BASE_SYMBOL:
                closed_pnl += float(d["Profit"])

        # ---- FINAL AGGREGATIONS ----
        net_lot = round(buy_lot - sell_lot, 2)
        use_pnl = round(open_pnl + closed_pnl, 2)

        # Only include accounts with any activity in XAUUSD
        if buy_lot > 0 or sell_lot > 0 or closed_pnl != 0:
            results.append({
                "login": login_id,
                "name": name,
                "group": group,
                "base_symbol": BASE_SYMBOL,
                "net_lot": net_lot,
                "use_pnl": use_pnl
            })

    # Display the results in Streamlit
    if results:
        st.dataframe(pd.DataFrame(results))

    return results
