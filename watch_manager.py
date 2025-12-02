import streamlit as st

def watch_manager_view():
    st.subheader('Watch Manager')

    st.markdown('<div style="border: 1px solid #ccc; padding: 20px; border-radius: 10px; background-color: #f9f9f9;">', unsafe_allow_html=True)

    password = st.text_input('Password', type='password', key='watch_manager_password')

    if st.button('Submit', key='watch_manager_submit'):
        st.success('Watch Manager form submitted successfully!')

    st.markdown('</div>', unsafe_allow_html=True)
