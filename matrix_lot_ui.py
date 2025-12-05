import streamlit as st
from Matrix_lot import get_login_symbol_matrix, get_detailed_position_table, display_position_table, display_login_symbol_pivot_table

def matrix_lot_view(data):
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

    st.subheader('Login vs Symbol Matrix - Net Lot')

    # Create tabs for four views
    tab1, tab2 = st.tabs(["🎯 Pivot Matrix (Lot)", "📋 Detailed Position Table"])

    with tab1:
        st.write("Login × Symbol pivot table showing net lots at intersections.")
        try:
            with st.spinner('Loading pivot table...'):
                display_login_symbol_pivot_table(data)
        except Exception as e:
            st.error(f'Failed to display pivot table: {e}')

    with tab2:
        st.write("This view shows individual positions organized by Symbol and Login.")
        try:
            with st.spinner('Loading positions...'):
                display_position_table(data)
        except Exception as e:
            st.error(f'Failed to display positions: {e}')
