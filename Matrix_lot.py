import pandas as pd
import streamlit as st
from MT5Service import MT5Service
import io
import logging
from datetime import datetime

# Setup logging for console output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

__all__ = ['get_login_symbol_matrix', 'get_detailed_position_table', 'display_position_table', 'display_login_symbol_pivot_table', 'get_login_symbol_profit_matrix', 'display_login_symbol_profit_pivot_table']

@st.cache_data(ttl=5)      # 🔥 Auto-cache for speed (reloads every 5 sec)
def get_login_symbol_matrix(accounts_df=None, positions_cache=None):
    svc = MT5Service()

    if accounts_df is not None and not accounts_df.empty:
        # Use provided accounts dataframe
        logins = accounts_df['login'].astype(str).unique()      
    else:
        # Fallback to fetching all accounts
        accounts = svc.list_mt5_accounts()
        if not accounts:
            return pd.DataFrame()
        logins = [acc["Login"] for acc in accounts]

    matrix = {}
    all_symbols = set()

    # If positions_cache wasn't provided, try to read it from Streamlit session state
    if positions_cache is None:
        try:
            positions_cache = st.session_state.get('positions_cache')
        except Exception:
            positions_cache = None

    # Normalize positions data if cache is available
    positions_list = None
    if positions_cache:
        # positions_cache may contain {'data': [...], 'timestamp': ..., ...}
        if isinstance(positions_cache, dict) and 'data' in positions_cache:
            positions_list = positions_cache.get('data') or []
        elif isinstance(positions_cache, list):
            positions_list = positions_cache

    for login in logins:
        symbol_lots = {}

        # First try to use cached positions (faster, background scanner)
        if positions_list:
            # positions stored by scanner include 'Login' key
            for p in positions_list:
                try:
                    p_login = str(p.get('Login') or p.get('login') or '')
                except Exception:
                    p_login = ''
                if p_login != str(login):
                    continue

                symbol = p.get('Symbol') or p.get('symbol')
                volume = p.get('Vol') or p.get('volume') or 0
                order_type = p.get('Type') or p.get('type')

                try:
                    volume = float(volume)
                except Exception:
                    volume = 0.0

                if not symbol:
                    continue

                if symbol not in symbol_lots:
                    symbol_lots[symbol] = 0.0

                # Determine if position is buy or sell
                is_buy = False
                if isinstance(order_type, (int, float)):
                    is_buy = int(order_type) == 0
                elif isinstance(order_type, str):
                    is_buy = order_type.strip().lower().startswith('b')
                else:
                    is_buy = True

                symbol_lots[symbol] += volume if is_buy else -volume
                all_symbols.add(symbol)

        else:
            # Fallback: query MT5Service per-login
            positions = svc.get_open_positions(login)
            for p in positions or []:
                symbol = p.get('symbol') or p.get('Symbol')
                volume = p.get('volume') or p.get('Volume') or 0
                order_type = p.get('type') or p.get('Type')

                try:
                    volume = float(volume)
                except Exception:
                    volume = 0.0

                if not symbol:
                    continue

                if symbol not in symbol_lots:
                    symbol_lots[symbol] = 0.0

                is_buy = False
                if isinstance(order_type, (int, float)):
                    is_buy = int(order_type) == 0
                elif isinstance(order_type, str):
                    is_buy = order_type.strip().lower().startswith('b')
                else:
                    is_buy = True

                symbol_lots[symbol] += volume if is_buy else -volume
                all_symbols.add(symbol)

        matrix[login] = symbol_lots

    # Convert into DataFrame
    df = pd.DataFrame.from_dict(matrix, orient="index").fillna(0.0)

    if not df.empty and len(df.columns) > 0:
        # Add "All Login" Row
        df.loc["All Login"] = df.sum()

        # Sort columns alphabetically
        df = df[sorted(df.columns)]

        # Move All Login to top
        df = df.reindex(["All Login"] + [i for i in df.index if i != "All Login"])

    return df


def get_detailed_position_table(accounts_df=None, positions_cache=None):
    """
    Get detailed position table in Symbol × Login format with volumes.
    Returns DataFrame with columns: Symbol, Login, Volume
    """
    logger.info("=" * 80)
    logger.info("🔄 LOADING POSITION TABLE - Started")
    logger.info(f"⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    svc = MT5Service()

    if accounts_df is not None and not accounts_df.empty:
        logins = accounts_df['login'].astype(str).unique()
        logger.info(f"✓ Using provided accounts_df with {len(logins)} logins")
    else:
        try:
            accounts = svc.list_accounts_by_groups()
            if not accounts:
                logger.warning("⚠️  No accounts found from MT5Service")
                return pd.DataFrame()
            logins = [str(acc["login"]) for acc in accounts]
            logger.info(f"✓ Fetched {len(logins)} logins from MT5Service")
        except Exception as e:
            logger.error(f"❌ Error fetching accounts: {str(e)}")
            return pd.DataFrame()

    # If positions_cache wasn't provided, try to read it from Streamlit session state
    if positions_cache is None:
        try:
            positions_cache = st.session_state.get('positions_cache')
        except Exception:
            positions_cache = None

    # Normalize positions data if cache is available
    positions_list = None
    if positions_cache:
        if isinstance(positions_cache, dict) and 'data' in positions_cache:
            positions_list = positions_cache.get('data') or []
        elif isinstance(positions_cache, list):
            positions_list = positions_cache

    all_records = []

    if positions_list:
        # Use cached positions
        for p in positions_list:
            try:
                p_login = str(p.get('Login') or p.get('login') or '')
                symbol = p.get('Symbol') or p.get('symbol')
                volume = p.get('Vol') or p.get('volume') or 0
                order_type = p.get('Type') or p.get('type')

                if not symbol or not p_login:
                    continue

                try:
                    volume = float(volume)
                except Exception:
                    volume = 0.0

                # Determine if position is buy or sell
                is_buy = True
                if isinstance(order_type, (int, float)):
                    is_buy = int(order_type) == 0
                elif isinstance(order_type, str):
                    is_buy = order_type.strip().lower().startswith('b')

                # Net volume (positive for buy, negative for sell)
                net_volume = volume if is_buy else -volume

                all_records.append({
                    'Symbol': symbol,
                    'Login': p_login,
                    'Volume': net_volume,
                    'Type': order_type
                })
            except Exception:
                continue
    else:
        # Fallback: query MT5Service per-login
        for login in logins:
            try:
                positions = svc.get_open_positions(login)
                for p in positions or []:
                    symbol = p.get('symbol') or p.get('Symbol')
                    volume = p.get('volume') or p.get('Volume') or 0
                    order_type = p.get('type') or p.get('Type')

                    if not symbol:
                        continue

                    try:
                        volume = float(volume)
                    except Exception:
                        volume = 0.0

                    is_buy = True
                    if isinstance(order_type, (int, float)):
                        is_buy = int(order_type) == 0
                    elif isinstance(order_type, str):
                        is_buy = order_type.strip().lower().startswith('b')

                    net_volume = volume if is_buy else -volume

                    all_records.append({
                        'Symbol': symbol,
                        'Login': str(login),
                        'Volume': net_volume,
                        'Type': order_type
                    })
            except Exception:
                continue

    if not all_records:
        logger.warning("⚠️  No position records found")
        return pd.DataFrame(columns=['Symbol', 'Login', 'Volume', 'Type'])

    df = pd.DataFrame(all_records)
    # Sort by Symbol, then by Login
    df = df.sort_values(['Symbol', 'Login']).reset_index(drop=True)
    
    # Log completion and show first 2 rows
    logger.info(f"✅ TABLE LOADED SUCCESSFULLY")
    logger.info(f"📊 Total records: {len(df)}")
    logger.info(f"📌 Unique Symbols: {df['Symbol'].nunique()}")
    logger.info(f"👥 Unique Logins: {df['Login'].nunique()}")
    logger.info("")
    logger.info("📋 FIRST 2 DATA ROWS:")
    logger.info("-" * 80)
    
    # Display first 2 rows in console
    if len(df) >= 1:
        logger.info(f"Row 1: Symbol={df.iloc[0]['Symbol']}, Login={df.iloc[0]['Login']}, Volume={df.iloc[0]['Volume']}, Type={df.iloc[0]['Type']}")
    if len(df) >= 2:
        logger.info(f"Row 2: Symbol={df.iloc[1]['Symbol']}, Login={df.iloc[1]['Login']}, Volume={df.iloc[1]['Volume']}, Type={df.iloc[1]['Type']}")
    
    logger.info("-" * 80)
    logger.info("✅ Position table ready for display")
    logger.info("")
    
    return df


def display_login_symbol_pivot_table(accounts_df=None, positions_cache=None):
    """
    Display pivot table with Login as rows and Symbol as columns (like the image).
    Each cell shows the net lot volume for that Login-Symbol combination.
    """
    logger.info("=" * 80)
    logger.info("DISPLAYING LOGIN x SYMBOL PIVOT TABLE")
    logger.info("=" * 80)
    
    st.subheader('📊 Login vs Symbol - Matrix View (Pivot Table)')
    st.write("**Rows: Login IDs | Columns: Symbols | Values: Net Lot Volume**")
    
    try:
        # Get the matrix
        matrix_df = get_login_symbol_matrix(accounts_df, positions_cache)
        
        if matrix_df.empty:
            st.warning("No data available to display pivot table.")
            return
        
        logger.info(f"Matrix shape: {matrix_df.shape}")
        logger.info(f"Logins (rows): {len(matrix_df) - 1} (plus All Login row)")
        logger.info(f"Symbols (columns): {len(matrix_df.columns)}")
        
        # Display metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Logins", len(matrix_df) - 1)
        with col2:
            st.metric("Total Symbols", len(matrix_df.columns))
        with col3:
            total_lots = matrix_df.loc['All Login'].sum() if 'All Login' in matrix_df.index else matrix_df.sum().sum()
            st.metric("Total Lots (All Login)", f"{total_lots:.2f}")
        
        # Display the pivot table
        st.write("**Pivot Table (Login × Symbol):**")
        
        # Format the dataframe for display
        display_df = matrix_df.copy()
        display_df = display_df.round(2)
        
        # Show with index (Login names)
        st.dataframe(display_df, use_container_width=True, height=500)
        
        # Log first 2 rows
        logger.info("")
        logger.info("FIRST 2 ROWS OF PIVOT TABLE:")
        logger.info("-" * 80)
        for idx, row_name in enumerate(matrix_df.index[:2]):
            row_data = matrix_df.loc[row_name]
            logger.info(f"Row {idx + 1} (Login={row_name}): {dict(row_data)}")
        logger.info("-" * 80)
        logger.info("")
        
        # Export option
        csv = display_df.to_csv().encode('utf-8')
        st.download_button(
            label='📥 Download Matrix as CSV',
            data=csv,
            file_name='login_symbol_matrix.csv',
            mime='text/csv'
        )
        
    except Exception as e:
        logger.error(f"Error displaying pivot table: {str(e)}")
        st.error(f'Error displaying pivot table: {str(e)}')


def display_position_table(accounts_df=None, positions_cache=None, show_details=True):
    """
    Display positions in Streamlit table format with pagination and single-record view.
    """
    logger.info("🎨 DISPLAYING POSITION TABLE IN STREAMLIT")
    st.subheader('📊 Login vs Symbol - Position Details')
    
    try:
        logger.info("📥 Fetching detailed position table...")
        df = get_detailed_position_table(accounts_df, positions_cache)
        logger.info(f"✅ Received DataFrame with {len(df)} rows")

        if df.empty:
            logger.warning("⚠️  DataFrame is empty - no positions to display")
            st.info('No open positions found.')
            return

        # Show summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Positions", len(df))
        with col2:
            total_volume = df['Volume'].sum()
            st.metric("Total Net Volume", f"{total_volume:.2f}")
        with col3:
            unique_symbols_count = len(df['Symbol'].unique())
            st.metric("Unique Symbols", unique_symbols_count)
        with col4:
            unique_logins_count = len(df['Login'].unique())
            st.metric("Unique Logins", unique_logins_count)

        # Create tabs for different views
        view_tab1, view_tab2, view_tab3 = st.tabs(["📑 Table View", "📄 Single Record View", "📊 Summary"])
        
        with view_tab1:
            st.write("**All Positions (grouped by Symbol):**")
            
            # Add filters (convert numpy arrays to lists for Streamlit)
            col_filter1, col_filter2, col_filter3 = st.columns(3)
            with col_filter1:
                selected_symbols = st.multiselect(
                    'Filter by Symbol',
                    options=sorted([str(s) for s in df['Symbol'].unique()]),
                    default=None,
                    key='symbol_filter'
                )
            with col_filter2:
                selected_logins = st.multiselect(
                    'Filter by Login',
                    options=sorted([str(l) for l in df['Login'].unique()]),
                    default=None,
                    key='login_filter'
                )
            with col_filter3:
                volume_min = st.number_input('Min Volume', value=float(df['Volume'].min()), key='vol_min')
            
            # Apply filters
            filtered_df = df.copy()
            if selected_symbols:
                filtered_df = filtered_df[filtered_df['Symbol'].isin(selected_symbols)]
            if selected_logins:
                filtered_df = filtered_df[filtered_df['Login'].isin(selected_logins)]
            filtered_df = filtered_df[filtered_df['Volume'].abs() >= volume_min]
            
            # Pagination for table view
            rows_per_page = st.slider('Rows per page', 5, 50, 10, key='rows_per_page')
            total_rows = len(filtered_df)
            total_pages = (total_rows // rows_per_page) + (1 if total_rows % rows_per_page > 0 else 0)
            
            if 'position_table_page' not in st.session_state:
                st.session_state.position_table_page = 1
            
            col_p1, col_p2, col_p3 = st.columns([1, 2, 1])
            with col_p1:
                if st.button('⬅️ Previous', key='prev_pos_page') and st.session_state.position_table_page > 1:
                    st.session_state.position_table_page -= 1
            with col_p2:
                page = st.selectbox(
                    'Page',
                    options=list(range(1, total_pages + 1)),
                    index=st.session_state.position_table_page - 1,
                    key='pos_page_select'
                )
                st.session_state.position_table_page = page
            with col_p3:
                if st.button('Next ➡️', key='next_pos_page') and st.session_state.position_table_page < total_pages:
                    st.session_state.position_table_page += 1
            
            # Display page
            start_idx = (st.session_state.position_table_page - 1) * rows_per_page
            end_idx = start_idx + rows_per_page
            page_df = filtered_df.iloc[start_idx:end_idx]
            
            display_df = page_df[['Symbol', 'Login', 'Volume']].copy()
            display_df['Volume'] = display_df['Volume'].round(2)
            st.write(f"Showing {start_idx + 1}-{min(end_idx, total_rows)} of {total_rows} records (Page {st.session_state.position_table_page}/{total_pages})")
            st.dataframe(display_df, use_container_width=True)
        
        with view_tab2:
            st.write("**View One Position at a Time:**")
            
            if len(df) > 0:
                # Single record view with navigation
                col_sr1, col_sr2, col_sr3 = st.columns([1, 2, 1])
                with col_sr1:
                    if st.button('⬅️ Prev Record', key='prev_record'):
                        if 'current_record_idx' not in st.session_state:
                            st.session_state.current_record_idx = 0
                        st.session_state.current_record_idx = max(0, st.session_state.current_record_idx - 1)
                
                with col_sr2:
                    if 'current_record_idx' not in st.session_state:
                        st.session_state.current_record_idx = 0
                    current_idx = st.number_input(
                        'Record #',
                        min_value=1,
                        max_value=len(df),
                        value=st.session_state.current_record_idx + 1,
                        key='record_idx_input'
                    ) - 1
                    st.session_state.current_record_idx = current_idx
                
                with col_sr3:
                    if st.button('Next Record ➡️', key='next_record'):
                        if 'current_record_idx' not in st.session_state:
                            st.session_state.current_record_idx = 0
                        st.session_state.current_record_idx = min(len(df) - 1, st.session_state.current_record_idx + 1)
                
                # Display single record
                if 0 <= st.session_state.current_record_idx < len(df):
                    record = df.iloc[st.session_state.current_record_idx]
                    st.write(f"**Record {st.session_state.current_record_idx + 1} of {len(df)}**")
                    
                    col_r1, col_r2, col_r3, col_r4 = st.columns(4)
                    with col_r1:
                        st.metric("Symbol", record['Symbol'])
                    with col_r2:
                        st.metric("Login", record['Login'])
                    with col_r3:
                        st.metric("Volume", f"{record['Volume']:.2f}")
                    with col_r4:
                        st.metric("Type", str(record['Type']))
                    
                    # Expandable details
                    with st.expander("📋 Full Details"):
                        for col_name in df.columns:
                            st.write(f"**{col_name}**: {record[col_name]}")
        
        with view_tab3:
            st.write("**Summary by Symbol:**")
            summary_df = df.groupby('Symbol')['Volume'].agg(['sum', 'count']).reset_index()
            summary_df.columns = ['Symbol', 'Total Volume', 'Position Count']
            summary_df['Total Volume'] = summary_df['Total Volume'].round(2)
            summary_df = summary_df.sort_values('Total Volume', ascending=False)
            st.dataframe(summary_df, use_container_width=True)
            
            st.write("**Summary by Login:**")
            login_summary = df.groupby('Login')['Volume'].agg(['sum', 'count']).reset_index()
            login_summary.columns = ['Login', 'Total Volume', 'Position Count']
            login_summary['Total Volume'] = login_summary['Total Volume'].round(2)
            login_summary = login_summary.sort_values('Total Volume', ascending=False)
            st.dataframe(login_summary, use_container_width=True)
        
        # Export to CSV (always available)
        st.divider()
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label='📥 Download All Positions as CSV',
            data=csv,
            file_name='open_positions.csv',
            mime='text/csv'
        )

    except Exception as e:
        st.error(f'Error displaying positions: {str(e)}')
