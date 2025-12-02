import streamlit as st
import pandas as pd
from Matrix_lot import get_detailed_position_table  # MT5 live positions fetch

def total_positions_from_detailed_table(accounts_df=None, positions_cache=None):
    """
    Return total positions, accounts with positions, and positions DataFrame
    based on get_detailed_position_table function.
    """
    df_positions = get_detailed_position_table(accounts_df, positions_cache)
    
    if df_positions.empty:
        total_positions = 0
        accounts_with_positions = 0
        total_accounts = len(accounts_df) if accounts_df is not None else 0
    else:
        total_positions = len(df_positions)
        accounts_with_positions = df_positions['Login'].nunique()
        total_accounts = len(accounts_df) if accounts_df is not None else accounts_with_positions

    return total_accounts, accounts_with_positions, total_positions, df_positions


def groupdashboard_view(data):
    # Base DataFrame from static data
    df = pd.DataFrame(data)
    if "group" not in df.columns:
        df["group"] = "Unknown"
    if "login" not in df.columns:
        df["login"] = 0

    # --------------------------
    # Get live MT5 positions
    # --------------------------
    total_accounts, accounts_with_positions, total_positions, df_positions = total_positions_from_detailed_table(df)

    # Ensure all logins have group info
    if not df_positions.empty:
        # Map login to group using 'data' if available, else default Unknown
        login_group_map = df.set_index('login')['group'].to_dict()
        df_positions['group'] = df_positions['Login'].map(lambda x: login_group_map.get(x, 'Unknown'))

        # Aggregate positions per group
        df_positions_grouped = (
            df_positions.groupby('group', as_index=False)
            .agg({'Login':'count','Volume':'sum'})
            .rename(columns={'Login':'positions','Volume':'volume'})
        )
    else:
        df_positions_grouped = pd.DataFrame(columns=['group','positions','volume'])

    st.info(f"Scanned {total_accounts} accounts, found {total_positions} positions so far")

    # --------------------------
    # Group summary table
    # --------------------------
    df_grouped = (
        df.groupby("group", as_index=False)
        .agg({
            "login": "count",
            "total_usd_pl": "sum"
        })
        .rename(columns={"login": "accounts"})
    )

    # Merge live positions per group
    df_grouped = df_grouped.merge(df_positions_grouped[['group','positions','volume']], on='group', how='left')
    df_grouped['positions'] = df_grouped['positions'].fillna(0).astype(int)
    df_grouped['volume'] = df_grouped['volume'].fillna(0)

    # --------------------------
    # Metrics
    # --------------------------
    total_groups = len(df_grouped)
    total_accounts_grouped = df_grouped["accounts"].sum()
    total_positions_grouped = df_grouped["positions"].sum()
    total_volume = df_grouped["volume"].sum()
    total_usd_pnl = df_grouped["total_usd_pl"].sum()

    st.title("🌟 Group Dashboard")
    st.success(
        f"Found {total_groups} groups, {total_accounts_grouped} accounts, "
        f"{total_positions_grouped} total positions"
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Groups", total_groups)
    col2.metric("Total Accounts", total_accounts_grouped)
    col3.metric("Total Net Volume", f"{total_volume:.2f}")
    col4.metric("Total USD P&L", f"${total_usd_pnl:,.2f}")

    df_grouped["Avg Volume"] = (df_grouped["volume"] / df_grouped["accounts"]).round(2)
    df_grouped["Avg USD P&L"] = (df_grouped["total_usd_pl"] / df_grouped["accounts"]).round(2)
    df_grouped["Total USD P&L"] = df_grouped["total_usd_pl"].apply(lambda v: f"${v:,.2f}")

    final_cols = [
        "group", "accounts", "positions", "volume",
        "Total USD P&L", "Avg Volume", "Avg USD P&L"
    ]
    st.subheader("📋 Group Summary Table")
    st.dataframe(df_grouped[final_cols], use_container_width=True)
