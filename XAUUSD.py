import pandas as pd
import streamlit as st
import time
from MT5Service import MT5Service

def get_xauusd_data():
    st.subheader('XAUUSD Positions')

    # Initialize filter in session state
    if 'xauusd_filter' not in st.session_state:
        st.session_state.xauusd_filter = 'all'

    # Get positions data from cache
    positions_cache = st.session_state.get('positions_cache', {})
    positions_list = positions_cache.get('data') or []

    # Get accounts
    svc = MT5Service()
    try:
        accounts = svc.list_accounts_by_groups()
        if not accounts:
            accounts = svc.list_accounts_by_range(start=1, end=100000)
    except Exception as e:
        st.error(f"Error loading accounts: {e}")
        accounts = []
    accounts_df = pd.DataFrame(accounts)

    # Function to create and display the dataframe
    def update_table():
        xauusd_positions = [p for p in positions_list if p.get('Symbol') == 'XAUUSD']
        if not xauusd_positions:
            # Show empty table with columns
            df = pd.DataFrame(columns=['Login', 'Name', 'Group', 'Base Symbol', 'Type', 'Net Lot', 'USD P&L'])
            table_placeholder.dataframe(df)
            if not positions_list:
                st.info('No data available. Please wait for background scan.')
            else:
                st.info('No XAUUSD data found.')
            return

        # Apply filter based on session state before aggregating
        if st.session_state.xauusd_filter == 'buy':
            xauusd_positions = [p for p in xauusd_positions if p.get('Type') == 'Buy']
        elif st.session_state.xauusd_filter == 'sell':
            xauusd_positions = [p for p in xauusd_positions if p.get('Type') == 'Sell']

        # Aggregate per login
        agg = {}
        for p in xauusd_positions:
            login = str(p.get('Login'))
            vol = float(p.get('Vol', 0))
            if p.get('Type') == 'Sell':
                vol = -vol
            if login not in agg:
                agg[login] = {'net_lot': 0}
            agg[login]['net_lot'] += vol

        # Create dataframe
        data = []
        for login, vals in agg.items():
            account = accounts_df[accounts_df['login'].astype(str) == login]
            if not account.empty:
                name = account['name'].iloc[0]
                group = account['group'].iloc[0]
                usd_pnl = account['profit'].iloc[0]
            else:
                name = 'Unknown'
                group = 'Unknown'
                usd_pnl = 0.0
            data.append({
                'Login': login,
                'Name': name,
                'Group': group,
                'Base Symbol': 'XAUUSD',
                'Type': 'Buy' if vals['net_lot'] > 0 else 'Sell' if vals['net_lot'] < 0 else 'Neutral',
                'Net Lot': vals['net_lot'],
                'USD P&L': usd_pnl
            })

        df = pd.DataFrame(data)

        table_placeholder.dataframe(df)

    # Filters above the table
    col_all, col_buy, col_sell = st.columns([1, 1, 1])
    with col_all:
        if st.button('All'):
            st.session_state.xauusd_filter = 'all'
    with col_buy:
        if st.button('XAUUSD_Buy'):
            st.session_state.xauusd_filter = 'buy'
    with col_sell:
        if st.button('XAUUSD_Sell'):
            st.session_state.xauusd_filter = 'sell'

    # Placeholder for dynamic table update
    table_placeholder = st.empty()

    # Initial table display
    update_table()
