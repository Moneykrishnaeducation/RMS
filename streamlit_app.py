import os
import io
import json
import pandas as pd
import streamlit as st
import time
import threading

from MT5Service import MT5Service
from accounts import accounts_view
from profile import profile_view
from filter_search import filter_search_view      # ⭐ NEW IMPORT
from openposition import positions_details_view   # ⭐ NEW IMPORT
from Matrix_lot import get_net_lot_matrix        # ⭐ NEW IMPORT


# Initialize session state for caches (persistent across reruns)
if 'positions_cache' not in st.session_state:
    st.session_state.positions_cache = {
        'data': None,
        'timestamp': 0,
        'scanning': False,
        'progress': {'current': 0, 'total': 0}
    }

if 'accounts_cache' not in st.session_state:
    st.session_state.accounts_cache = {
        'timestamp': 0,
        'scanning': False
    }

# For backward compatibility, create references
positions_cache = st.session_state.positions_cache
accounts_cache = st.session_state.accounts_cache
    
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
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        if st.button("🏠 Dashboard", key="nav_dashboard"):
            st.session_state.page = "dashboard"
    with col2:
        if st.button("👥 Accounts", key="nav_accounts"):
            st.session_state.page = "accounts"
    with col3:
        if st.button("📊 Reports", key="nav_reports"):
            st.session_state.page = "reports"
    with col4:
        if st.button("🔍 Filter Search", key="nav_filter_search_top"):   # ⭐ NEW BUTTON
            st.session_state.page = "filter_search"
    with col5:
        if st.button("👥 Groups", key="nav_groups_top"):
            st.session_state.page = "groups"
    st.markdown('</div>', unsafe_allow_html=True)

def dashboard_view(data):
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
        <h3 class="metric-title">Total Profit</h3>
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

    # Use cached data from background scanner
    global positions_cache

    # Manual scan trigger
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button('🔄 Manual Scan', key='manual_scan'):
            st.session_state.manual_scan_trigger = True
            st.rerun()

    # Show scanning status
    st.write(f"Debug scanning status: scanning={positions_cache['scanning']}, progress={positions_cache.get('progress', {})}")
    if positions_cache['scanning']:
        progress = positions_cache.get('progress', {})
        current = progress.get('current', 0)
        total = progress.get('total', 0)
        current_login = progress.get('current_login', '')
        if total > 0:
            progress_percentage = int((current / total) * 100)
            st.progress(progress_percentage / 100)
            st.info(f"🔄 Background position scanning in progress... {current}/{total} accounts scanned ({progress_percentage}%) - Currently scanning: {current_login}")
        else:
            st.info("🔄 Background position scanning in progress...")
        time.sleep(2)  # Brief pause to allow thread updates
        if positions_cache['scanning']:
            st.rerun()
    elif st.session_state.get('manual_scan_trigger', False):
        st.session_state.manual_scan_trigger = False
        # Trigger manual scan
        try:
            st.info("🔄 Starting manual position scan...")
            svc = MT5Service()
            accounts = svc.list_accounts_by_groups()
            if not accounts:
                accounts = svc.list_accounts_by_range(start=1, end=100000)

            if accounts:
                accounts_df = pd.json_normalize(accounts)
                if 'login' in accounts_df.columns:
                    accounts_df['login'] = accounts_df['login'].astype(str)

                    all_positions = []
                    for login in accounts_df['login'].unique()[:10]:  # Test with first 10 accounts only
                        try:
                            positions = svc.get_open_positions(login)
                            if positions:
                                for p in positions:
                                    position_data = {
                                        'Login': login,
                                        'ID': p.get('id'),
                                        'Symbol': p.get('symbol'),
                                        'Vol': p.get('volume'),
                                        'Price': p.get('price'),
                                        'P/L': p.get('profit'),
                                        'Type': p.get('type'),
                                        'Date': p.get('date')
                                    }
                                    # Add account details
                                    account_row = accounts_df[accounts_df['login'] == login]
                                    if not account_row.empty:
                                        position_data['Name'] = account_row['name'].iloc[0] if 'name' in account_row.columns else ''
                                        position_data['Email'] = account_row['email'].iloc[0] if 'email' in account_row.columns else ''
                                        position_data['Group'] = account_row['group'].iloc[0] if 'group' in account_row.columns else ''
                                    all_positions.append(position_data)
                        except Exception as e:
                            st.error(f"Error scanning positions for login {login}: {e}")
                            continue

                    positions_cache['data'] = all_positions
                    positions_cache['timestamp'] = time.time()
                    st.success(f"Manual scan completed: {len(all_positions)} positions found from 10 test accounts")
            else:
                st.error("No accounts found to scan")
        except Exception as e:
            st.error(f"Manual scan failed: {e}")

    # Get positions from cache
    all_positions = positions_cache.get('data', [])
    last_scan = positions_cache.get('timestamp', 0)
    time_since_scan = time.time() - last_scan

    # Debug info
    st.write(f"Debug: positions_cache scanning={positions_cache.get('scanning', False)}, data length={len(all_positions) if all_positions else 0}, last_scan={last_scan}, time_since_scan={int(time_since_scan)}")

    if all_positions:
        st.write(f"Total positions found: {len(all_positions)}")
        st.write(f"Last updated: {int(time_since_scan)} seconds ago")

        df = pd.DataFrame(all_positions)
        # Select only the desired columns: Login, ID, Symbol, Vol, Price, P/L, Type, Date, Name, Group
        desired_columns = ['Login', 'ID', 'Symbol', 'Vol', 'Price', 'P/L', 'Type', 'Date', 'Name', 'Group']
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
        if time_since_scan > 60:
            st.warning("No cached position data available. Background scanner may not be running or has encountered errors.")
        else:
            st.info('No open positions found.')



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

def groups_view(data):
    st.subheader('Groups Overview')

    if 'group' in data.columns:
        # Get unique groups
        groups_list = sorted(data['group'].dropna().unique().tolist())

        if groups_list:
            # Select group
            selected_group = st.selectbox('Select a group to view its data', groups_list, key='selected_group')

            # Filter data by selected group
            filtered_data = data[data['group'] == selected_group]

            # Display group summary
            st.write(f"**Group:** {selected_group}")
            st.write(f"**Total Accounts:** {len(filtered_data)}")

            # Display filtered dataframe
            st.dataframe(filtered_data)
        else:
            st.info('No groups available.')
    else:
        st.info('No group data available.')

def background_position_scanner():
    """Background thread function to continuously scan open positions"""

    print("Background position scanner thread started!")
    while True:
        try:
            # Check if we need to scan (every 30 seconds)
            current_time = time.time()
            if current_time - positions_cache['timestamp'] > 30:
                positions_cache['scanning'] = True
                print(f"Starting background position scan at {time.strftime('%H:%M:%S')}")

                # Load accounts data
                svc = MT5Service()
                accounts = svc.list_accounts_by_groups()
                if not accounts:
                    print("No accounts from groups, trying range scan...")
                    accounts = svc.list_accounts_by_range(start=1, end=100000)

                if accounts:
                    print(f"Found {len(accounts)} accounts to scan")
                    accounts_df = pd.json_normalize(accounts)
                    if 'login' in accounts_df.columns:
                        accounts_df['login'] = accounts_df['login'].astype(str)

                        # Initialize progress
                        total_accounts = len(accounts_df['login'].unique())
                        positions_cache['progress']['total'] = total_accounts
                        positions_cache['progress']['current'] = 0
                        positions_cache['progress']['current_login'] = ''

                        # Scan positions for all accounts
                        all_positions = []
                        scanned_count = 0
                        for login in accounts_df['login'].unique():
                            try:
                                positions_cache['progress']['current_login'] = login
                                positions = svc.get_open_positions(login)
                                if positions:
                                    for p in positions:
                                        position_data = {
                                            'Login': login,
                                            'ID': p.get('id'),
                                            'Symbol': p.get('symbol'),
                                            'Vol': p.get('volume'),
                                            'Price': p.get('price'),
                                            'P/L': p.get('profit'),
                                            'Type': p.get('type'),
                                            'Date': p.get('date')
                                        }
                                        # Add account details
                                        account_row = accounts_df[accounts_df['login'] == login]
                                        if not account_row.empty:
                                            position_data['Name'] = account_row['name'].iloc[0] if 'name' in account_row.columns else ''
                                            position_data['Email'] = account_row['email'].iloc[0] if 'email' in account_row.columns else ''
                                            position_data['Group'] = account_row['group'].iloc[0] if 'group' in account_row.columns else ''
                                        all_positions.append(position_data)
                                scanned_count += 1
                                positions_cache['progress']['current'] = scanned_count
                                if scanned_count % 100 == 0:
                                    print(f"Scanned {scanned_count}/{total_accounts} accounts, found {len(all_positions)} positions so far")
                            except Exception as e:
                                print(f"Error scanning positions for login {login}: {e}")
                                continue

                        # Update cache
                        positions_cache['data'] = all_positions
                        positions_cache['timestamp'] = current_time
                        print(f"Background scan completed: {len(all_positions)} positions found from {scanned_count} accounts")

                else:
                    print("No accounts found to scan")

                positions_cache['scanning'] = False

        except Exception as e:
            print(f"Error in background position scanner: {e}")
            positions_cache['scanning'] = False

        # Sleep for 10 seconds before next check
        time.sleep(10)

def matrix_lot_view(data):
    st.subheader('Login vs Symbol Matrix - Net Lot')
    st.write("This matrix shows the net lot (buy volume - sell volume) for each login across specified symbols.")
        
    if data.empty:
        st.info('No account data available.')
        return

    try:
        with st.spinner('Generating net lot matrix...'):
            matrix_df = get_net_lot_matrix(data)

        if matrix_df.empty:
            st.info('No open positions found for the accounts.')
        else:
            st.dataframe(matrix_df)

            # Export to CSV
            buf = io.StringIO()
            matrix_df.to_csv(buf, index=False)
            st.download_button('Download Matrix CSV', data=buf.getvalue(), file_name='net_lot_matrix.csv', mime='text/csv')

    except Exception as e:
        st.error(f'Failed to generate matrix: {e}')

@st.cache_data(ttl=5)
def load_from_mt5(use_groups=True):
    """Fetch accounts from MT5 using MT5Service. Cached for 5 seconds by default."""
    svc = MT5Service()
    if use_groups:
        accounts = svc.list_accounts_by_groups()
    else:
        # Fallback to range-based scan for more complete enumeration
        accounts = svc.list_accounts_by_range(start=1, end=100000)
    if not accounts:
        return pd.DataFrame()
    return pd.json_normalize(accounts)


def main():
    # Start background position scanner thread (only once)
    if 'scanner_thread' not in st.session_state or not st.session_state.scanner_thread.is_alive():
        st.session_state.scanner_thread = threading.Thread(target=background_position_scanner, daemon=True)
        st.session_state.scanner_thread.start()

    st.set_page_config(page_title='RMS - Accounts', layout='wide')
    st.title('RMS — Accounts Dashboard (Streamlit)')

    # Auto refresh every 5 seconds, or every 1 second if scanning
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = time.time()

    refresh_interval = 1 if positions_cache.get('scanning', False) else 5
    if time.time() - st.session_state.last_refresh > refresh_interval:
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
    if st.sidebar.button("📊 Positions Details", key="nav_positions_details"):
        st.session_state.page = "positions_details"
    if st.sidebar.button("💰 P/L", key="nav_pl"):
        st.session_state.page = "pl"
    if st.sidebar.button("🔍 Filter Search"):   # ⭐ NEW SIDEBAR BUTTON
        st.session_state.page = "filter_search"
    if st.sidebar.button("👥 Groups", key="nav_groups"):
        st.session_state.page = "groups"
    if st.sidebar.button("📊 Matrix Lot", key="nav_matrix_lot"):
        st.session_state.page = "matrix_lot"


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
        accounts_cache['scanning'] = True
        with st.spinner('Loading accounts from MT5...'):
            data = load_from_mt5(use_groups)
        accounts_cache['scanning'] = False
        accounts_cache['timestamp'] = time.time()
    except Exception as e:
        st.error(f'Error loading from MT5: {e}')
        data = pd.DataFrame()
        accounts_cache['scanning'] = False

    if data.empty:
        st.info('No account data available.')
        return

    # Debug: Show total accounts loaded
    st.sidebar.write(f"Total accounts loaded: {len(data)}")

    # Global scanning status indicator
    if positions_cache['scanning']:
        progress = positions_cache.get('progress', {})
        current = progress.get('current', 0)
        total = progress.get('total', 0)
        current_login = progress.get('current_login', '')
        if total > 0:
            progress_percentage = int((current / total) * 100)
            st.sidebar.progress(progress_percentage / 100)
            st.sidebar.info(f"🔄 Background position scanning: {current}/{total} ({progress_percentage}%) - Scanning: {current_login}")
        else:
            st.sidebar.info("🔄 Background position scanning in progress...")

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
        accounts_view(data, accounts_cache)
    elif st.session_state.page == 'profile':
        profile_view()
    elif st.session_state.page == 'reports':
        reports_view(data)
    elif st.session_state.page == 'positions':
        positions_view(data)
    elif st.session_state.page == 'positions_details':
        positions_details_view(data, positions_cache)
    elif st.session_state.page == 'pl':
        pl_view(data)
    elif st.session_state.page == 'filter_search':   # ⭐ NEW PAGE
        filter_search_view(data)
    elif st.session_state.page == 'groups':
        groups_view(data)
    elif st.session_state.page == 'matrix_lot':
        matrix_lot_view(data)

if __name__ == '__main__':
    main()
