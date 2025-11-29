# pnl_matrix.py
import pandas as pd
import streamlit as st
from MT5Service import MT5Service
import logging

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ===========================
#  HELPER FUNCTIONS (OPTIMIZED)
# ===========================
def _safe_float(value):
    """Safely convert to float, default to 0.0."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _get_positions_list(positions_cache):
    """Extract positions list from cache or session state."""
    if positions_cache is None:
        try:
            positions_cache = st.session_state.get("positions_cache")
        except Exception:
            return None

    if not positions_cache:
        return None

    if isinstance(positions_cache, dict) and "data" in positions_cache:
        return positions_cache.get("data") or None
    elif isinstance(positions_cache, list):
        return positions_cache if positions_cache else None

    return None


def _build_final_matrix(matrix):
    """Convert matrix dict to DataFrame with 'All Login' row."""
    if not matrix:
        return pd.DataFrame()

    df = pd.DataFrame.from_dict(matrix, orient="index").fillna(0.0)

    if df.empty or len(df.columns) == 0:
        return df

    df.loc["All Login"] = df.sum()
    df = df[sorted(df.columns)]
    df = df.reindex(["All Login"] + [i for i in df.index if i != "All Login"])

    return df


# ===========================
#  UNIFIED MATRIX FUNCTIONS
# ===========================
@st.cache_data(ttl=5)
def get_login_symbol_pnl_matrix(data):
    """Wrapper for getting PNL matrix from open positions."""
    return get_login_symbol_pnl_from_open_positions(
        accounts_df=data.get("accounts_df"),
        positions_cache=data.get("positions_cache")
    )


# ===========================
#  PNL FROM OPEN POSITIONS
# ===========================
@st.cache_data(ttl=5)
def get_login_symbol_pnl_from_open_positions(accounts_df=None, positions_cache=None):
    """
    Compute USD unrealized P&L per Login vs Symbol using open positions.

    ✔ Uses cached scanner data (positions_cache)
    ✔ Falls back to MT5Service.get_open_positions(login)
    ✔ Returns final matrix with “All Login”
    """
    svc = MT5Service()

    # -----------------------------------
    # 1. GET LOGIN LIST
    # -----------------------------------
    if accounts_df is not None and not accounts_df.empty:
        logins = accounts_df["login"].astype(str).unique()
    else:
        try:
            accounts = svc.list_accounts_by_groups()
            if not accounts:
                return pd.DataFrame()
            logins = [str(acc.get("Login") or acc.get("login")) for acc in accounts]
        except Exception:
            return pd.DataFrame()

    # -----------------------------------
    # 2. NORMALIZE SCANNER POSITIONS CACHE
    # -----------------------------------
    positions_list = None

    if positions_cache is None:
        positions_cache = st.session_state.get("positions_cache", None)

    if positions_cache:
        if isinstance(positions_cache, dict) and "data" in positions_cache:
            positions_list = positions_cache.get("data") or []
        elif isinstance(positions_cache, list):
            positions_list = positions_cache

    matrix = {}

    # -----------------------------------
    # 3. FOR EACH LOGIN BUILD SYMBOL PNL
    # -----------------------------------
    for login in logins:
        symbol_pnl = {}

        # ------------------------------
        # USE SCANNER CACHE
        # ------------------------------
        if positions_list:
            for p in positions_list:
                p_login = str(p.get("Login") or p.get("login") or "")
                if p_login != str(login):
                    continue

                symbol = p.get("Symbol") or p.get("symbol")
                profit = p.get("P/L") or p.get("profit") or p.get("Profit") or p.get("pl") or 0

                try:
                    profit = float(profit)
                except:
                    profit = 0.0

                if symbol:
                    symbol_pnl[symbol] = symbol_pnl.get(symbol, 0.0) + profit

        # ------------------------------
        # FALLBACK: PER-LOGIN MT5 API CALL
        # ------------------------------
        else:
            try:
                positions = svc.get_open_positions(login)
            except Exception:
                positions = []

            for p in positions or []:
                symbol = p.get("symbol") or p.get("Symbol")
                profit = p.get("profit") or p.get("Profit") or p.get("pl") or 0

                try:
                    profit = float(profit)
                except:
                    profit = 0.0

                if symbol:
                    symbol_pnl[symbol] = symbol_pnl.get(symbol, 0.0) + profit

        matrix[str(login)] = symbol_pnl

    # -----------------------------------
    # 4. BUILD FINAL PIVOT DF
    # -----------------------------------
    df = pd.DataFrame.from_dict(matrix, orient="index").fillna(0.0)

    if not df.empty:
        df.loc["All Login"] = df.sum()
        df = df[sorted(df.columns)]
        df = df.reindex(["All Login"] + [i for i in df.index if i != "All Login"])

    return df


# ===========================
#  PROFIT/LOSS MATRIX FUNCTION
# ===========================
@st.cache_data(ttl=5)
def get_login_symbol_profit_matrix(accounts_df=None, positions_cache=None):
    """Get Login vs Symbol matrix with PROFIT/LOSS values from open positions."""
    svc = MT5Service()

    if accounts_df is not None and not accounts_df.empty:
        logins = accounts_df['login'].astype(str).unique()
    else:
        try:
            accounts = svc.list_accounts_by_groups()
            if not accounts:
                return pd.DataFrame()
            logins = [str(acc["login"]) for acc in accounts]
        except Exception:
            return pd.DataFrame()

    positions_list = _get_positions_list(positions_cache)
    matrix = {}

    for login in logins:
        symbol_pnl = {}
        login_str = str(login)

        if positions_list:
            for p in positions_list:
                p_login = str(p.get('Login') or p.get('login') or '')
                if p_login != login_str:
                    continue

                symbol = p.get('Symbol') or p.get('symbol')
                if not symbol:
                    continue

                profit = _safe_float(p.get('P/L') or p.get('profit') or p.get('Profit') or p.get('pl') or 0)
                symbol_pnl[symbol] = symbol_pnl.get(symbol, 0.0) + profit

        else:
            try:
                positions = svc.get_open_positions(login_str)
                for p in positions or []:
                    symbol = p.get('symbol') or p.get('Symbol')
                    if not symbol:
                        continue

                    profit = _safe_float(p.get('profit') or p.get('Profit') or p.get('pl') or 0)
                    symbol_pnl[symbol] = symbol_pnl.get(symbol, 0.0) + profit
            except Exception:
                pass

        matrix[login_str] = symbol_pnl

    return _build_final_matrix(matrix)


# ===========================
#  UI DISPLAY FUNCTION
# ===========================
def display_login_symbol_pnl_pivot(accounts_df=None, positions_cache=None):
    """
    Streamlit UI displaying the final pivot.
    """
    st.subheader("📈 Login vs Symbol Matrix - USD P&L")
    st.write("Rows: Login | Columns: Symbol | Values: USD P&L (open positions)")

    try:
        df = get_login_symbol_pnl_from_open_positions(accounts_df, positions_cache)

        if df.empty:
            st.info("No P&L data available from open positions.")
            return

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Logins", len(df) - (1 if "All Login" in df.index else 0))
        with col2:
            st.metric("Total Symbols", len(df.columns))
        with col3:
            total_pnl = df.loc["All Login"].sum()
            st.metric("Total USD P&L (All Login)", f"${total_pnl:,.2f}")

        display_df = df.copy().round(2)
        st.dataframe(display_df, width="stretch", height=520)

        logger.info("📋 FIRST 10 ROWS OF PNL PIVOT:")
        for idx, row_name in enumerate(display_df.index[:10]):
            logger.info(f"Row {idx+1} (Login={row_name}): {display_df.loc[row_name].to_dict()}")

        csv = display_df.to_csv().encode("utf-8")
        st.download_button(
            "📥 Download P&L Matrix CSV",
            data=csv,
            file_name="login_symbol_pnl_matrix.csv",
            mime="text/csv"
        )

    except Exception as e:
        logger.exception("Error displaying P&L pivot:")
        st.error(f"Error displaying P&L pivot: {e}")


# ===========================
#  PROFIT/LOSS DISPLAY FUNCTION
# ===========================
def display_login_symbol_profit_pivot_table(accounts_df=None, positions_cache=None):
    """
    Display pivot table with Login as rows and Symbol as columns.
    Each cell shows the USD P&L (profit/loss) for that Login-Symbol combination from open positions.
    """
    logger.info("=" * 80)
    logger.info("DISPLAYING LOGIN x SYMBOL PROFIT/LOSS PIVOT TABLE")
    logger.info("=" * 80)
    
    st.subheader('📊 Login vs Symbol - Profit/Loss Matrix (Open Positions)')
    st.write("**Rows: Login IDs | Columns: Symbols | Values: USD P&L (Profit/Loss)**")
    
    try:
        # Get the profit matrix
        matrix_df = get_login_symbol_profit_matrix(accounts_df, positions_cache)
        
        if matrix_df.empty:
            st.warning("No data available to display profit/loss pivot table.")
            return
        
        logger.info(f"Profit Matrix shape: {matrix_df.shape}")
        logger.info(f"Logins (rows): {len(matrix_df) - 1} (plus All Login row)")
        logger.info(f"Symbols (columns): {len(matrix_df.columns)}")
        
        # Display metrics and views (Table + Single-Row)
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Logins", max(0, len(matrix_df) - (1 if 'All Login' in matrix_df.index else 0)))
        with col2:
            st.metric("Total Symbols", len(matrix_df.columns))
        with col3:
            total_pnl = matrix_df.loc['All Login'].sum() if 'All Login' in matrix_df.index else matrix_df.sum().sum()
            color = "inverse" if total_pnl < 0 else "off"
            st.metric("Total USD P&L (All Login)", f"${total_pnl:,.2f}", delta_color=color)
        with col4:
            profitable_positions = (matrix_df.loc['All Login'] > 0).sum() if 'All Login' in matrix_df.index else (matrix_df.sum() > 0).sum()
            st.metric("Profitable Symbols", int(profitable_positions))

        # Tabs: full table view and single-row (one-by-one) view
        tab_table, tab_single = st.tabs(["📄 Table View", "🔎 Single Row View"])

        # Table View: show full pivot
        with tab_table:
            st.write("**Profit/Loss Matrix (Login × Symbol):**")
            display_df = matrix_df.copy().round(2)
            st.dataframe(display_df, use_container_width=True, height=500)

        # Single Row View: navigate rows one-by-one similar to Matrix_lot.py
        with tab_single:
            st.write("**View one Login row at a time**")

            rows = list(matrix_df.index)
            if not rows:
                st.info("No rows available to view.")
                return

            # Ensure we don't show All Login as a navigable item first (optional)
            start_index = 0
            # Provide Prev / Next and index selector
            if 'pnl_current_row_idx' not in st.session_state:
                st.session_state.pnl_current_row_idx = start_index

            col_sr1, col_sr2, col_sr3 = st.columns([1, 2, 1])
            with col_sr1:
                if st.button('⬅️ Prev', key='pnl_prev'):
                    st.session_state.pnl_current_row_idx = max(0, st.session_state.pnl_current_row_idx - 1)
            with col_sr2:
                current = st.number_input('Row #', min_value=1, max_value=len(rows), value=st.session_state.pnl_current_row_idx + 1, key='pnl_row_num')
                st.session_state.pnl_current_row_idx = int(current) - 1
            with col_sr3:
                if st.button('Next ➡️', key='pnl_next'):
                    st.session_state.pnl_current_row_idx = min(len(rows) - 1, st.session_state.pnl_current_row_idx + 1)

            idx = st.session_state.pnl_current_row_idx
            idx = max(0, min(idx, len(rows) - 1))
            st.session_state.pnl_current_row_idx = idx

            login_name = rows[idx]
            record = matrix_df.loc[login_name]

            st.write(f"**Record {idx + 1} of {len(rows)} — Login: {login_name}**")

            # Summary metrics for this login
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                row_total = record.sum()
                st.metric("Row Total P&L (USD)", f"${row_total:,.2f}")
            with col_b:
                profitable = int((record > 0).sum())
                st.metric("Profitable Symbols", profitable)
            with col_c:
                loss_symbols = int((record < 0).sum())
                st.metric("Losing Symbols", loss_symbols)

            # Show the symbols and pnl for this login as a small table
            row_df = record.reset_index()
            row_df.columns = ['Symbol', 'USD P&L']
            row_df['USD P&L'] = row_df['USD P&L'].round(2)
            st.dataframe(row_df, use_container_width=True, height=350)

            # Expandable: full raw row dict
            with st.expander('📋 Full Row Details'):
                st.json(record.fillna(0).to_dict())
        
        # Log first 10 rows
        logger.info("")
        logger.info("FIRST 10 ROWS OF PROFIT/LOSS PIVOT TABLE:")
        logger.info("-" * 80)
        for idx, row_name in enumerate(matrix_df.index[:10]):
            row_data = matrix_df.loc[row_name]
            logger.info(f"Row {idx + 1} (Login={row_name}): {dict(row_data)}")
        logger.info("-" * 80)
        logger.info("")
        
        # Export option (from full table)
        csv = matrix_df.round(2).to_csv().encode('utf-8')
        st.download_button(
            label='📥 Download Profit/Loss Matrix as CSV',
            data=csv,
            file_name='login_symbol_profit_matrix.csv',
            mime='text/csv'
        )
        
    except Exception as e:
        logger.error(f"Error displaying profit/loss pivot table: {str(e)}")
        st.error(f'Error displaying profit/loss pivot table: {str(e)}')
