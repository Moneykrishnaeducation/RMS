# pnl_matrix.py
import pandas as pd
import streamlit as st
from MT5Service import MT5Service

@st.cache_data(ttl=5)
def get_login_symbol_pnl_matrix(data):
    """
    Returns a matrix of total USD P&L per Login vs Symbol.
    P&L is computed from closed trades.
    """
    svc = MT5Service()

    if data.empty:
        return pd.DataFrame()

    matrix = {}
    all_symbols = set()

    for acc in data.to_dict('records'):
        login = str(acc["login"])
        deals = svc.list_deals_by_login(login)   # ⭐ closed PL data

        symbol_pnl = {}

        for d in deals or []:
            symbol = d["Symbol"]
            profit = float(d["Profit"])  # USD P&L

            if symbol not in symbol_pnl:
                symbol_pnl[symbol] = 0.0

            symbol_pnl[symbol] += profit
            all_symbols.add(symbol)

        matrix[login] = symbol_pnl

    # Convert to DataFrame
    df = pd.DataFrame.from_dict(matrix, orient="index").fillna(0.0)

    # Add All Login summary row
    df.loc["All Login"] = df.sum()

    # Sort columns alphabetically
    df = df[sorted(df.columns)]

    # Move 'All Login' to top
    df = df.reindex(["All Login"] + [i for i in df.index if i != "All Login"])

    return df
