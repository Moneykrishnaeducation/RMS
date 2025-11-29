import pandas as pd
import streamlit as st
from Services import MT5ManagerActions

@st.cache_data(ttl=5)      # 🔥 Auto-cache for speed (reloads every 5 sec)
def get_login_symbol_matrix():
    svc = MT5ManagerActions()

    accounts = svc.list_mt5_accounts()
    if not accounts:
        return pd.DataFrame()

    matrix = {}
    all_symbols = set()

    for acc in accounts:
        login = acc["Login"]
        orders = svc.list_orders_by_login(login)

        symbol_lots = {}

        for o in orders or []:
            symbol = o["Symbol"]
            volume = float(o["Volume"])
            order_type = o["Type"]

            if symbol not in symbol_lots:
                symbol_lots[symbol] = 0.0

            # BUY 0 → Add, SELL 1 → Subtract
            symbol_lots[symbol] += volume if order_type == 0 else -volume
            all_symbols.add(symbol)

        matrix[login] = symbol_lots

    # Convert into DataFrame
    df = pd.DataFrame.from_dict(matrix, orient="index").fillna(0.0)

    # Add "All Login" Row
    df.loc["All Login"] = df.sum()

    # Sort columns alphabetically
    df = df[sorted(df.columns)]

    # Move All Login to top
    df = df.reindex(["All Login"] + [i for i in df.index if i != "All Login"])

    return df
