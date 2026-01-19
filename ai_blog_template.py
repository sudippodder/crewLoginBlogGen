import streamlit as st
import os
import sqlite3
from dotenv import load_dotenv
import common

load_dotenv()

DATABASE_FILE = os.getenv("DATABASE_FILE")

def clone_template(template_id, user_id):
    conn = sqlite3.connect(DATABASE_FILE)
    cur = conn.cursor()

    # Fetch original template
    cur.execute("""
        SELECT template_title, data_json,template_type,version
        FROM templates_form
        WHERE id=? AND user_id=?
    """, (template_id, user_id))

    row = cur.fetchone()
    if not row:
        conn.close()
        return False

    original_name, data_json, template_type, version = row
    new_name = f"{original_name} (Copy)"

    from datetime import datetime
    now = datetime.utcnow().isoformat()

    # Insert cloned row
    cur.execute("""
        INSERT INTO templates_form (user_id, template_title, data_json, created_at, updated_at, template_type, version)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, new_name, data_json, now, now, template_type, version))

    conn.commit()
    conn.close()
    return True

def main():
    st.set_page_config(page_title="Template Type", layout="wide")
    cur = sqlite3.connect(DATABASE_FILE)
    conn = cur.cursor()
    user = st.session_state['user_info']
    user_id = user['id']
    params = st.session_state['params'] if 'params' in st.session_state else {}
    subpage = params.get("subpage", "") if "subpage" in params else ""
    template_type_id = params.get("template_id", "") if "template_id" in params else ""

    qs = st.query_params
    edit_id = qs.get("id")
    st.write("---")
    st.title("📋 Blog Template List")
    col1, col2, col3 = st.columns([2, 1, 6])
    with col1:
        if st.button("➕ Create New Blog Template"):
            st.session_state["params"]["current_page"] = "template_type"
            st.session_state["params"]["page"] = "template type"
            st.session_state["params"]["subpage"] = "ai_blog_form"
            st.session_state["params"]["template_frm_id"] = ""
            st.rerun()
    with col2:
        if st.button("Back"):
            st.session_state["params"]["current_page"] = "template_type"
            st.session_state["params"]["page"] = "template type"
            st.session_state["params"]["subpage"] = ""
            st.rerun()

    rows = conn.execute("""
        SELECT id, template_title, use_case, version
        FROM templates_form where template_type=? and user_id=?
        ORDER BY id DESC
    """, (template_type_id, user_id)).fetchall()

    if rows:
        h1, h2, h3, h4, h5 = st.columns([3, 4, 2, 1, 1])

        h1.markdown("**Title**")
        h2.markdown("**Version**")
        h3.markdown("**Clone**")
        h4.markdown("**Edit**")
        h5.markdown("**Delete**")
        for tid, title, use_case, version in rows:
            c1, c2, c3, c4, c5 = st.columns([3,4,2,1,1])

            c1.write(title)
            c2.write(version)

            if c3.button("📄 Clone", key=f"clone_{tid}"):
                clone_template(tid, user_id)
                st.success(f"Template '{title}' cloned!")
                st.rerun()
            if c4.button("✏ Edit", key=f"edit_{tid}"):
                st.session_state["params"]["current_page"] = "template_type"
                st.session_state["params"]["page"] = "template type"
                st.session_state["params"]["subpage"] = "ai_blog_form"
                st.session_state["params"]["template_frm_id"] = tid
                st.rerun()

            if c5.button("🗑 Delete", key=f"del_{tid}"):
                conn.execute("DELETE FROM templates_form WHERE id=?", (tid,))
                cur.commit()
                st.success("Template deleted")
                st.rerun()
    else:
        st.info("No templates found. Please create a new blog template.")
