import streamlit as st
import pandas as pd

def groupdashboard_view(data):

    # Convert incoming data to dataframe
    df = pd.DataFrame(data)

    # ---------------------------------------------------------------
    # GROUP DASHBOARD HEADER
    # ---------------------------------------------------------------
    st.markdown("<h1>🌟 Group Dashboard</h1>", unsafe_allow_html=True)

    total_groups = len(df)
    total_accounts = df["accounts"].sum()
    total_positions = df["positions"].sum()

    # ---------------------------------------------------------------
    # SUCCESS MESSAGE
    # ---------------------------------------------------------------
    st.success(f"Found {total_groups} groups with {total_positions} total positions")

    # ---------------------------------------------------------------
    # GROUP OVERVIEW SECTION
    # ---------------------------------------------------------------
    st.markdown("## 📊 Group Overview")

    total_net_lot = df["total_net_lot"].sum()
    total_usd_pnl = df["total_usd_pl"].sum()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Groups", total_groups)

    with col2:
        st.metric("Total Accounts", total_accounts)

    with col3:
        st.metric("Total Net Lot", round(total_net_lot, 2))

    with col4:
        st.metric("Total USD P&L", f"${total_usd_pnl:,.2f}")

    # ---------------------------------------------------------------
    # GROUP SUMMARY TABLE
    # ---------------------------------------------------------------
    st.markdown("## 📝 Group Summary Table")

    df_display = df.copy()
    df_display["Total USD P&L"] = df_display["total_usd_pl"].apply(lambda x: f"${x:,.2f}")
    df_display["Avg Net Lot"] = (df_display["total_net_lot"] / df_display["positions"]).round(2)
    df_display["Avg USD P&L"] = (df_display["total_usd_pl"] / df_display["positions"]).round(2)

    final_columns = [
        "group", "accounts", "positions", "total_net_lot",
        "Total USD P&L", "Avg Net Lot", "Avg USD P&L"
    ]

    st.dataframe(df_display[final_columns], use_container_width=True)
