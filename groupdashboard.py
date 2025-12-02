import streamlit as st
import pandas as pd

def groupdashboard_view(data):

    df = pd.DataFrame(data)

    # -------------------------------
    # DETECT POSITION COLUMN
    # -------------------------------
    def detect_positions(df):
        possible_pos_cols = [
            "positions", "position", "open_positions",
            "total_positions", "pos", "open_pos"
        ]
        for col in possible_pos_cols:
            if col in df.columns:
                return pd.to_numeric(df[col], errors="coerce").fillna(0)
        return pd.Series(0, index=df.index)

    # -------------------------------
    # DETECT VOLUME COLUMN
    # -------------------------------
    def detect_volume(df):
        lower_map = {c.lower(): c for c in df.columns}

        possible_volume_cols = [
            "volume", "vol", "deal_volume", "trade_volume",
            "total_net_lot", "net_lot", "lot", "lots",
            "netlots", "vol_total"
        ]

        if "Vol" in df.columns:
            return pd.to_numeric(df["Vol"], errors="coerce").fillna(0)

        for pcol in possible_volume_cols:
            if pcol.lower() in lower_map:
                real_col = lower_map[pcol.lower()]
                return pd.to_numeric(df[real_col], errors="coerce").fillna(0)

        return pd.Series(0, index=df.index)

    # -------------------------------
    # DETECT PROFIT COLUMN
    # -------------------------------
    def detect_profit(df):
        profit_cols = ["total_usd_pl", "usd_pl", "pl", "profit", "pnl"]
        for col in profit_cols:
            if col in df.columns:
                return pd.to_numeric(df[col], errors="coerce").fillna(0)
        return pd.Series(0, index=df.index)

    # -------------------------------
    # APPLY DETECTORS
    # -------------------------------
    df["positions"] = detect_positions(df)
    df["volume"] = detect_volume(df)
    df["total_usd_pl"] = detect_profit(df)

    if "group" not in df.columns:
        df["group"] = "Unknown"

    if "login" not in df.columns:
        df["login"] = 0

    # -------------------------------
    # GROUP SUMMARY
    # -------------------------------
    df_grouped = (
        df.groupby("group", as_index=False)
        .agg({
            "login": "count",
            "positions": "sum",
            "volume": "sum",
            "total_usd_pl": "sum"
        })
        .rename(columns={"login": "accounts"})
    )

    total_groups = len(df_grouped)
    total_accounts = df_grouped["accounts"].sum()
    total_positions = df_grouped["positions"].sum()
    total_volume = df_grouped["volume"].sum()
    total_usd_pnl = df_grouped["total_usd_pl"].sum()

    # -------------------------------
    # DISPLAY METRICS
    # -------------------------------
    st.title("🌟 Group Dashboard")
    st.success(
        f"Found {total_groups} groups, {total_accounts} accounts, "
        f"{int(total_positions)} total positions"
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Groups", total_groups)
    col2.metric("Total Accounts", total_accounts)
    col3.metric("Total Net Volume", f"{total_volume:.2f}")
    col4.metric("Total USD P&L", f"${total_usd_pnl:,.2f}")

    # -------------------------------
    # AVERAGES
    # -------------------------------
    df_grouped["Avg Volume"] = (df_grouped["volume"] / df_grouped["accounts"]).round(2)
    df_grouped["Avg USD P&L"] = (df_grouped["total_usd_pl"] / df_grouped["accounts"]).round(2)

    df_grouped["Total USD P&L"] = df_grouped["total_usd_pl"].apply(lambda v: f"${v:,.2f}")

    final_cols = [
        "group", "accounts", "positions", "volume",
        "Total USD P&L", "Avg Volume", "Avg USD P&L"
    ]

    st.subheader("📋 Group Summary Table")
    st.dataframe(df_grouped[final_cols], use_container_width=True)
