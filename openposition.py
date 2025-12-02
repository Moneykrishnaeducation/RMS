import pandas as pd
import streamlit as st
import time

# Import the persistent MT5Service getter from mt5_utils
from mt5_utils import get_mt5_service

def positions_details_view(data):
    st.subheader('Open Positions Details')

    # Use the persistent MT5Service instance
    svc = get_mt5_service()

    # Initialize session state for progressive scanning
    if 'scanning_in_progress' not in st.session_state:
        st.session_state.scanning_in_progress = False
    if 'current_index' not in st.session_state:
        st.session_state.current_index = 0
    if 'all_positions' not in st.session_state:
        st.session_state.all_positions = []
    if 'logins_list' not in st.session_state:
        st.session_state.logins_list = []
    if 'all_positions_dict' not in st.session_state:
        st.session_state.all_positions_dict = {}

    # Check if we have cached positions data
    if 'positions_data' not in st.session_state or 'positions_timestamp' not in st.session_state:
        st.session_state.positions_data = None
        st.session_state.positions_timestamp = 0

    # Refresh button
    if st.button("🔄 Refresh Positions Data", key="refresh_positions"):
        st.session_state.scanning_in_progress = True
        if not st.session_state.logins_list:
            st.session_state.logins_list = data['login'].unique().tolist()
        st.session_state.positions_data = None
        st.session_state.positions_timestamp = 0
        st.rerun()

    # Continuous scanning logic
    if st.session_state.scanning_in_progress:
        if not st.session_state.logins_list:
            st.session_state.logins_list = data['login'].unique().tolist()

        login = st.session_state.logins_list[st.session_state.current_index]
        try:
            st.info(f"🔄 Continuous scanning: account {st.session_state.current_index + 1}/{len(st.session_state.logins_list)} (Login: {login})...")
            positions = svc.get_open_positions(login)
            # Update positions for this login
            st.session_state.all_positions_dict[login] = []
            for p in positions:
                # Map the keys to match the display columns: ID, Symbol, Vol, Price, P/L
                position_data = {
                    'Login': login,  # Add login for reference
                    'ID': p.get('id'),
                    'Symbol': p.get('symbol'),
                    'Vol': p.get('volume'),
                    'Price': p.get('price'),
                    'P/L': p.get('profit'),
                    'Type': p.get('type')
                }
                st.session_state.all_positions_dict[login].append(position_data)
        except Exception as e:
            st.warning(f"Error fetching positions for login {login}: {e}")

        # Flatten all_positions from dict
        st.session_state.all_positions = []
        for login_positions in st.session_state.all_positions_dict.values():
            st.session_state.all_positions.extend(login_positions)

        st.session_state.current_index += 1
        if st.session_state.current_index >= len(st.session_state.logins_list):
            st.session_state.current_index = 0  # Loop back to start

        st.rerun()  # Rerun to update the display progressively

    # Display current positions (either from cache or progressive scan)
    if st.session_state.positions_data is not None:
        all_positions = st.session_state.positions_data
        st.info(f"📊 Showing cached data ({len(all_positions)} positions). Click refresh to update.")
    else:
        all_positions = st.session_state.all_positions
        if st.session_state.scanning_in_progress:
            st.info(f"📊 Showing partial data ({len(all_positions)} positions so far). Scanning in progress...")
        else:
            st.info(f"📊 Showing data ({len(all_positions)} positions).")

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
