import streamlit as st
from w_import import w_import
from so_import import staroddi_import
from plot_wso import sayhi

# Force wide layout for Streamlit
st.set_page_config(layout="wide")

# Custom CSS to reduce blank space
st.markdown(
    """
    <style>
    /* Reduce padding in the main content container */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
        padding-left: 0rem !important; /* Remove left padding */
        padding-right: 1rem !important;
    }
    /* Remove margin between the sidebar and main content */
    .css-1lcbmhc {
        margin-left: 0rem !important; /* Remove left margin */
        margin-right: 0rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Sidebar navigation
menu = ["Plot", "Import Winch Data", "Import Star-Oddi Data"]  # Add the new page to the menu
choice = st.sidebar.radio("Select Option", menu)

# Render the selected page
if choice == "Plot":
    sayhi()
elif choice == "Import Winch Data":
    w_import()
elif choice == "Import Star-Oddi Data":
    staroddi_import()