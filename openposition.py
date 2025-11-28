import pandas as pd
import streamlit as st
import time

# Import the persistent MT5Service getter from mt5_utils
from mt5_utils import get_mt5_service

def positions_details_view(data):
    st.subheader('Open Positions Details')

    # Use the persistent MT5Service instance
    svc = get_mt5_service()

    # Check if we have cached positions data
    if 'positions_data' not in st.session_state or 'positions_timestamp' not in st.session_state:
        st.session_state.positions_data = None
        st.session_state.positions_timestamp = 0

    # Refresh data if it's older than 30 seconds or doesn't exist
    current_time = time.time()
    if current_time - st.session_state.positions_timestamp > 30 or st.session_state.positions_data is None:
        with st.spinner('Checking accounts for open positions...'):
            progress_bar = st.progress(0)
            status_text = st.empty()

            all_positions = []
            total_logins = len(data['login'].unique())
            logins_list = data['login'].unique()

            for i, login in enumerate(logins_list):
                try:
                    # Update progress
                    progress = (i + 1) / total_logins
                    progress_bar.progress(progress)
                    status_text.text(f"Checking account {i+1}/{total_logins} (Login: {login})...")

                    positions = svc.get_open_positions(login)
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
                        all_positions.append(position_data)

                except Exception as e:
                    st.warning(f"Error fetching positions for login {login}: {e}")
                    continue

            # Clear progress indicators
            progress_bar.empty()
            status_text.empty()

            # Cache the results
            st.session_state.positions_data = all_positions
            st.session_state.positions_timestamp = current_time

            st.success(f"✅ Scan complete! Found {len(all_positions)} open positions across {total_logins} accounts.")
    else:
        all_positions = st.session_state.positions_data
        st.info(f"📊 Showing cached data ({len(all_positions)} positions). Click refresh to update.")

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

        # Add refresh button
        if st.button("🔄 Refresh Positions Data", key="refresh_positions"):
            st.session_state.positions_data = None
            st.session_state.positions_timestamp = 0
            st.rerun()

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
