import streamlit as st
import pandas as pd
import io

def reports_view(data):
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

    st.subheader('Reports')
    # Add some report elements, e.g., tables and charts
    if 'group' in data.columns:
        groups = data.groupby('group').agg(count=('login', 'count'), balance_sum=('balance', 'sum'), equity_sum=('equity', 'sum'))
        groups = groups.sort_values('count', ascending=False)
        st.dataframe(groups.reset_index().rename(columns={'group': 'Group'}).head(20))
        st.bar_chart(groups['count'].head(20))

    # Export filtered results
    buf = io.StringIO()
    data.to_csv(buf, index=False)
    st.download_button('Download CSV', data=buf.getvalue(), file_name='accounts.csv', mime='text/csv')
