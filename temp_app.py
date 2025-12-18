from urllib import response
import streamlit as st
import sqlite3
import os
from datetime import datetime
import json
#import openai  # or your preferred LLM
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()
# ----------------------------
# DATABASE INITIALIZATION
# ----------------------------
openai_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY")
conn = sqlite3.connect("app.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    template_title TEXT,
    audience TEXT,
    tone_style TEXT,
    content_structure TEXT,
    notes_for_editors TEXT,
    expected_length TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS contents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    topic TEXT,
    template_id INTEGER,
    generated_content TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
""")

conn.commit()

# ----------------------------
# BASIC LOGIN SYSTEM
# ----------------------------
def login_user(username, password):
    cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    return cursor.fetchone()

def register_user(username, password):
    try:
        cursor.execute("INSERT INTO users(username, password) VALUES (?,?)", (username, password))
        conn.commit()
        return True
    except:
        return False

# ----------------------------
# JSON → HTML Renderer
# ----------------------------
def json_to_html(json_data):
    if isinstance(json_data, str):
        try:
            json_data = json.loads(json_data)
        except:
            return "<p style='color:red;'>Invalid JSON Format</p>"

    html = "<table border='1' style='border-collapse: collapse; width: 100%;'>"
    for key, value in json_data.items():
        html += f"<tr><th style='padding:6px; background:#f2f2f2;'>{key}</th>"
        html += f"<td style='padding:6px;'>{value}</td></tr>"
    html += "</table>"
    return html

# ----------------------------
# LLM GENERATION
# ----------------------------
def generate_content(topic, template_json):
    #openai.api_key = openai_key
    client = OpenAI()
    prompt = f"""
Generate detailed content on the topic: "{topic}"

Template:
Audience: {template_json['audience']}
Tone Style: {template_json['tone_style']}
Content Structure: {template_json['content_structure']}
Expected Length: {template_json['expected_length']}
Notes for Editors: {template_json['notes_for_editors']}

Format your response as well-structured headings.
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    # response = openai.ChatCompletion.create(
    #     model="gpt-4o-mini",
    #     messages=[{"role": "user", "content": prompt}]
    # )

    #return response["choices"][0]["message"]["content"]
    return response.choices[0].message.content

# ----------------------------
# SIDEBAR NAVIGATION
# ----------------------------
def sidebar_menu():
    return st.sidebar.radio("Navigation", ["Dashboard", "Templates", "Contents", "Generate Content", "Logout"])

# ----------------------------
# TEMPLATES PAGE (CRUD)
# ----------------------------
def template_page(user_id):
    st.header("Template Management")

    st.subheader("Create / Edit Template")

    template_id = st.session_state.get("edit_template_id", None)

    if template_id:
        cursor.execute("SELECT * FROM templates WHERE id=? AND user_id=?", (template_id, user_id))
        t = cursor.fetchone()
        title_default = t[2]
        aud_default = t[3]
        tone_default = t[4]
        structure_default = t[5]
        notes_default = t[6]
        length_default = t[7]
    else:
        title_default = aud_default = tone_default = structure_default = notes_default = length_default = ""

    template_title = st.text_input("Template Title", value=title_default)
    audience = st.text_input("Audience (use | for multiple)", value=aud_default)
    tone_style = st.text_input("Tone Style (use | for multiple)", value=tone_default)
    content_structure = st.text_area("Content Structure", value=structure_default)
    notes_for_editors = st.text_area("Notes for Editors", value=notes_default)
    expected_length = st.text_input("Expected Length", value=length_default)

    if st.button("Save Template"):
        if template_id:
            cursor.execute("""
                UPDATE templates SET template_title=?, audience=?, tone_style=?, content_structure=?, notes_for_editors=?, expected_length=?
                WHERE id=? AND user_id=?
            """, (template_title, audience, tone_style, content_structure, notes_for_editors, expected_length, template_id, user_id))
            st.success("Template updated successfully!")
            st.session_state.edit_template_id = None
        else:
            cursor.execute("""
                INSERT INTO templates (user_id, template_title, audience, tone_style, content_structure, notes_for_editors, expected_length)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, template_title, audience, tone_style, content_structure, notes_for_editors, expected_length))
            st.success("Template created successfully!")

        conn.commit()

    st.subheader("Your Templates")
    cursor.execute("SELECT * FROM templates WHERE user_id=?", (user_id,))
    rows = cursor.fetchall()

    for row in rows:
        st.write(f"### {row[2]}")
        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"Edit {row[0]}"):
                st.session_state.edit_template_id = row[0]
                st.rerun()
        with col2:
            if st.button(f"Delete {row[0]}"):
                cursor.execute("DELETE FROM templates WHERE id=? AND user_id=?", (row[0], user_id))
                conn.commit()
                st.warning("Template deleted")
                st.rerun()

# ----------------------------
# CONTENT CRUD PAGE
# ----------------------------
def content_page(user_id):
    st.header("Generated Content List")

    cursor.execute("""
        SELECT contents.id, contents.topic, templates.template_title, contents.generated_content
        FROM contents
        JOIN templates ON contents.template_id = templates.id
        WHERE contents.user_id=?
    """, (user_id,))

    rows = cursor.fetchall()

    for row in rows:
        st.write(f"### {row[1]} — ({row[2]})")

        if st.button(f"View {row[0]}"):
            st.markdown(row[3])

        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"Delete {row[0]}"):
                cursor.execute("DELETE FROM contents WHERE id=?", (row[0],))
                conn.commit()
                st.warning("Deleted successfully")
                st.rerun()

# ----------------------------
# GENERATE CONTENT PAGE
# ----------------------------
def generate_content_page(user_id):
    st.header("Generate Content")

    topic = st.text_input("Enter Topic")

    cursor.execute("SELECT id, template_title FROM templates WHERE user_id=?", (user_id,))
    templates = cursor.fetchall()

    template_select = st.selectbox("Choose Template", templates, format_func=lambda x: x[1])

    if st.button("Generate"):
        template_id = template_select[0]

        cursor.execute("SELECT * FROM templates WHERE id=?", (template_id,))
        t = cursor.fetchone()

        template_json = {
            "template_title": t[2],
            "audience": t[3].split("|"),
            "tone_style": t[4].split("|"),
            "content_structure": t[5].split("|"),
            "notes_for_editors": t[6].split("|"),
            "expected_length": t[7].split("|"),
        }

        st.subheader("Template (JSON View)")
        st.markdown(json_to_html(template_json), unsafe_allow_html=True)

        generated = generate_content(topic, template_json)
        st.subheader("Generated Content")
        st.markdown(generated)

        if generated and st.button("Save Content"):
            cursor.execute("""
                INSERT INTO contents (user_id, topic, template_id, generated_content)
                VALUES (?, ?, ?, ?)
            """, (user_id, topic, template_id, generated))
            conn.commit()
            st.success("Content saved!")

# ----------------------------
# MAIN APP
# ----------------------------
def main():
    st.title("AI Content Builder App")

    if "user" not in st.session_state:
        choice = st.selectbox("Login or Register", ["Login", "Register"])

        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if choice == "Login":
            if st.button("Login"):
                user = login_user(username, password)
                if user:
                    st.session_state.user = user
                    st.rerun()
                else:
                    st.error("Invalid login")

        else:
            if st.button("Register"):
                if register_user(username, password):
                    st.success("User registered! Please login.")
                else:
                    st.error("Username exists")

        return

    user = st.session_state.user
    user_id = user[0]

    page = sidebar_menu()

    if page == "Dashboard":
        st.header("Dashboard")
        st.info("Welcome! Use the sidebar to manage templates and content.")

    elif page == "Templates":
        template_page(user_id)

    elif page == "Contents":
        content_page(user_id)

    elif page == "Generate Content":
        generate_content_page(user_id)

    elif page == "Logout":
        del st.session_state["user"]
        st.rerun()


if __name__ == "__main__":
    main()
