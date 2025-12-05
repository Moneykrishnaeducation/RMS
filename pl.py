import streamlit as st
import pandas as pd

def pl_view(data):
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

    st.subheader('Profit/Loss Overview')

    # Account type buttons
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("All Accounts", key="all_pl"):
            if 'pl_account_type' in st.session_state:
                del st.session_state.pl_account_type
    with col2:
        if st.button("Demo Account", key="demo_pl"):
            st.session_state.pl_account_type = "demo"
    with col3:
        if st.button("Real Account", key="real_pl"):
            st.session_state.pl_account_type = "real"

    # Filter by account type if selected
    if 'pl_account_type' in st.session_state:
        if st.session_state.pl_account_type == "demo":
            # Assuming demo accounts have 'demo' in group name, adjust logic as needed
            data = data[data['group'].str.contains('demo', case=False, na=False)]
        elif st.session_state.pl_account_type == "real":
            # Assuming real accounts don't have 'demo' in group name
            data = data[~data['group'].str.contains('demo', case=False, na=False)]

    if 'profit' in data.columns:
        # Debug: Show profit statistics
        st.write(f"Debug: Total accounts: {len(data)}, Min profit: {data['profit'].min()}, Max profit: {data['profit'].max()}, Negative profits: {(data['profit'] < 0).sum()}")

        # Sort by profit descending
        pl_data = data.sort_values('profit', ascending=False)[['login', 'name', 'group', 'profit', 'balance', 'equity']]
        st.dataframe(pl_data)

        # P/L distribution chart
        st.subheader('P/L Distribution')
        st.bar_chart(data['profit'])
    else:
        st.info('No profit/loss data available.')
