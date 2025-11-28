import os
import io
import json
import pandas as pd
import streamlit as st
import time

from MT5Service import MT5Service
from accounts import accounts_view
from profile import profile_view
    
# Custom CSS for attractive navigation bar
nav_css = """
<style>
.nav-container {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 10px 20px;
    border-radius: 10px;
    margin-bottom: 20px;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}
.nav-button {
    background: rgba(255, 255, 255, 0.1);
    border: none;
    color: white;
    padding: 10px 20px;
    margin: 0 5px;
    border-radius: 5px;
    cursor: pointer;
    font-size: 16px;
    transition: all 0.3s ease;
}
.nav-button:hover {
    background: rgba(255, 255, 255, 0.2);
    transform: translateY(-2px);
}
.nav-button.active {
    background: rgba(255, 255, 255, 0.3);
    font-weight: bold;
}
.nav-icon {
    margin-right: 8px;
}
</style>
"""

def render_nav():
    st.markdown(nav_css, unsafe_allow_html=True)
    st.markdown('<div class="nav-container">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🏠 Dashboard", key="nav_dashboard"):
            st.session_state.page = "dashboard"
    with col2:
        if st.button("👥 Accounts", key="nav_accounts"):
            st.session_state.page = "accounts"
    with col3:
        if st.button("📊 Reports", key="nav_reports"):
            st.session_state.page = "reports"
    st.markdown('</div>', unsafe_allow_html=True)

def dashboard_view(data):
    # Top-level KPIs
    total_accounts = len(data)
    total_balance = data.get('balance', pd.Series(0)).astype(float).sum()
    total_equity = data.get('equity', pd.Series(0)).astype(float).sum()

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
        height: 120px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .metric-title {
        margin: 0;
        font-size: 16px;
        font-weight: normal;
        opacity: 0.9;
    }
    .metric-value {
        margin: 10px 0 0 0;
        font-size: 28px;
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

    # Display cards in columns
    st.markdown(card_css, unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(card_accounts, unsafe_allow_html=True)
    with col2:
        st.markdown(card_balance, unsafe_allow_html=True)
    with col3:
        st.markdown(card_equity, unsafe_allow_html=True)

    # Top profit person for Real and Demo accounts
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
                <h3 class="metric-title">Top Profit Person (Real)</h3>
                <p class="metric-value">{top_real_name}<br/>${top_real_amount:,.2f}</p>
            </div>
            """

        # Top profit for Demo accounts
        if not demo_accounts.empty:
            top_demo_row = demo_accounts.loc[demo_accounts['profit'].astype(float).idxmax()]
            top_demo_name = top_demo_row.get('name', 'Unknown')
            top_demo_amount = float(top_demo_row.get('profit', 0))
            card_top_demo = f"""
            <div class="metric-card">
                <h3 class="metric-title">Top Profit Person (Demo)</h3>
                <p class="metric-value">{top_demo_name}<br/>${top_demo_amount:,.2f}</p>
            </div>
            """

        # Display additional cards in columns
        col4, col5 = st.columns(2)
        if not real_accounts.empty:
            with col4:
                st.markdown(card_top_real, unsafe_allow_html=True)
        if not demo_accounts.empty:
            with col5:
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



def reports_view(data):
    st.subheader('Reports')
    # Add some report elements, e.g., tables and charts
    if 'group' in data.columns:
        groups = data.groupby('group').agg(count=('login', 'count'), balance_sum=('balance', 'sum'), equity_sum=('equity', 'sum'))
        groups = groups.sort_values('count', ascending=False)
        st.dataframe(groups.reset_index().rename(columns={'group': 'Group'}).head(20))
        st.bar_chart(groups['count'].head(20))

    # Export filtered results
    buf = io.StringIO()
    data.to_csv(buf, index=False)
    st.download_button('Download CSV', data=buf.getvalue(), file_name='accounts.csv', mime='text/csv')

def positions_view(data):
    st.subheader('All Open Positions')
    svc = MT5Service()
    all_positions = []
    for login in data['login'].unique():
        try:
            positions = svc.get_open_positions(login)
            for p in positions:
                p['login'] = login
                # Add account details
                account_row = data[data['login'] == login]
                if not account_row.empty:
                    p['name'] = account_row['name'].iloc[0] if 'name' in account_row.columns else ''
                    p['email'] = account_row['email'].iloc[0] if 'email' in account_row.columns else ''
                    p['group'] = account_row['group'].iloc[0] if 'group' in account_row.columns else ''
                all_positions.append(p)
        except Exception:
            continue
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

        if 'positions_page' not in st.session_state:
            st.session_state.positions_page = 1

        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button('Previous', key='prev_page') and st.session_state.positions_page > 1:
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
    else:
        st.info('No open positions.')

def pl_view(data):
    st.subheader('Profit/Loss Overview')

    # Account type buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Demo Account", key="demo_pl"):
            st.session_state.pl_account_type = "demo"
    with col2:
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
        # Create separate Profit and Loss columns
        data_copy = data.copy()
        data_copy['Profit'] = data_copy['profit'].apply(lambda x: x if x > 0 else 0)
        data_copy['Loss'] = data_copy['profit'].apply(lambda x: x if x < 0 else 0)

        # Sort by profit descending
        pl_data = data_copy.sort_values('profit', ascending=False)[['login', 'name', 'group', 'Profit', 'Loss', 'balance', 'equity']]
        st.dataframe(pl_data.head(50))

        # P/L distribution chart
        st.subheader('P/L Distribution')
        st.bar_chart(data['profit'].head(50))
    else:
        st.info('No profit/loss data available.')

@st.cache_data(ttl=5)
def load_from_mt5(use_groups=True):
    """Fetch accounts from MT5 using MT5Service. Cached for 5 seconds by default."""
    svc = MT5Service()
    if use_groups:
        accounts = svc.list_accounts_by_groups()
    else:
        # Fallback to index-based if desired
        accounts = svc.list_accounts_by_index()
    if not accounts:
        return pd.DataFrame()
    return pd.json_normalize(accounts)


def main():
    st.set_page_config(page_title='RMS - Accounts', layout='wide')
    st.title('RMS — Accounts Dashboard (Streamlit)')

    # Auto refresh every 5 seconds
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = time.time()

    if time.time() - st.session_state.last_refresh > 5:
        st.session_state.last_refresh = time.time()
        st.rerun()

    # Initialize session state for page
    if 'page' not in st.session_state:
        st.session_state.page = 'dashboard'

    # Sidebar navigation
    st.sidebar.header('Navigation')
    if st.sidebar.button("🏠 Dashboard", key="nav_dashboard"):
        st.session_state.page = "dashboard"
    if st.sidebar.button("👥 Accounts", key="nav_accounts"):
        st.session_state.page = "accounts"
    if st.sidebar.button("👤 Profile", key="nav_profile"):
        st.session_state.page = "profile"
    if st.sidebar.button("📊 Reports", key="nav_reports"):
        st.session_state.page = "reports"
    if st.sidebar.button("📈 Open Positions", key="nav_positions"):
        st.session_state.page = "positions"
    if st.sidebar.button("💰 P/L", key="nav_pl"):
        st.session_state.page = "pl"

    st.sidebar.header('Data source')
    st.sidebar.write('Loading accounts directly from MT5 Manager using `.env` credentials')
    data = pd.DataFrame()
    col1, col2 = st.sidebar.columns([3,1])
    with col1:
        use_groups = st.checkbox('Enumerate by groups (recommended)', value=True)
    with col2:
        refresh = st.button('Refresh')

    try:
        if refresh:
            # clear cache and re-fetch
            load_from_mt5.clear()
        with st.spinner('Loading accounts from MT5...'):
            data = load_from_mt5(use_groups)
    except Exception as e:
        st.error(f'Error loading from MT5: {e}')
        data = pd.DataFrame()

    if data.empty:
        st.info('No account data available.')
        return

    # Normalize columns and types
    if 'login' in data.columns:
        try:
            data['login'] = data['login'].astype(str)
        except Exception:
            pass

    # Sidebar filters for accounts
    if st.session_state.page == 'accounts':
        st.sidebar.header('Filters')
        login_search = st.sidebar.text_input('Search login', key='login_search')
        if 'name' in data.columns:
            names_list = sorted(data['name'].dropna().unique().tolist())
            name_filter = st.sidebar.multiselect('Filter names', names_list, max_selections=10, key='name_filter')
        if 'group' in data.columns:
            groups_list = sorted(data['group'].dropna().unique().tolist())
            group_filter = st.sidebar.multiselect('Filter groups', groups_list, max_selections=5, key='group_filter')
        if 'email' in data.columns:
            emails_list = sorted(data['email'].dropna().unique().tolist())
            email_filter = st.sidebar.multiselect('Filter emails', emails_list, max_selections=10, key='email_filter')
        if 'leverage' in data.columns:
            leverages_list = sorted(data['leverage'].dropna().unique().tolist())
            leverage_filter = st.sidebar.multiselect('Filter leverages', leverages_list, max_selections=5, key='leverage_filter')
        min_balance = st.sidebar.number_input('Min balance', value=float(data['balance'].min() if 'balance' in data.columns else 0.0), key='min_balance')
        max_balance = st.sidebar.number_input('Max balance', value=float(data['balance'].max() if 'balance' in data.columns else 0.0), key='max_balance')
        if 'profit' in data.columns:
            min_pl = st.sidebar.number_input('Min P/L', value=float(data['profit'].min() if 'profit' in data.columns else 0.0), key='min_pl')
            max_pl = st.sidebar.number_input('Max P/L', value=float(data['profit'].max() if 'profit' in data.columns else 0.0), key='max_pl')

    # Display the selected page
    if st.session_state.page == 'dashboard':
        dashboard_view(data)
    elif st.session_state.page == 'accounts':
        accounts_view(data)
    elif st.session_state.page == 'profile':
        profile_view()
    elif st.session_state.page == 'reports':
        reports_view(data)
    elif st.session_state.page == 'positions':
        positions_view(data)
    elif st.session_state.page == 'pl':
        pl_view(data)


if __name__ == '__main__':
    main()
