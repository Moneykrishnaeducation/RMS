import streamlit as st

def file_management_view():
    st.subheader('File Management')

    st.markdown('<div style="border: 1px solid #ccc; padding: 20px; border-radius: 10px; background-color: #f9f9f9;">', unsafe_allow_html=True)

    password = st.text_input('Password', type='password', key='file_management_password')

    if st.button('Submit', key='file_management_submit'):
        st.success('File Management form submitted successfully!')

    st.markdown('</div>', unsafe_allow_html=True)
