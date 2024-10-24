import streamlit as st
from components.transaction_form import render_transaction_form
from components.dashboard import render_dashboard

# Page config
st.set_page_config(
    page_title="Personal Finance Manager",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    # Sidebar
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Dashboard", "Add Transaction"])
    
    # Theme toggle
    theme = st.sidebar.select_slider(
        "Theme",
        options=["Light", "Dark"],
        value="Dark"
    )
    
    # Main content
    st.title("Personal Finance Manager")
    
    if page == "Dashboard":
        render_dashboard()
    else:
        render_transaction_form()

if __name__ == "__main__":
    main()
