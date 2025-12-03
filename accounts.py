import pandas as pd
import streamlit as st

def accounts_view(data):

    # ------------------------------
    # Account type buttons
    # ------------------------------
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Demo Account", key="demo_accounts"):
            st.session_state.account_type = "demo"

    with col2:
        if st.button("Real Account", key="real_accounts"):
            st.session_state.account_type = "real"

    # ------------------------------
    # Filter by account type
    # ------------------------------
    if 'account_type' in st.session_state:
        if st.session_state.account_type == "demo":
            data = data[data['group'].str.contains('demo', case=False, na=False)]
        elif st.session_state.account_type == "real":
            data = data[~data['group'].str.contains('demo', case=False, na=False)]

    # ------------------------------
    # Apply sidebar filters
    # ------------------------------
    df = data.copy()

    if 'group_filter' in st.session_state and st.session_state.group_filter:
        df = df[df['group'].isin(st.session_state.group_filter)]

    if 'name_filter' in st.session_state and st.session_state.name_filter:
        df = df[df['name'].isin(st.session_state.name_filter)]

    if 'email_filter' in st.session_state and st.session_state.email_filter:
        df = df[df['email'].isin(st.session_state.email_filter)]

    if 'leverage_filter' in st.session_state and st.session_state.leverage_filter:
        df = df[df['leverage'].isin(st.session_state.leverage_filter)]

    if 'login_search' in st.session_state and st.session_state.login_search:
        df = df[df['login'].astype(str).str.contains(st.session_state.login_search)]

    if 'balance' in df.columns:
        min_bal = st.session_state.get(
            'min_balance',
            float(data['balance'].min() if 'balance' in data.columns else 0.0)
        )
        max_bal = st.session_state.get(
            'max_balance',
            float(data['balance'].max() if 'balance' in data.columns else 0.0)
        )

        df = df[
            (df['balance'].astype(float) >= min_bal) &
            (df['balance'].astype(float) <= max_bal)
        ]

    # ------------------------------
    # MAIN TABLE (ALL ACCOUNTS)
    # ------------------------------
    st.subheader('Explore Accounts')
    st.write(f'{len(df)} accounts matching filters')

    # ⭐ FIXED: Show all rows (no 500 row limit)
    st.dataframe(df, use_container_width=True)

    # ------------------------------
    # Top accounts
    # ------------------------------
    st.subheader('Top accounts')
    if 'equity' in data.columns:
        top_eq = data.sort_values('equity', ascending=False).head(10)[['login', 'name', 'group', 'equity']]
        st.table(top_eq)

    st.subheader('Lowest Balance')
    if 'balance' in data.columns:
        worst_bal = data.sort_values('balance', ascending=True).head(10)[['login', 'name', 'group', 'balance']]
        st.table(worst_bal)
