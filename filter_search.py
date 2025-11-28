import pandas as pd
import streamlit as st

# ------------------------------------------------------------
# SAFE FILTER HELPERS
# ------------------------------------------------------------

def is_demo(group_value):
    """Return True only if group starts with 'demo'."""
    if pd.isna(group_value):
        return False
    return str(group_value).lower().startswith("demo")

def is_real(group_value):
    """Return True only if group does NOT start with 'demo'."""
    if pd.isna(group_value):
        return True
    return not str(group_value).lower().startswith("demo")

# ------------------------------------------------------------
# FILTER SEARCH VIEW (Real + Demo Combined)
# ------------------------------------------------------------

def filter_search_view(data):
    st.title("🔍 Advanced Filter Search")

    # ---------------- TOTAL COUNTS ----------------
    total_real = len(data[data["group"].apply(is_real)])
    total_demo = len(data[data["group"].apply(is_demo)])

    st.markdown(
        f"**Total Real Accounts:** {total_real} &nbsp; | &nbsp; "
        f"**Total Demo Accounts:** {total_demo}"
    )

    # ---------------- ACCOUNT TYPE RADIO ----------------
    account_type = st.radio(
        "Select Account Type",
        ["Real Account", "Demo Account"],
        horizontal=True
    )

    df = data.copy()

    # ---------------- FILTER ACCOUNT TYPE (FIXED BUG) ----------------
    if 'group' in df.columns:
        if account_type == "Real Account":
            df = df[df["group"].apply(is_real)]
        else:
            df = df[df["group"].apply(is_demo)]

    # ---------------- SEARCH FILTERS ----------------
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        # Create dropdown list for login (unique values + "All")
        login_options = ["All"] + sorted(df['login'].dropna().unique().tolist())

        # Dropdown selectbox
        login_filter = st.selectbox("Filter by Login", login_options)

    with col2:
        name_options = ["All"] + sorted(df['name'].dropna().unique().tolist())
        name_filter = st.selectbox("Filter by Name", name_options)

    with col3:
        group_options = ["All"] + sorted(df['group'].dropna().unique().tolist())
        base_filter = st.selectbox("Filter by Base Symbol", group_options)

    # ---------------- APPLY FILTERS ---------------
    filtered_df = df.copy()
    if login_filter != "All":
        filtered_df = filtered_df[ filtered_df['login'] == login_filter ]

    if name_filter != "All":
        df = df[df['name'] == name_filter]

    if base_filter != "All":
        df = df[df['group'] == base_filter]

    # ---------------- APPLY SIDEBAR FILTERS ----------------
    if st.session_state.get("group_filter"):
        df = df[df['group'].isin(st.session_state.group_filter)]

    if st.session_state.get("name_filter"):
        df = df[df['name'].isin(st.session_state.name_filter)]

    if st.session_state.get("email_filter"):
        df = df[df['email'].isin(st.session_state.email_filter)]

    if st.session_state.get("leverage_filter"):
        df = df[df['leverage'].isin(st.session_state.leverage_filter)]

    if st.session_state.get("login_search"):
        df = df[df['login'].astype(str).str.contains(st.session_state.login_search)]

    if 'balance' in df.columns:
        min_bal = st.session_state.get('min_balance', float(df['balance'].min()))
        max_bal = st.session_state.get('max_balance', float(df['balance'].max()))
        df = df[(df['balance'].astype(float) >= min_bal) & (df['balance'].astype(float) <= max_bal)]

    # ---------------- DISPLAY FULL REAL ACCOUNT LIST ----------------
    st.subheader(f"{account_type} Matching Filters")

    st.write(f"**{len(df)} accounts found**")

    # ⭐ SHOW FULL TABLE (not sliced to 500 rows)
    st.dataframe(df, use_container_width=True)

# ------------------------------------------------------------
# DEMO ACCOUNTS VIEW
# ------------------------------------------------------------

def demo_accounts_view(data):
    data = data[data["group"].apply(is_demo)]
    df = data.copy()

    if st.session_state.get("group_filter"):
        df = df[df['group'].isin(st.session_state.group_filter)]

    if st.session_state.get("name_filter"):
        df = df[df['name'].isin(st.session_state.name_filter)]

    if st.session_state.get("email_filter"):
        df = df[df['email'].isin(st.session_state.email_filter)]

    if st.session_state.get("leverage_filter"):
        df = df[df['leverage'].isin(st.session_state.leverage_filter)]

    if st.session_state.get("login_search"):
        df = df[df['login'].astype(str).str.contains(st.session_state.login_search)]

    if 'balance' in df.columns:
        min_bal = st.session_state.get('min_balance', float(df['balance'].min()))
        max_bal = st.session_state.get('max_balance', float(df['balance'].max()))
        df = df[(df['balance'].astype(float) >= min_bal) & (df['balance'].astype(float) <= max_bal)]

    st.subheader('Demo Account Matching Filters')
    st.write(f'{len(df)} demo accounts found')

    # ⭐ SHOW FULL LIST
    st.dataframe(df, use_container_width=True)

    # Top demo accounts
    st.subheader('Top Demo Accounts')
    if 'equity' in df.columns:
        top_eq = df.sort_values('equity', ascending=False).head(10)[['login', 'name', 'group', 'equity']]
        st.table(top_eq)

    if 'balance' in df.columns:
        worst_bal = df.sort_values('balance', ascending=True).head(10)[['login', 'name', 'group', 'balance']]
        st.table(worst_bal)
