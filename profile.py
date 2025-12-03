import pandas as pd
import streamlit as st
from MT5Service import MT5Service

def profile_view():
    st.header('Account Profile Search')

    # Search inputs
    col1, col2 = st.columns(2)
    with col1:
        search_name = st.text_input('Search by Name', key='search_name')
    with col2:
        search_email = st.text_input('Search by Email', key='search_email')

    # Search button
    if st.button('Search Account'):
        if not search_name and not search_email:
            st.warning('Please enter a name or email to search.')
            return

        # Load MT5 service
        svc = MT5Service()

        # Search for accounts
        accounts = svc.search_accounts_by_name_email(search_name, search_email)
        if accounts:
            st.subheader('Search Results')
            st.dataframe(pd.DataFrame(accounts))

            # Select account for detailed view
            if len(accounts) == 1:
                selected_login = accounts[0]['login']
            else:
                login_options = [acc['login'] for acc in accounts]
                selected_login = st.selectbox('Select account for details:', login_options)

            if selected_login:
                st.session_state.selected_login = selected_login
                display_account_details(selected_login)
        else:
            st.info('No accounts found matching the search criteria.')

    # Display selected account details if available
    if 'selected_login' in st.session_state:
        display_account_details(st.session_state.selected_login)

    # Back button
    if st.button('Back to Accounts'):
        st.session_state.page = 'accounts'

def display_account_details(login_id):
    st.subheader(f'Details for Login: {login_id}')

    # Load MT5 service
    svc = MT5Service()

    # Get account details
    account_details = svc.get_account_details(login_id)
    if account_details:
        st.subheader('Account Details')
        # Display in a readable format instead of JSON
        for key, value in account_details.items():
            if key not in ['last_access', 'registration']:  # Skip time fields if causing issues
                st.write(f"**{key.replace('_', ' ').title()}:** {value}")
    else:
        st.error('Account details not found.')

    # Get open positions
    positions = svc.get_open_positions(login_id)
    if positions:
        st.subheader('Open Positions')
        df = pd.DataFrame(positions)
        df['volume'] = df['volume'].map('{:.2f}'.format)
        st.table(df)
    else:
        st.info('No open positions.')
