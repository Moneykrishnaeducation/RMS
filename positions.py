import streamlit as st
import pandas as pd
import time
from MT5Service import MT5Service

def positions_view(data, positions_cache):
    # Auto-refresh every 5 seconds
    st.markdown("""
        <script>
        function autoRefreshTable() {
            setTimeout(function() {
                window.location.reload();
            }, 15000);
        }
        autoRefreshTable();
        </script>
    """, unsafe_allow_html=True)

    st.subheader('All Open Positions')

    # Use cached data from background scanner

    # Control buttons
    col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
    with col1:
        if st.button('🔄 Manual Scan', key='manual_scan'):
            st.session_state.manual_scan_trigger = True
            st.rerun()
    with col2:
        if st.button('▶️ Start Scanning', key='start_scanning'):
            positions_cache['scanning'] = True
            positions_cache['timestamp'] = 0  # Reset timestamp to force immediate scan
            from backend import save_scanning_status
            save_scanning_status({'scanning': True})  # Persist scanning status
            st.success("Background scanning started. Will begin scanning all accounts.")
            st.rerun()
    with col3:
        if st.button('⏹️ Stop Scanning', key='stop_scanning'):
            positions_cache['scanning'] = False
            from backend import save_scanning_status
            save_scanning_status({'scanning': False})  # Persist scanning status
            st.success("Background scanning stopped. Showing current data.")
            st.rerun()
    with col4:
        if positions_cache['scanning']:
            st.info("🔄 Background scanning is active")
        else:
            st.info("⏹️ Background scanning is stopped")

    # Show scanning status
    st.write(f"Debug scanning status: scanning={positions_cache['scanning']}, progress={positions_cache.get('progress', {})}")
    if positions_cache['scanning']:
        progress = positions_cache.get('progress', {})
        current = progress.get('current', 0)
        total = progress.get('total', 0)
        current_login = progress.get('current_login', '')
        if total > 0:
            progress_percentage = int((current / total) * 100)
            st.progress(progress_percentage / 100)
            st.info(f"🔄 Background position scanning in progress... {current}/{total} accounts scanned ({progress_percentage}%) - Currently scanning: {current_login}")
        else:
            st.info("🔄 Background position scanning in progress...")

        # Show table below scanning even during scan
        all_positions = positions_cache.get('data', [])
        last_scan = positions_cache.get('timestamp', 0)
        time_since_scan = time.time() - last_scan

        df = pd.DataFrame(all_positions)
        # Select only the desired columns: Login, ID, Symbol, Vol, Price, P/L, Type, Date, Name
        desired_columns = ['Login', 'ID', 'Symbol', 'Vol', 'Price', 'P/L', 'Type', 'Name']
        if not df.empty:
            available_columns = [col for col in desired_columns if col in df.columns]
            if available_columns:
                df_display = df[available_columns]
            else:
                df_display = df
        else:
            df_display = pd.DataFrame(columns=desired_columns)

        if df_display.empty:
            st.table(df_display)
            st.info('No open positions found yet.')
        else:
            st.write(f"Total positions found so far: {len(all_positions)}")
            # Pagination: 10 rows per page
            rows_per_page = 10
            total_rows = len(df_display)
            total_pages = (total_rows // rows_per_page) + (1 if total_rows % rows_per_page > 0 else 0)

            if 'positions_page' not in st.session_state:
                st.session_state.positions_page = 1

            col1, col2, col3 = st.columns([1, 2, 1])
            with col1:
                if st.button('Previous', key='prev_page_main') and st.session_state.positions_page > 1:
                    st.session_state.positions_page -= 1
            with col2:
                page = st.selectbox('Page', options=list(range(1, total_pages + 1)), index=st.session_state.positions_page - 1, key='page_select')
                st.session_state.positions_page = page
            with col3:
                if st.button('Next', key='next_page') and st.session_state.positions_page < total_pages:
                    st.session_state.positions_page += 1

            start_row = (st.session_state.positions_page - 1) * rows_per_page
            end_row = start_row + rows_per_page
            st.dataframe(df_display.iloc[start_row:end_row])

        time.sleep(1)  # Brief pause to allow thread updates
        if positions_cache['scanning']:
            st.rerun()
    elif st.session_state.get('manual_scan_trigger', False):
        st.session_state.manual_scan_trigger = False
        # Trigger manual scan
        try:
            st.info("🔄 Starting manual position scan...")
            svc = MT5Service()
            accounts = svc.list_accounts_by_groups()
            if not accounts:
                accounts = svc.list_accounts_by_range(start=1, end=100000)

            if accounts:
                accounts_df = pd.json_normalize(accounts)
                if 'login' in accounts_df.columns:
                    accounts_df['login'] = accounts_df['login'].astype(str)

                    all_positions = []
                    for login in accounts_df['login'].unique()[:10]:  # Test with first 10 accounts only
                        try:
                            positions = svc.get_open_positions(login)
                            if positions:
                                for p in positions:
                                    position_data = {
                                        'Login': login,
                                        'ID': p.get('id'),
                                        'Symbol': p.get('symbol'),
                                        'Vol': p.get('volume'),
                                        'Price': p.get('price'),
                                        'P/L': p.get('profit'),
                                        'Type': p.get('type'),
                                        'Date': p.get('date')
                                    }
                                    # Add account details
                                    account_row = accounts_df[accounts_df['login'] == login]
                                    if not account_row.empty:
                                        position_data['Name'] = account_row['name'].iloc[0] if 'name' in account_row.columns else ''
                                        position_data['Email'] = account_row['email'].iloc[0] if 'email' in account_row.columns else ''
                                        position_data['Group'] = account_row['group'].iloc[0] if 'group' in account_row.columns else ''
                                    all_positions.append(position_data)
                        except Exception as e:
                            st.error(f"Error scanning positions for login {login}: {e}")
                            continue

                    positions_cache['data'] = all_positions
                    positions_cache['timestamp'] = time.time()
                    from backend import save_positions_cache
                    save_positions_cache(positions_cache)  # Persist cache to file
                    st.success(f"Manual scan completed: {len(all_positions)} positions found from 10 test accounts")
            else:
                st.error("No accounts found to scan")
        except Exception as e:
            st.error(f"Manual scan failed: {e}")

    # Get positions from cache
    all_positions = positions_cache.get('data', [])
    last_scan = positions_cache.get('timestamp', 0)
    time_since_scan = time.time() - last_scan

    # Debug info
    st.write(f"Debug: positions_cache scanning={positions_cache.get('scanning', False)}, data length={len(all_positions) if all_positions else 0}, last_scan={last_scan}, time_since_scan={int(time_since_scan)}")

    if all_positions:
        st.write(f"Total positions found: {len(all_positions)}")
        st.write(f"Last updated: {int(time_since_scan)} seconds ago")

    df = pd.DataFrame(all_positions)
    # Select only the desired columns: Login, ID, Symbol, Vol, Price, P/L, Type, Date, Name
    desired_columns = ['Login', 'ID', 'Symbol', 'Vol', 'Price', 'P/L', 'Type', 'Date', 'Name']
    available_columns = [col for col in desired_columns if col in df.columns]
    if available_columns:
        df_display = df[available_columns]
    else:
        df_display = df

    if df_display.empty:
        st.dataframe(df_display)
        if time_since_scan > 60:
            st.warning("No cached position data available. Background scanner may not be running or has encountered errors.")
        else:
            st.info('No open positions found.')
    else:
        # Pagination: 10 rows per page
        rows_per_page = 10
        total_rows = len(df_display)
        total_pages = (total_rows // rows_per_page) + (1 if total_rows % rows_per_page > 0 else 0)

        if 'positions_page' not in st.session_state:
            st.session_state.positions_page = 1

        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button('Previous', key='prev_page_final') and st.session_state.positions_page > 1:
                st.session_state.positions_page -= 1
        with col2:
            page = st.selectbox('Page', options=list(range(1, total_pages + 1)), index=st.session_state.positions_page - 1, key='page_select')
            st.session_state.positions_page = page
        with col3:
            if st.button('Next', key='next_page') and st.session_state.positions_page < total_pages:
                st.session_state.positions_page += 1

        start_row = (st.session_state.positions_page - 1) * rows_per_page
        end_row = start_row + rows_per_page
        st.dataframe(df_display.iloc[start_row:end_row])
