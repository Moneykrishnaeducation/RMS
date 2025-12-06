import streamlit as st
import pandas as pd
import io
from pnl_matrix import get_login_symbol_pnl_matrix
from streamlit_autorefresh import st_autorefresh

def  usd_matrix_view(data):
    st_autorefresh(interval=15000, key="refresh_counter")

    st.write("This page refreshes every 15 seconds.")

    st.subheader('Login vs Symbol Matrix - USD P&L')
    st.write("This matrix shows the total USD P&L for each login across specified symbols from open positions.")

    if data.empty:
        st.info('No account data available.')
        return

    try:
        # Prepare data dictionary with accounts_df and positions_cache
        matrix_data = {
            'accounts_df': data,
            'positions_cache': st.session_state.positions_cache
        }
        matrix_df = get_login_symbol_pnl_matrix(matrix_data)

        if matrix_df.empty:
            st.info('No open positions found for the accounts.')
        else:
            # Display metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Logins", len(matrix_df) - (1 if "All Login" in matrix_df.index else 0))
            with col2:
                st.metric("Total Symbols", len(matrix_df.columns))
            with col3:
                total_pnl = matrix_df.loc["All Login"].sum() if "All Login" in matrix_df.index else matrix_df.sum().sum()
                st.metric("Total USD P&L (All Login)", f"${total_pnl:,.2f}")

            st.dataframe(matrix_df, width='stretch', height=500)

            # Export to CSV
            buf = io.StringIO()
            matrix_df.to_csv(buf, index=False)
            st.download_button('📥 Download Matrix CSV', data=buf.getvalue(), file_name='usd_pnl_matrix.csv', mime='text/csv')

    except Exception as e:
        st.error(f'Failed to generate matrix: {e}')
