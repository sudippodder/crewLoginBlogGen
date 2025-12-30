import streamlit as st
import os
import sqlite3
from dotenv import load_dotenv
#from utils import go_to
import common

load_dotenv()

DATABASE_FILE = os.getenv("DATABASE_FILE")

def main():
    st.set_page_config(page_title="Template Type", layout="wide")
    conn = sqlite3.connect(DATABASE_FILE)
    cur = conn.cursor()

    #st.title("Category Management")

    qs = st.query_params
    edit_id = qs.get("id")

    st.write("---")

    # ---------- CATEGORY LIST ----------
    cur.execute("SELECT id, name FROM template_type ORDER BY id DESC")
    rows = cur.fetchall()

    st.subheader("Template Type")
    if "params" not in st.session_state:
        st.session_state.params = {}
    for r in rows:
        col1, col2, col3 = st.columns([5,1,1])

        # CLICK → GO TO PRODUCTS PAGE
        with col1:
            if st.button(r[1], key=f"tpl_{r[0]}"):
                #st.markdown(f"Navigating to template type: {r[1]} - ID: {r[0]}")
                st.session_state["params"]["template_id"] = r[0]
                st.session_state["params"]["template_name"] = r[1]
                st.session_state["params"]["current_page"] = "template_type"
                st.session_state["params"]["page"] = "template type"
                st.session_state["params"]["subpage"] = "template_list"

                # st.query_params.update({
                #     "template_id": str(r[0]),
                #     "current_page": "template_type"
                # })
                st.rerun()
