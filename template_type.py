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
    cur.execute("SELECT id, name, slug, cslug,page_title,file_name FROM template_type ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return rows

def add_template_type(name):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO template_type (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()

def update_template_type(type_id, name,slug,cslug,page_title,file_name):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE template_type SET name=?,slug=?,cslug=?,page_title=?,file_name=? WHERE id=?",
        (name,slug,cslug,page_title,file_name, type_id)
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
    conn = common.get_row_conn()
    cur = conn.cursor()
    qs = st.query_params
    edit_id = qs.get("id")
    st.write("---")

    #st.json(st.session_state["params"]["data"])
    # ---------- CATEGORY LIST ----------
    cur.execute("SELECT id, name, slug, cslug,page_title,file_name FROM template_type ORDER BY id ASC")
    rows = cur.fetchall()
    st.subheader("Template Type")
    if "params" not in st.session_state:
        st.session_state.params = {}
    for r in rows:
        col1, col2, col3 = st.columns([5,1,1])

        with col1:
            if st.button(r['name'], key=f"tpl_{r['id']}"):
                st.session_state["params"]["template_id"] = r['id']
                st.session_state["params"]["template_name"] = r['name']
                st.session_state["params"]["current_page"] = "template_type"
                st.session_state["params"]["page"] = "template type"
                lower_title = r['name'].lower()
                
                if r['file_name'] != "" and r['file_name'] is not None:
                    replace_title = r['file_name']
                else:
                    replace_title = lower_title.replace(" ", "_")
                rdata = dict(r) 
                #st.markdown(f"---{replace_title}---{rdata}")
                # st.json(rdata)
                # st.stop()

                if replace_title == "case_study":
                    #st.session_state["params"]["subpage"] = "casestudy_form"
                    st.session_state["params"]["subpage"] = "template_list"
                elif replace_title == "success_story":
                    #st.session_state["params"]["subpage"] = "successstory_form"
                    st.session_state["params"]["subpage"] = "successstory_template_list"
                elif replace_title == "articles":
                    st.session_state["params"]["subpage"] = "template_for_articles"    
                    
                elif replace_title == "seo_page":
                    st.session_state["params"]["subpage"] = "ai_blog_template"    
                else:
                    st.session_state["params"]["subpage"] = 'd_page'
                    st.session_state["params"]["d_page"] = 1
                    st.session_state["params"]["data"] = rdata
                st.rerun()

    #st.json(st.session_state["params"]["data"])

def show_template_type():
    st.subheader("📂 Template Types")

    # -----------------------
    # ADD TEMPLATE TYPE
    # -----------------------
    all_items = common.file_type_exist_check()
    st.json(all_items)
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
    col1, col2, col3,col4,col5,col6,col7 = st.columns([6, 2, 2,2,2,2,2])
    with col1:
        st.markdown(f"**Title**")
    with col2:
        st.markdown(f"**Slug**")
    with col3:
        st.markdown(f"**Content List Slug**") 
    with col4:
        st.markdown(f"**Page title**") 
    with col5:
        st.markdown(f"**File**")          
    with col6:
        st.markdown(f"**Edit**")  
    with col7:
        st.markdown(f"**Delete**")          
    for row in types:
        

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
                updated_slug = st.text_input(
                    "Edit Slug",
                    value=row["slug"],
                    key=f"edit_slug_{row['id']}"
                )
            with col3:
                updated_cslug = st.text_input(
                    "Edit Content Slug",
                    value=row["cslug"],
                    key=f"edit_cslug_{row['id']}"
                )   
            with col4:
                updated_page = st.text_input(
                    "Edit Page Title",
                    value=row["page_title"],
                    key=f"edit_page_{row['id']}"
                )        
            with col5:
                updated_file = st.text_input(
                    "Edit File Name",
                    value=row["file_name"],
                    key=f"edit_file_{row['id']}"
                )       
            with col6:
                if st.button("💾 Save", key=f"save_{row['id']}"):
                    update_template_type(row["id"], updated_name,updated_slug,updated_cslug,updated_page,updated_file)
                    st.session_state.edit_type_id = None
                    st.success("Updated")
                    st.rerun()

            with col7:
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
                st.markdown(f"**{row['slug']}**")
            with col3:
                st.markdown(f"**{row['cslug']}**")  
            with col4:
                st.markdown(f"**{row['page_title']}**")  
            with col5:
                st.markdown(f"**{row['file_name']}**")    
            with col6:
                if st.button("✏ Edit", key=f"edit_{row['id']}"):
                    st.session_state.edit_type_id = row["id"]
                    st.rerun()

            with col7:
                if st.button("🗑 Delete", key=f"delete_{row['id']}"):
                    delete_template_type(row["id"])
                    st.success("Deleted")
                    st.rerun()
