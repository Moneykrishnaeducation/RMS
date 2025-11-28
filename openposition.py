import pandas as pd
import streamlit as st

from MT5Service import MT5Service

def positions_details_view(data):
    st.subheader('Open Positions Details')
    svc = MT5Service()
    all_positions = []
    total_logins = len(data['login'].unique())
    st.write(f"Checking {total_logins} accounts for open positions...")
    for login in data['login'].unique():
        try:
            positions = svc.get_open_positions(login)
            for p in positions:
                # Map the keys to match the display columns: ID, Symbol, Vol, Price, P/L
                position_data = {
                    'ID': p.get('id'),
                    'Symbol': p.get('symbol'),
                    'Vol': p.get('volume'),
                    'Price': p.get('price'),
                    'P/L': p.get('profit')
                }
                all_positions.append(position_data)
        except Exception as e:
            st.write(f"Error fetching positions for login {login}: {e}")
            continue
    st.write(f"Total positions found: {len(all_positions)}")
    if all_positions:
        df = pd.DataFrame(all_positions)
        # Select only the desired columns: ID, Symbol, Vol, Price, P/L
        desired_columns = ['ID', 'Symbol', 'Vol', 'Price', 'P/L']
        available_columns = [col for col in desired_columns if col in df.columns]
        if available_columns:
            df_display = df[available_columns]
        else:
            df_display = df

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
    else:
        st.info('No open positions found.')
