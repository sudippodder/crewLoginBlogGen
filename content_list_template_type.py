import streamlit as st
import os
import sqlite3
from dotenv import load_dotenv
#from utils import go_to
import common

load_dotenv()

DATABASE_FILE = os.getenv("DATABASE_FILE")


def get_conn():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def get_template_types():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM template_type ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return rows

def add_template_type(name):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO template_type (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()

def update_template_type(type_id, name):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE template_type SET name=? WHERE id=?",
        (name, type_id)
    )
    conn.commit()
    conn.close()

def delete_template_type(type_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM template_type WHERE id=?",
        (type_id,)
    )
    conn.commit()
    conn.close()

def main():
    st.set_page_config(page_title="Template Type", layout="wide")
    conn = sqlite3.connect(DATABASE_FILE)
    cur = conn.cursor()
    qs = st.query_params
    edit_id = qs.get("id")
    st.write("---")
    # ---------- CATEGORY LIST ----------
    cur.execute("SELECT id, name,slug,cslug FROM template_type ORDER BY id ASC")
    rows = cur.fetchall()
    st.subheader("Template Type > Content List")
    if "params" not in st.session_state:
        st.session_state.params = {}
    for r in rows:
        col1, col2, col3 = st.columns([5,1,1])

        with col1:
            if st.button(r[1], key=f"tpl_{r[0]}"):
                st.session_state["params"]["template_id"] = r[0]
                st.session_state["params"]["template_name"] = r[1]
                st.session_state["params"]["current_page"] = "content_list"
                st.session_state["params"]["page"] = "content list"
                lower_title = r[1].lower()
                replace_title = lower_title.replace(" ", "_")
                
                replace_title = 'con_' + replace_title
                # st.markdown(f"---{replace_title}---{r[3]}")
                # st.stop()
                if replace_title == r[3]:
                    st.session_state["params"]["subpage"] = r[3]    
                else:
                    st.session_state["params"]["subpage"] = r[3]  
                st.rerun()



def show_template_type():
    st.subheader("📂 Template Types")

    # -----------------------
    # ADD TEMPLATE TYPE
    # -----------------------
    with st.form("add_template_type"):
        new_type = st.text_input("New Template Type")
        submitted = st.form_submit_button("➕ Add")

        if submitted:
            if new_type.strip():
                add_template_type(new_type.strip())
                st.success("Template type added")
                st.rerun()
            else:
                st.warning("Name cannot be empty")

    st.divider()

    # -----------------------
    # LIST TEMPLATE TYPES
    # -----------------------
    types = get_template_types()

    for row in types:
        col1, col2, col3 = st.columns([6, 2, 2])

        # -----------------------
        # EDIT MODE
        # -----------------------
        edit_type_id = st.session_state.get("edit_type_id", None)
        
        if "edit_type_id" in st.session_state and edit_type_id == row["id"]:
            with col1:
                updated_name = st.text_input(
                    "Edit Name",
                    value=row["name"],
                    key=f"edit_input_{row['id']}"
                )

            with col2:
                if st.button("💾 Save", key=f"save_{row['id']}"):
                    update_template_type(row["id"], updated_name)
                    st.session_state.edit_type_id = None
                    st.success("Updated")
                    st.rerun()

            with col3:
                if st.button("❌ Cancel", key=f"cancel_{row['id']}"):
                    st.session_state.edit_type_id = None
                    st.rerun()

        # -----------------------
        # VIEW MODE
        # -----------------------
        else:
            with col1:
                st.markdown(f"**{row['name']}**")

            with col2:
                if st.button("✏ Edit", key=f"edit_{row['id']}"):
                    st.session_state.edit_type_id = row["id"]
                    st.rerun()

            with col3:
                if st.button("🗑 Delete", key=f"delete_{row['id']}"):
                    delete_template_type(row["id"])
                    st.success("Deleted")
                    st.rerun()
