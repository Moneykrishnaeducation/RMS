import streamlit as st
import pandas as pd

def groupdashboard_view(data):

    df = pd.DataFrame(data)

    # ----------------------------------------------------
    # ENSURE REQUIRED COLUMNS
    # ----------------------------------------------------
    if "group" not in df.columns:
        df["group"] = "Unknown"

    if "login" not in df.columns:
        df["login"] = 1     # fallback: treat each row as one account

    # Ensure numeric fields exist
    for col in ["positions", "total_net_lot", "total_usd_pl"]:
        if col not in df.columns:
            df[col] = 0

    # ----------------------------------------------------
    # GROUPING LOGIC
    # ----------------------------------------------------
    df_grouped = (
        df.groupby("group", as_index=False)
        .agg({
            "login": "count",
            "positions": "sum",
            "total_net_lot": "sum",
            "total_usd_pl": "sum"
        })
        .rename(columns={"login": "accounts"})
    )

    # ----------------------------------------------------
    # TOTALS
    # ----------------------------------------------------
    total_groups = len(df_grouped)
    total_accounts = df_grouped["accounts"].sum()
    total_positions = df_grouped["positions"].sum()
    total_net_lot = df_grouped["total_net_lot"].sum()
    total_usd_pnl = df_grouped["total_usd_pl"].sum()

    # ----------------------------------------------------
    # UI HEADER
    # ----------------------------------------------------
    st.markdown("<h1>🌟 Group Dashboard</h1>", unsafe_allow_html=True)

    st.success(
        f"Found {total_groups} groups, "
        f"{total_accounts} accounts, and "
        f"{total_positions} Total positions"
    )

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Groups", total_groups)
    with col2:
        st.metric("Total Accounts", total_accounts)
    with col3:
        st.metric("Total Net Lot", total_net_lot)
    with col4:
        st.metric("Total USD P&L", f"${total_usd_pnl:,.2f}")

    # ----------------------------------------------------
    # ADD AVERAGE VALUES
    # ----------------------------------------------------
    df_grouped["Avg Net Lot"] = df_grouped.apply(
        lambda r: round(r["total_net_lot"] / r["positions"], 2)
        if r["positions"] else 0,
        axis=1
    )

    df_grouped["Avg USD P&L"] = df_grouped.apply(
        lambda r: round(r["total_usd_pl"] / r["positions"], 2)
        if r["positions"] else 0,
        axis=1
    )

    # Format USD P&L column
    df_grouped["Total USD P&L"] = df_grouped["total_usd_pl"].apply(
        lambda x: f"${x:,.2f}"
    )

    # Columns to display
    final_cols = [
        "group",
        "accounts",
        "positions",
        "total_net_lot",
        "Total USD P&L",
        "Avg Net Lot",
        "Avg USD P&L"
    ]

    # ----------------------------------------------------
    # SHOW FINAL TABLE
    # ----------------------------------------------------
    st.dataframe(df_grouped[final_cols], use_container_width=True)