import pandas as pd
import streamlit as st
import io
from MT5Service import MT5Service
from Matrix_lot import get_login_symbol_matrix
from pnl_matrix import get_login_symbol_pnl_from_open_positions
import logging

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

__all__ = ['get_symbol_net_lot_pnl', 'display_net_lot_view']


@st.cache_data(ttl=5)
def get_symbol_net_lot_pnl(accounts_df=None, positions_cache=None):
    """
    Aggregate net lots and USD P&L per symbol across all logins.

    Returns DataFrame with columns: ['symbol', 'net_lot', 'usd_pnl']
    """
    logger.info("🔄 LOADING SYMBOL NET LOT AND P&L DATA")

    # Get net lot matrix (login x symbol)
    net_lot_matrix = get_login_symbol_matrix(accounts_df, positions_cache)

    # Get P&L matrix (login x symbol)
    pnl_matrix = get_login_symbol_pnl_from_open_positions(accounts_df, positions_cache)

    if net_lot_matrix.empty and pnl_matrix.empty:
        logger.warning("⚠️  No data available for net lot and P&L")
        return pd.DataFrame(columns=['symbol', 'net_lot', 'usd_pnl'])

    # Aggregate by symbol (sum across all logins)
    symbol_data = {}

    # Collect all symbols from both matrices
    all_symbols = set()
    if not net_lot_matrix.empty:
        all_symbols.update(net_lot_matrix.columns)
    if not pnl_matrix.empty:
        all_symbols.update(pnl_matrix.columns)

    for symbol in all_symbols:
        net_lot = 0.0
        usd_pnl = 0.0

        # Sum net lots across logins for this symbol
        if symbol in net_lot_matrix.columns:
            # Exclude 'All Login' row if present
            login_rows = [idx for idx in net_lot_matrix.index if idx != 'All Login']
            net_lot = net_lot_matrix.loc[login_rows, symbol].sum()

        # Sum P&L across logins for this symbol
        if symbol in pnl_matrix.columns:
            # Exclude 'All Login' row if present
            login_rows = [idx for idx in pnl_matrix.index if idx != 'All Login']
            usd_pnl = pnl_matrix.loc[login_rows, symbol].sum()

        symbol_data[symbol] = {
            'net_lot': round(net_lot, 2),
            'usd_pnl': round(usd_pnl, 2)
        }

    # Convert to DataFrame
    df = pd.DataFrame.from_dict(symbol_data, orient='index').reset_index()
    df.columns = ['symbol', 'net_lot', 'usd_pnl']

    # Sort by absolute net lot descending
    df['abs_net_lot'] = df['net_lot'].abs()
    df = df.sort_values('abs_net_lot', ascending=False).drop(columns=['abs_net_lot'])

    logger.info(f"✅ SYMBOL NET LOT DATA LOADED: {len(df)} symbols")
    logger.info(f"📊 FIRST 5 SYMBOLS: {df.head(100).to_dict('records')}")

    return df


def display_net_lot_view(data):
    """
    Display Net Lot data per symbol in Streamlit.
    """
    st.subheader('📊 Net Lot Data by Symbol')
    st.write("This table shows aggregated net lots and USD P&L for each symbol across all logins.")

    # Auto-refresh every 5 seconds
    st.markdown("""
        <script>
        function autoRefreshTable() {
            setTimeout(function() {
                window.location.reload();
            }, 5000);
        }
        autoRefreshTable();
        </script>
    """, unsafe_allow_html=True)

    if data.empty:
        st.info('No account data available.')
        return

    try:
        df = get_symbol_net_lot_pnl(data, st.session_state.get('positions_cache'))

        if df.empty:
            st.info('No net lot data found.')
            return

        # Display metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Symbols", len(df))
        with col2:
            total_net_lot = df['net_lot'].sum()
            st.metric("Total Net Lot", f"{total_net_lot:.2f}")
        with col3:
            total_pnl = df['usd_pnl'].sum()
            st.metric("Total USD P&L", f"${total_pnl:,.2f}")

        # Display table
        display_df = df.copy()
        display_df['usd_pnl'] = display_df['usd_pnl'].apply(lambda x: f"${x:,.2f}")
        st.dataframe(display_df, use_container_width=True)

        # Export to CSV
        buf = io.StringIO()
        df.to_csv(buf, index=False)
        st.download_button('📥 Download Net Lot Data CSV', data=buf.getvalue(), file_name='net_lot_data.csv', mime='text/csv')

    except Exception as e:
        logger.error(f"Error displaying net lot view: {str(e)}")
        st.error(f'Failed to display net lot data: {e}')
