import streamlit as st

def groups_view(data):
    # Auto-refresh every 5 seconds
    st.markdown("""
        <script>
        function autoRefreshTable() {
            setTimeout(function() {
                window.location.reload();
            }, 15000);
        }
        autoRefreshTable();
        </script>
    """, unsafe_allow_html=True)

    st.subheader('Groups Overview')

    if 'group' in data.columns:
        # Get unique groups
        groups_list = sorted(data['group'].dropna().unique().tolist())

        if groups_list:
            # Select group
            selected_group = st.selectbox('Select a group to view its data', groups_list, key='selected_group')

            # Filter data by selected group
            filtered_data = data[data['group'] == selected_group]

            # Display group summary
            st.write(f"**Group:** {selected_group}")
            st.write(f"**Total Accounts:** {len(filtered_data)}")

            # Display filtered dataframe
            st.dataframe(filtered_data)
        else:
            st.info('No groups available.')
    else:
        st.info('No group data available.')
