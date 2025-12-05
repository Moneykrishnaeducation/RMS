import streamlit as st
import pandas as pd

def dashboard_view(data):
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

    # Top-level KPIs
    total_accounts = len(data)
    total_balance = data.get('balance', pd.Series(0)).astype(float).sum()
    total_equity = data.get('equity', pd.Series(0)).astype(float).sum()
    total_profit = data.get('profit', pd.Series(0)).astype(float).sum()

    # Card HTML templates
    card_css = """
    <style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        margin: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        color: white;
        text-align: center;
        height: 100px;
        display: flex;
        flex-direction: column;
        justify-content: center;
        gap:0px;
    }
    .metric-title {
        margin: 0;
        font-size: 11px;
        font-weight: normal;
        opacity: 0.9;
    }
    .metric-value {
        margin: 10px 0 0 0;
        font-size: 23px;
        font-weight: bold;
    }
    </style>
    """

    card_accounts = f"""
    <div class="metric-card">
        <h3 class="metric-title">Total Accounts</h3>
        <p class="metric-value">{total_accounts}</p>
    </div>
    """

    card_balance = f"""
    <div class="metric-card">
        <h3 class="metric-title">Total Balance</h3>
        <p class="metric-value">${total_balance:,.2f}</p>
    </div>
    """

    card_equity = f"""
    <div class="metric-card">
        <h3 class="metric-title">Total Equity</h3>
        <p class="metric-value">${total_equity:,.2f}</p>
    </div>
    """

    card_profit = f"""
    <div class="metric-card">
        <h3 class="metric-title">Total P/L</h3>
        <p class="metric-value">${total_profit:,.2f}</p>
    </div>
    """

    # Display cards in two lines (rows)
    st.markdown(card_css, unsafe_allow_html=True)

    # First row: Total Accounts, Total Balance, Total Equity
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(card_accounts, unsafe_allow_html=True)
    with col2:
        st.markdown(card_balance, unsafe_allow_html=True)
    with col3:
        st.markdown(card_equity, unsafe_allow_html=True)

    # Second row: Total Profit, Top Profit Person (Real), Top Profit Person (Demo)
    if 'profit' in data.columns and 'group' in data.columns and not data.empty:
        # Separate real and demo accounts
        real_accounts = data[~data['group'].str.contains('demo', case=False, na=False)]
        demo_accounts = data[data['group'].str.contains('demo', case=False, na=False)]

        # Top profit for Real accounts
        if not real_accounts.empty:
            top_real_row = real_accounts.loc[real_accounts['profit'].astype(float).idxmax()]
            top_real_name = top_real_row.get('name', 'Unknown')
            top_real_amount = float(top_real_row.get('profit', 0))
            card_top_real = f"""
            <div class="metric-card">
                <h3 class="metric-title">Top Profit(Real)</h3>
                <p class="metric-value">{top_real_name}${top_real_amount:,.2f}</p>
            </div>
            """
        else:
            card_top_real = f"""
            <div class="metric-card">
                <h3 class="metric-title">Top Profit(Real)</h3>
                <p class="metric-value">No Data</p>
            </div>
            """

        # Top profit for Demo accounts
        if not demo_accounts.empty:
            top_demo_row = demo_accounts.loc[demo_accounts['profit'].astype(float).idxmax()]
            top_demo_name = top_demo_row.get('name', 'Unknown')
            top_demo_amount = float(top_demo_row.get('profit', 0))
            card_top_demo = f"""
            <div class="metric-card">
                <h3 class="metric-title">Top Profit (Demo)</h3>
                <p class="metric-value">{top_demo_name}${top_demo_amount:,.2f}</p>
            </div>
            """
        else:
            card_top_demo = f"""
            <div class="metric-card">
                <h3 class="metric-title">Top Profit (Demo)</h3>
                <p class="metric-value">No Data</p>
            </div>
            """

        # Second row
        col4, col5, col6 = st.columns(3)
        with col4:
            st.markdown(card_profit, unsafe_allow_html=True)
        with col5:
            st.markdown(card_top_real, unsafe_allow_html=True)
        with col6:
            st.markdown(card_top_demo, unsafe_allow_html=True)

    # Top accounts
    st.subheader('Top accounts')
    if 'equity' in data.columns:
        top_eq = data.sort_values('equity', ascending=False).head(10)[['login', 'name', 'group', 'equity']]
        st.table(top_eq)
    if 'balance' in data.columns:
        worst_bal = data.sort_values('balance', ascending=True).head(10)[['login', 'name', 'group', 'balance']]
        st.table(worst_bal)

    # Groups breakdown
    st.subheader('Groups')
    if 'group' in data.columns:
        groups = data.groupby('group').agg(count=('login', 'count'), balance_sum=('balance', 'sum'), equity_sum=('equity', 'sum'))
        groups = groups.sort_values('count', ascending=False)
        st.dataframe(groups.reset_index().rename(columns={'group': 'Group'}).head(50))
