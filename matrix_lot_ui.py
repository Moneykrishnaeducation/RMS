import streamlit as st
from Matrix_lot import display_position_table, display_login_symbol_pivot_table
from streamlit_autorefresh import st_autorefresh

def matrix_lot_view(data):
    # Auto-refresh every 5 seconds
    st_autorefresh(interval=15000, key="refresh_counter")

    st.write("This page refreshes every 15 seconds.")
    st.subheader('Login vs Symbol Matrix - Net Lot')

    # Create tabs for four views
    tab1, tab2 = st.tabs(["🎯 Pivot Matrix (Lot)", "📋 Detailed Position Table"])

    with tab1:
        st.write("Login × Symbol pivot table showing net lots at intersections.")
        try:
            display_login_symbol_pivot_table(data)
        except Exception as e:
            st.error(f'Failed to display pivot table: {e}')

    with tab2:
        st.write("This view shows individual positions organized by Symbol and Login.")
        try:
            display_position_table(data)
        except Exception as e:
            st.error(f'Failed to display positions: {e}')
