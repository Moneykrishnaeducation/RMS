import pandas as pd
import streamlit as st
from MT5Service import MT5Service

@st.cache_data(ttl=5)      # 🔥 Auto-cache for speed (reloads every 5 sec)
def get_login_symbol_matrix(accounts_df=None, positions_cache=None):
    svc = MT5Service()

    if accounts_df is not None and not accounts_df.empty:
        # Use provided accounts dataframe
        logins = accounts_df['login'].astype(str).unique()
    else:
        # Fallback to fetching all accounts
        accounts = svc.list_mt5_accounts()
        if not accounts:
            return pd.DataFrame()
        logins = [acc["Login"] for acc in accounts]

    matrix = {}
    all_symbols = set()

    # If positions_cache wasn't provided, try to read it from Streamlit session state
    if positions_cache is None:
        try:
            positions_cache = st.session_state.get('positions_cache')
        except Exception:
            positions_cache = None

    # Normalize positions data if cache is available
    positions_list = None
    if positions_cache:
        # positions_cache may contain {'data': [...], 'timestamp': ..., ...}
        if isinstance(positions_cache, dict) and 'data' in positions_cache:
            positions_list = positions_cache.get('data') or []
        elif isinstance(positions_cache, list):
            positions_list = positions_cache

    for login in logins:
        symbol_lots = {}

        # First try to use cached positions (faster, background scanner)
        if positions_list:
            # positions stored by scanner include 'Login' key
            for p in positions_list:
                try:
                    p_login = str(p.get('Login') or p.get('login') or '')
                except Exception:
                    p_login = ''
                if p_login != str(login):
                    continue

                symbol = p.get('Symbol') or p.get('symbol')
                volume = p.get('Vol') or p.get('volume') or 0
                order_type = p.get('Type') or p.get('type')

                try:
                    volume = float(volume)
                except Exception:
                    volume = 0.0

                if not symbol:
                    continue

                if symbol not in symbol_lots:
                    symbol_lots[symbol] = 0.0

                # Determine if position is buy or sell
                is_buy = False
                if isinstance(order_type, (int, float)):
                    is_buy = int(order_type) == 0
                elif isinstance(order_type, str):
                    is_buy = order_type.strip().lower().startswith('b')
                else:
                    is_buy = True

                symbol_lots[symbol] += volume if is_buy else -volume
                all_symbols.add(symbol)

        else:
            # Fallback: query MT5Service per-login
            positions = svc.get_open_positions(login)
            for p in positions or []:
                symbol = p.get('symbol') or p.get('Symbol')
                volume = p.get('volume') or p.get('Volume') or 0
                order_type = p.get('type') or p.get('Type')

                try:
                    volume = float(volume)
                except Exception:
                    volume = 0.0

                if not symbol:
                    continue

                if symbol not in symbol_lots:
                    symbol_lots[symbol] = 0.0

                is_buy = False
                if isinstance(order_type, (int, float)):
                    is_buy = int(order_type) == 0
                elif isinstance(order_type, str):
                    is_buy = order_type.strip().lower().startswith('b')
                else:
                    is_buy = True

                symbol_lots[symbol] += volume if is_buy else -volume
                all_symbols.add(symbol)

        matrix[login] = symbol_lots

    # Convert into DataFrame
    df = pd.DataFrame.from_dict(matrix, orient="index").fillna(0.0)

    if not df.empty and len(df.columns) > 0:
        # Add "All Login" Row
        df.loc["All Login"] = df.sum()

        # Sort columns alphabetically
        df = df[sorted(df.columns)]

        # Move All Login to top
        df = df.reindex(["All Login"] + [i for i in df.index if i != "All Login"])

    return df
