import os
import io
import json
import pandas as pd
import streamlit as st
import time
import threading
import concurrent.futures
from pnl_matrix import get_login_symbol_pnl_matrix
from MT5Service import MT5Service
from accounts import accounts_view
from profile import profile_view
from filter_search import filter_search_view      # ⭐ NEW IMPORT
from openposition import positions_details_view   # ⭐ NEW IMPORT
from Matrix_lot import get_login_symbol_matrix,get_detailed_position_table,display_position_table,display_login_symbol_pivot_table          # ⭐ NEW IMPORT
from net_lot import display_net_lot_view          # ⭐ NEW IMPORT
from trend import display_trend_view              # ⭐ NEW IMPORT
from XAUUSD import get_xauusd_data
from groupdashboard import groupdashboard_view
from file_management import file_management_view  # ⭐ NEW IMPORT
from watch_manager import watch_manager_view      # ⭐ NEW IMPORT
from backend import get_initial_caches, save_scanning_status, save_positions_cache, load_from_mt5
from backend import background_position_scanner
from dashboard import dashboard_view
from reports import reports_view
from positions import positions_view
from pl import pl_view
from groups import groups_view
from matrix_lot_ui import matrix_lot_view
from usd_matrix import usd_matrix_view

# Initialize session state for caches using backend (only once per session)
if 'positions_cache' not in st.session_state:
    positions_cache, accounts_cache = get_initial_caches()
    st.session_state.positions_cache = positions_cache
    st.session_state.accounts_cache = accounts_cache
else:
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
    col1, col2, col3, col4, col5, col6, col7, col8, col9, col10, col11, col12 = st.columns(12)
    with col1:
        if st.button("🏠 Dashboard", key="nav_dashboard"):
            st.session_state.page = "dashboard"
            st.query_params['page'] = "Dashboard"
    with col2:
        if st.button("👥 Accounts", key="nav_accounts"):
            st.session_state.page = "accounts"
            st.query_params['page'] = "Accounts"
    with col3:
        if st.button("📊 Reports", key="nav_reports"):
            st.session_state.page = "reports"
            st.query_params['page'] = "Reports"
    with col4:
        if st.button("🔍 Filter Search", key="nav_filter_search_top"):   # ⭐ NEW BUTTON
            st.session_state.page = "filter_search"
            st.query_params['page'] = "Filter Search"
    with col5:
        if st.button("👥 Groups", key="nav_groups_top"):
            st.session_state.page = "groups"
            st.query_params['page'] = "Groups"

    with col6:
        if st.button("📊 Matrix Lot", key="nav_matrix_lot"):
            st.session_state.page = "matrix_lot"
            st.query_params['page'] = "Matrix Lot"
    with col7:
        if st.button("📉 View USD P&L Matrix", key="nav_usd_matrix"):
            st.session_state.page = "usd_matrix"
            st.query_params['page'] = "USD Matrix"
    with col8:
        if st.button("📉XAUUSD", key="nav_xauusd"):
            st.session_state.page = "xauusd"
            st.query_params['page'] = "XAUUSD"
    with col9:
        if st.button("📊 Group Dashboard", key="nav_group_dashboard_top"):
            st.session_state.page = "groupdashboard"
            st.query_params['page'] = "Group Dashboard"
    with col10:
        if st.button("📊 Net Lot", key="nav_net_lot"):
            st.session_state.page = "net_lot"
            st.query_params['page'] = "Net Lot"
    with col11:
        if st.button("📁 File Management", key="nav_file_management"):
            st.session_state.page = "file_management"
            st.query_params['page'] = "File Management"
    with col12:
        if st.button("👀 Watch Manager", key="nav_watch_manager"):
            st.session_state.page = "watch_manager"
            st.query_params['page'] = "Watch Manager"



    st.markdown('</div>', unsafe_allow_html=True)

def main():
    # Start background position scanner thread (only once)
    if 'scanner_thread' not in st.session_state or not st.session_state.scanner_thread.is_alive():
        st.session_state.scanner_thread = threading.Thread(target=background_position_scanner, args=(positions_cache,), daemon=True)
        st.session_state.scanner_thread.start()

    st.set_page_config(page_title='RMS - Accounts', layout='wide')
    st.title('RMS — Accounts Dashboard (Streamlit)')

    # Auto refresh removed

    # Page mapping for URL navigation
    page_mapping = {
        "Dashboard": "dashboard",
        "Accounts": "accounts",
        "Profile": "profile",
        "Reports": "reports",
        "Positions": "positions",
        "P/L": "pl",
        "Groups": "groups",
        "Filter Search": "filter_search",
        "Group Dashboard": "groupdashboard",
        "Net Lot": "net_lot",
        "Trend": "trend",
        "Matrix Lot": "matrix_lot",
        "USD Matrix": "usd_matrix",
        "XAUUSD": "xauusd",
        "File Management": "file_management",
        "Watch Manager": "watch_manager"
    }

    # Initialize session state for page
    if 'page' not in st.session_state:
        st.session_state.page = 'dashboard'

    # Check URL query params for page navigation
    if 'page' in st.query_params:
        query_page = st.query_params['page']
        if query_page in page_mapping:
            st.session_state.page = page_mapping[query_page]

    # Sidebar navigation
    st.sidebar.header('Navigation')
    if st.sidebar.button("🏠 Dashboard", key="nav_dashboard"):
        st.session_state.page = "dashboard"
        st.query_params['page'] = "Dashboard"
    if st.sidebar.button("👥 Accounts", key="nav_accounts"):
        st.session_state.page = "accounts"
        st.query_params['page'] = "Accounts"
    if st.sidebar.button("👤 Profile", key="nav_profile"):
        st.session_state.page = "profile"
        st.query_params['page'] = "Profile"
    if st.sidebar.button("📊 Reports", key="nav_reports"):
        st.session_state.page = "reports"
        st.query_params['page'] = "Reports"
    if st.sidebar.button("📈 Open Positions", key="nav_positions"):
        st.session_state.page = "positions"
        st.query_params['page'] = "Positions"
    if st.sidebar.button("💰 P/L", key="nav_pl"):
        st.session_state.page = "pl"
        st.query_params['page'] = "P/L"
    if st.sidebar.button("👥 Groups", key="nav_groups"):
        st.session_state.page = "groups"
        st.query_params['page'] = "Groups"
    if st.sidebar.button("🔍 Filter Search"):   # ⭐ NEW SIDEBAR BUTTON
        st.session_state.page = "filter_search"
        st.query_params['page'] = "Filter Search"
    if st.sidebar.button("📊 Group Dashboard"):
        st.session_state.page = "groupdashboard"
        st.query_params['page'] = "Group Dashboard"
    if st.sidebar.button("📊 Net Lot"):
        st.session_state.page = "net_lot"
        st.query_params['page'] = "Net Lot"
    if st.sidebar.button("📈 Trend"):
        st.session_state.page = "trend"
        st.query_params['page'] = "Trend"
    if st.sidebar.button("📊 Matrix Lot", key="nav_matrix_lot"):
        st.session_state.page = "matrix_lot"
        st.query_params['page'] = "Matrix Lot"
    if st.sidebar.button("📉 View USD P&L Matrix", key="nav_usd_matrix_sidebar"):
        st.session_state.page = "usd_matrix"
        st.query_params['page'] = "USD Matrix"
    if st.sidebar.button("🪙 XAUUSD", key="nav_XAUUSD_top"):
        st.session_state.page = "xauusd"
        st.query_params['page'] = "XAUUSD"
    if st.sidebar.button("📁 File Management", key="nav_file_management_sidebar"):
        st.session_state.page = "file_management"
        st.query_params['page'] = "File Management"
    if st.sidebar.button("👀 Watch Manager", key="nav_watch_manager_sidebar"):
        st.session_state.page = "watch_manager"
        st.query_params['page'] = "Watch Manager"


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
        positions_view(data, positions_cache)
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
    elif st.session_state.page == 'usd_matrix':
        usd_matrix_view(data)
    elif st.session_state.page == 'xauusd':
        get_xauusd_data()
    elif st.session_state.page == "groupdashboard":
        groupdashboard_view(data)
    elif st.session_state.page == "net_lot":
        display_net_lot_view(data)
    elif st.session_state.page == "trend":
        display_trend_view(data)
    elif st.session_state.page == "file_management":
        file_management_view()
    elif st.session_state.page == "watch_manager":
        watch_manager_view()


if __name__ == '__main__':
    main()
__all__ = ['get_login_symbol_matrix', 'get_detailed_position_table', 'display_position_table']