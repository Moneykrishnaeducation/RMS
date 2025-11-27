import os
import io
import json
import pandas as pd
import streamlit as st

from MT5Service import MT5Service

@st.cache_data(ttl=300)
def load_from_mt5(use_groups=True):
    """Fetch accounts from MT5 using MT5Service. Cached for 5 minutes by default."""
    svc = MT5Service()
    if use_groups:
        accounts = svc.list_accounts_by_groups()
    else:
        # Fallback to index-based if desired
        accounts = svc.list_accounts_by_index()
    if not accounts:
        return pd.DataFrame()
    return pd.json_normalize(accounts)


@st.cache_data(ttl=300)
def load_from_mt5(use_groups=True):
    """Fetch accounts from MT5 using MT5Service. Cached for 5 minutes by default."""
    svc = MT5Service()
    if use_groups:
        accounts = svc.list_accounts_by_groups()
    else:
        # Fallback to index-based if desired
        accounts = svc.list_accounts_by_index()
    if not accounts:
        return pd.DataFrame()
    return pd.json_normalize(accounts)


def main():
    st.set_page_config(page_title='RMS - Accounts', layout='wide')
    st.title('RMS — Accounts Dashboard (Streamlit)')

    st.sidebar.header('Data source')
    st.sidebar.write('Loading accounts directly from MT5 Manager using `.env` credentials')
    data = pd.DataFrame()
    col1, col2 = st.sidebar.columns([3,1])
    with col1:
        use_groups = st.checkbox('Enumerate by groups (recommended)', value=True)
    with col2:
        refresh = st.button('Refresh')

    try:
        if refresh:
            # clear cache and re-fetch
            load_from_mt5.clear()
        with st.spinner('Loading accounts from MT5...'):
            data = load_from_mt5(use_groups)
    except Exception as e:
        st.error(f'Error loading from MT5: {e}')
        data = pd.DataFrame()

    if data.empty:
        st.info('No account data available.')
        return

    # Normalize columns and types
    if 'login' in data.columns:
        try:
            data['login'] = data['login'].astype(str)
        except Exception:
            pass

    # Top-level KPIs
    total_accounts = len(data)
    total_balance = data.get('balance', pd.Series(0)).astype(float).sum()
    total_equity = data.get('equity', pd.Series(0)).astype(float).sum()

    k1, k2, k3 = st.columns(3)
    k1.metric('Total accounts', total_accounts)
    k2.metric('Total balance', f"{total_balance:,.2f}")
    k3.metric('Total equity', f"{total_equity:,.2f}")

    # Groups breakdown
    st.subheader('Groups')
    if 'group' in data.columns:
        groups = data.groupby('group').agg(count=('login', 'count'), balance_sum=('balance', 'sum'), equity_sum=('equity', 'sum'))
        groups = groups.sort_values('count', ascending=False)
        st.dataframe(groups.reset_index().rename(columns={'group': 'Group'}).head(50))
        st.bar_chart(groups['count'].head(20))

    # Filters
    st.subheader('Explore Accounts')
    c1, c2 = st.columns([3, 1])
    with c2:
        login_search = st.text_input('Search login')
        group_filter = None
        if 'group' in data.columns:
            groups_list = sorted(data['group'].dropna().unique().tolist())
            group_filter = st.multiselect('Filter groups', groups_list, max_selections=5)
        min_balance = st.number_input('Min balance', value=float(data['balance'].min() if 'balance' in data.columns else 0.0))

    df = data.copy()
    if group_filter:
        df = df[df['group'].isin(group_filter)]
    if login_search:
        df = df[df['login'].astype(str).str.contains(login_search)]
    if 'balance' in df.columns:
        df = df[df['balance'].astype(float) >= float(min_balance)]

    st.write(f'{len(df)} accounts matching filters')
    st.dataframe(df.head(500))

    # Top accounts
    st.subheader('Top accounts')
    if 'equity' in data.columns:
        top_eq = data.sort_values('equity', ascending=False).head(10)[['login', 'name', 'group', 'equity']]
        st.table(top_eq)
    if 'balance' in data.columns:
        worst_bal = data.sort_values('balance', ascending=True).head(10)[['login', 'name', 'group', 'balance']]
        st.table(worst_bal)

    # Export filtered results
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    st.download_button('Download filtered CSV', data=buf.getvalue(), file_name='accounts_filtered.csv', mime='text/csv')


if __name__ == '__main__':
    main()
