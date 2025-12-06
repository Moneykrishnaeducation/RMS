import streamlit as st
import pandas as pd
from Matrix_lot import get_detailed_position_table  # Your MT5 positions function


# ============================================================
#     TOTAL POSITIONS FROM DETAILED MT5 POSITION TABLE
# ============================================================
def total_positions_from_detailed_table(accounts_df=None, positions_cache=None):
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



# ============================================================
#                GROUP DASHBOARD VIEW
# ============================================================
def groupdashboard_view(data):

    df = pd.DataFrame(data)

    # ---------- Detect fields ----------
    def detect_positions(df):
        for col in ["positions","position","open_positions","total_positions","pos","open_pos"]:
            if col in df.columns:
                return pd.to_numeric(df[col], errors="coerce").fillna(0)
        return pd.Series(0, index=df.index)

    def detect_volume(df):
        lower = {c.lower(): c for c in df.columns}
        for c in ["volume","vol","deal_volume","trade_volume","total_net_lot","net_lot","lot","lots","netlots"]:
            if c.lower() in lower:
                col = lower[c.lower()]
                return pd.to_numeric(df[col], errors="coerce").fillna(0)
        return pd.Series(0, index=df.index)

    def detect_profit(df):
        for col in ["total_usd_pl","usd_pl","pl","profit","pnl"]:
            if col in df.columns:
                return pd.to_numeric(df[col], errors="coerce").fillna(0)
        return pd.Series(0, index=df.index)

    df["positions"] = detect_positions(df)
    df["volume"] = detect_volume(df)
    df["total_usd_pl"] = detect_profit(df)

    if "group" not in df.columns:
        df["group"] = "Unknown"
    if "login" not in df.columns:
        df["login"] = 0


    # ---------- Get actual MT5 live positions ----------
    total_accounts, accounts_with_positions, total_positions, df_positions = total_positions_from_detailed_table(df)

    #st.info(f"Scanned {total_accounts} accounts → Found {total_positions} open positions")


    # ---------- Group live positions ----------
    if not df_positions.empty:
        df_positions_grouped = (
            df_positions.merge(df[['login','group']], left_on='Login', right_on='login', how='left')
            .groupby('group', as_index=False)
            .agg({'Login': 'count', 'Volume': 'sum'})
            .rename(columns={'Login': 'positions', 'Volume': 'volume'})
        )
    else:
        df_positions_grouped = df.groupby("group", as_index=False).agg({'login':'count'})
        df_positions_grouped.rename(columns={'login':'positions'}, inplace=True)
        df_positions_grouped['volume'] = 0


    # ---------- Group dashboard summary ----------
    df_grouped = (
        df.groupby("group", as_index=False)
        .agg({"login": "count", "total_usd_pl": "sum"})
        .rename(columns={"login": "accounts"})
    )

    df_grouped = df_grouped.merge(df_positions_grouped[['group','positions','volume']], on="group", how="left")
    df_grouped["positions"] = df_grouped["positions"].fillna(0).astype(int)
    df_grouped["volume"] = df_grouped["volume"].fillna(0)

    # Totals
    total_groups = len(df_grouped)
    total_accounts_grouped = df_grouped["accounts"].sum()
    total_positions_grouped = df_grouped["positions"].sum()
    total_volume = df_grouped["volume"].sum()
    total_usd_pnl = df_grouped["total_usd_pl"].sum()


    # ---------- UI ----------
    st.title("🌟 Group Dashboard")

    st.success(
        f"Found {total_groups} groups | {total_accounts_grouped} accounts | "
        f"{total_positions_grouped} Total positions"
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Groups", total_groups)
    col2.metric("Total Accounts", total_accounts_grouped)
    col3.metric("Total Net Lot", f"{total_volume:.2f}")
    col4.metric("Total USD P&L", f"${total_usd_pnl:,.2f}")


    # ---------- Rename UI columns ----------
    df_grouped["Avg Net Lot"] = (df_grouped["volume"] / df_grouped["accounts"]).round(2)
    df_grouped["Avg USD P&L"] = (df_grouped["total_usd_pl"] / df_grouped["accounts"]).round(2)
    df_grouped["Total USD P&L"] = df_grouped["total_usd_pl"].apply(lambda v: f"${v:,.2f}")

    df_grouped.rename(columns={
        "volume": "Net Lot"
    }, inplace=True)

    final_cols = [
        "group", "accounts", "positions", "Net Lot",
        "Total USD P&L", "Avg Net Lot", "Avg USD P&L"
    ]


    st.subheader("📌 Group Summary Table")
    st.dataframe(df_grouped[final_cols], width='stretch')



# ============================================================
#     ADD OPEN POSITIONS FUNCTION (FINAL)
# ============================================================
class MT5Service:

    def get_open_positions(self, login_id):
        """Return list of open positions for the given login id."""
        mgr = self.connect()
        try:
            positions = mgr.PositionGet(int(login_id))
            if not positions:
                return []

            out = []
            for p in positions:
                out.append({
                    'date': getattr(p, 'TimeCreate', None),
                    'id': getattr(p, 'Position', None),
                    'symbol': getattr(p, 'Symbol', None),
                    'volume': round(getattr(p, 'Volume', 0) / 10000, 2),
                    'price': getattr(p, 'PriceOpen', None),
                    'profit': getattr(p, 'Profit', None),
                    'type': 'Buy' if getattr(p, 'Action', None) == 0 else 'Sell',
                })
            return out

        except Exception:
            return []      
