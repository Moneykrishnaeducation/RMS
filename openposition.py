import pandas as pd
import streamlit as st
import time

# Import the persistent MT5Service getter from mt5_utils
from mt5_utils import get_mt5_service

def positions_details_view(data, positions_cache):
    st.subheader('Open Positions Details')

    # Use cached data from background scanner

    # Show scanning status
    if positions_cache['scanning']:
        st.info("🔄 Background position scanning in progress...")

    # Get positions from cache
    all_positions = positions_cache.get('data', [])
    last_scan = positions_cache.get('timestamp', 0)
    time_since_scan = time.time() - last_scan

    # Show account count that was scanned
    total_accounts_scanned = len(data['login'].unique()) if not data.empty and 'login' in data.columns else 0

    if all_positions:
        st.write(f"Total positions found: {len(all_positions)} across {total_accounts_scanned} accounts")
        st.write(f"Last updated: {int(time_since_scan)} seconds ago")
    else:
        if time_since_scan > 60:
            st.warning(f"No cached position data available. Background scanner may not be running or has encountered errors. (Scanned {total_accounts_scanned} accounts)")
        else:
            st.info(f'No open positions found from background scan. (Checked {total_accounts_scanned} accounts)')

    # Create DataFrame
    df = pd.DataFrame(all_positions)

    # Select only the desired columns: Login, ID, Symbol, Vol, Price, P/L, Type
    desired_columns = ['Login', 'ID', 'Symbol', 'Vol', 'Price', 'P/L', 'Type']
    available_columns = [col for col in desired_columns if col in df.columns]
    if available_columns:
        df_display = df[available_columns]
    else:
        # If no data, create empty DataFrame with desired columns
        df_display = pd.DataFrame(columns=desired_columns)

    if df_display.empty:
        st.dataframe(df_display)
        st.info('No open positions found.')
    else:
        # Add summary statistics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Positions", len(df_display))
        with col2:
            total_pl = df_display['P/L'].sum() if 'P/L' in df_display.columns else 0
            st.metric("Total P/L", f"${total_pl:,.2f}")
        with col3:
            unique_accounts = df_display['Login'].nunique() if 'Login' in df_display.columns else 0
            st.metric("Accounts with Positions", unique_accounts)

        # Note: Refresh is handled by background scanner

        # Pagination: 10 rows per page
        rows_per_page = 10
        total_rows = len(df_display)
        total_pages = (total_rows // rows_per_page) + (1 if total_rows % rows_per_page > 0 else 0)

        if 'positions_details_page' not in st.session_state:
            st.session_state.positions_details_page = 1

        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button('Previous', key='prev_details_page') and st.session_state.positions_details_page > 1:
                st.session_state.positions_details_page -= 1
        with col2:
            page = st.selectbox('Page', options=list(range(1, total_pages + 1)), index=st.session_state.positions_details_page - 1, key='page_details_select')
            st.session_state.positions_details_page = page
        with col3:
            if st.button('Next', key='next_details_page') and st.session_state.positions_details_page < total_pages:
                st.session_state.positions_details_page += 1

        start_row = (st.session_state.positions_details_page - 1) * rows_per_page
        end_row = start_row + rows_per_page
        st.dataframe(df_display.iloc[start_row:end_row])
