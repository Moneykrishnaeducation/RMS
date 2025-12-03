import pandas as pd
import streamlit as st
import time
from MT5Service import MT5Service

def get_xauusd_data():
    st.subheader('XAUUSD Positions')

    # Initialize filter in session state
    if 'xauusd_filter' not in st.session_state:
        st.session_state.xauusd_filter = 'all'

    # Get combined data from cache
    combined_cache = st.session_state.get('combined_cache', {})
    combined_list = combined_cache.get('data') or []

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
        xauusd_combined = [c for c in combined_list if c.get('Symbol') == 'XAUUSD']
        if not xauusd_combined:
            # Show empty table with columns
            df = pd.DataFrame(columns=['Login', 'Name', 'Group', 'Base Symbol', 'Type', 'Net Lot', 'USD P&L'])
            table_placeholder.dataframe(df)
            if not combined_list:
                st.info('No data available. Please wait for background scan or trigger manual scan.')
            else:
                st.info('No XAUUSD data found.')
            return

        # Apply filter based on session state before aggregating
        if st.session_state.xauusd_filter == 'buy':
            xauusd_combined = [c for c in xauusd_combined if c.get('Type') == 'Buy']
        elif st.session_state.xauusd_filter == 'sell':
            xauusd_combined = [c for c in xauusd_combined if c.get('Type') == 'Sell']

        # Aggregate per login
        agg = {}
        for c in xauusd_combined:
            login = str(c.get('Login'))
            vol = float(c.get('NetLot', 0))
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
                usd_pnl = float(account['profit'].iloc[0]) if 'profit' in account.columns else 0.0
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

    # Trigger automatic scan
    try:
        st.info("🔄 Starting automatic data scan...")
        if accounts:
            accounts_df = pd.DataFrame(accounts)
            if 'login' in accounts_df.columns:
                accounts_df['login'] = accounts_df['login'].astype(str)

                all_combined = combined_list.copy() if combined_list else []  # Start with existing
                total_accounts = len(accounts_df['login'].unique())
                progress_bar = st.progress(0)
                status_text = st.empty()

                scanned = 0
                for login in accounts_df['login'].unique():
                    try:
                        status_text.text(f"Scanning account {login} ({scanned+1}/{total_accounts})...")
                        # Fetch deals
                        deals = svc.list_deals_by_login(login)
                        # Fetch positions
                        positions = svc.get_open_positions(login)

                        # Process deals
                        if deals:
                            for d in deals:
                                if d.get('Symbol') == 'XAUUSD':
                                    vol = float(d.get('Volume', 0))
                                    if d.get('Type') == 1:  # Sell
                                        vol = -vol
                                    combined_data = {
                                        'Login': login,
                                        'Symbol': d.get('Symbol'),
                                        'NetLot': vol,
                                        'Profit': float(d.get('Profit') or 0),
                                        'Type': 'Buy' if vol > 0 else 'Sell' if vol < 0 else 'Neutral'
                                    }
                                    # Add account details
                                    account_row = accounts_df[accounts_df['login'] == login]
                                    if not account_row.empty:
                                        combined_data['Name'] = account_row['name'].iloc[0] if 'name' in account_row.columns else ''
                                        combined_data['Group'] = account_row['group'].iloc[0] if 'group' in account_row.columns else ''
                                    all_combined.append(combined_data)

                        # Process positions
                        if positions:
                            for p in positions:
                                if p.get('symbol') == 'XAUUSD':
                                    vol = float(p.get('volume', 0))
                                    if p.get('type') == 'Sell':
                                        vol = -vol
                                    combined_data = {
                                        'Login': login,
                                        'Symbol': p.get('symbol'),
                                        'NetLot': vol,
                                        'Profit': 0,  # Positions don't have profit in the same way
                                        'Type': 'Buy' if vol > 0 else 'Sell' if vol < 0 else 'Neutral'
                                    }
                                    # Add account details
                                    account_row = accounts_df[accounts_df['login'] == login]
                                    if not account_row.empty:
                                        combined_data['Name'] = account_row['name'].iloc[0] if 'name' in account_row.columns else ''
                                        combined_data['Group'] = account_row['group'].iloc[0] if 'group' in account_row.columns else ''
                                    all_combined.append(combined_data)

                        # Update table dynamically if XAUUSD data found
                        xauusd_combined_dynamic = [c for c in all_combined if c.get('Symbol') == 'XAUUSD']
                        if xauusd_combined_dynamic:
                            # Apply filter based on session state before aggregating for dynamic display
                            if st.session_state.xauusd_filter == 'buy':
                                xauusd_combined_dynamic = [c for c in xauusd_combined_dynamic if c.get('Type') == 'Buy']
                            elif st.session_state.xauusd_filter == 'sell':
                                xauusd_combined_dynamic = [c for c in xauusd_combined_dynamic if c.get('Type') == 'Sell']

                            # Aggregate per login for dynamic display
                            agg_dynamic = {}
                            for c in xauusd_combined_dynamic:
                                login_str = str(c.get('Login'))
                                vol = float(c.get('NetLot', 0))
                                pnl = float(c.get('Profit', 0))
                                if login_str not in agg_dynamic:
                                    agg_dynamic[login_str] = {'net_lot': 0, 'usd_pnl': 0}
                                agg_dynamic[login_str]['net_lot'] += vol
                                agg_dynamic[login_str]['usd_pnl'] += pnl

                            data_dynamic = []
                            for login_str, vals in agg_dynamic.items():
                                account = accounts_df[accounts_df['login'].astype(str) == login_str]
                                if not account.empty:
                                    name = account['name'].iloc[0]
                                    group = account['group'].iloc[0]
                                    usd_pnl = float(account['profit'].iloc[0]) if 'profit' in account.columns else 0.0
                                else:
                                    name = 'Unknown'
                                    group = 'Unknown'
                                    usd_pnl = 0.0
                                data_dynamic.append({
                                    'Login': login_str,
                                    'Name': name,
                                    'Group': group,
                                    'Base Symbol': 'XAUUSD',
                                    'Type': 'Buy' if vals['net_lot'] > 0 else 'Sell' if vals['net_lot'] < 0 else 'Neutral',
                                    'Net Lot': vals['net_lot'],
                                    'USD P&L': usd_pnl
                                })

                            df_dynamic = pd.DataFrame(data_dynamic)
                            table_placeholder.dataframe(df_dynamic)

                    except Exception as e:
                        st.error(f"Error scanning data for login {login}: {e}")
                        continue
                    scanned += 1
                    progress_bar.progress(scanned / total_accounts)

                combined_cache['data'] = all_combined
                combined_cache['timestamp'] = time.time()
                progress_bar.empty()
                status_text.empty()
                st.success(f"Automatic scan completed: {len(all_combined)} data entries found from {scanned} accounts")
                combined_list = all_combined  # Update local list
        else:
            st.error("No accounts found to scan")
    except Exception as e:
        st.error(f"Automatic scan failed: {e}")

    # Initial table display
    update_table()