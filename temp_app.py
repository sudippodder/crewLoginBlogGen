from urllib import response
import common
import streamlit as st
import sqlite3
import os
from datetime import datetime
import json
import zerogpt_api
import highlight_ai_segments
import paragraph_editor
#import openai  # or your preferred LLM
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()
# ----------------------------
# DATABASE INITIALIZATION
# ----------------------------
openai_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY")
DATABASE_FILE = os.getenv("DATABASE_FILE")
conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
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
def update_content_field_by_id(content_id, field_name, new_value):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    #clean_template = sanitize_for_json(new_value)
    #json_string = json.dumps(clean_template, ensure_ascii=False)
    if isinstance(new_value, (dict, list)):
        new_value = json.dumps(new_value, ensure_ascii=False)
    cursor.execute(f"UPDATE contents SET {field_name} = ? WHERE id=? ", (new_value, content_id))
    conn.commit()
    conn.close()


def select_content_field_by_id(content_id, field_name):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    cursor.execute(f"SELECT {field_name} FROM contents WHERE id=?", (content_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None


def content_page(user_id):
    st.header("Generated Content List cp")
    conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
    cursor = conn.cursor()

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

def sanitize_for_json(obj):
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(i) for i in obj]
    elif isinstance(obj, str):
        return (
            obj.replace("\\", "\\\\")
               .replace("\n", "\\n")
               .replace("\r", "")
               .replace("\t", " ")
        )
    else:
        return obj

def get_templates_by_type(type_id):
    conn = common.get_row_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, template_title, data_json
        FROM templates_form
        WHERE template_type = ?
        ORDER BY template_title
    """, (type_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows
def content_list(user_id):
    if st.button("Back"):
        st.session_state["params"]["current_page"] = "content_list"
        st.session_state["params"]["page"] = "content list"
        st.session_state["params"]["subpage"] = ""
        st.rerun()
    st.header("Generated Content List ")
    
    #st.json(st.session_state["params"])
    
    #st.write(f"### {st.session_state["params"]["template_name"]} ")
    if st.session_state["params"]["template_id"] :
        template_types = get_templates_by_type(st.session_state["params"]["template_id"])
        type_map = {row[1]: row[0] for row in template_types}
        type_names = list(type_map.keys())
        selected_type_name = st.selectbox(
            "Template Type",
            ["-- Select Type --"] + type_names
        )
      
    if selected_type_name !=  "-- Select Type --" :
        selected_type_id = type_map[selected_type_name]
        #st.markdown(f"{selected_type_id}")
        cursor.execute("""
            SELECT c.id, c.topic, c.generated_content, u.username, c.created_at, c.humanize_content
            FROM contents as c left join users as u on  c.user_id=u.id
            WHERE c.template_id=?
        """, (selected_type_id,))

        rows = cursor.fetchall()
        st.markdown("""
        <style>
        .rounded-card {
            width: 100%;
            box-sizing: border-box;
            border: 1px solid #e6e6e6;
            border-radius: 14px;
            padding: 16px;
            margin-bottom: 16px;
            background-color: #ffffff;
        }
                            /* Root container */
        .json-container {
            font-family: Arial, sans-serif;
            padding: 20px;
            border-radius: 12px;
            border: 1px solid #e0e0e0;
        }

        /* Remove default bullets */
        .json-container ul {
            list-style: none;
            padding-left: 20px;
            margin: 6px 0;
        }

        /* List items */
        .json-container li {
            margin: 6px 0;
            padding: 6px 10px;
            border-radius: 6px;
            border: 1px solid #f0f0f0;
        }

        /* Keys */
        .json-container strong {
            color: #ff4b4b;
            font-weight: 600;
        }

        /* Nested indentation guide */
        .json-container ul ul {
            border-left: 2px solid #ff4b4b;
            margin-left: 10px;
            padding-left: 12px;
        }
        </style>
        """, unsafe_allow_html=True)
        
        if rows:
            for row in rows:
                with st.container():
                    # st.markdown('<div class="rounded-card">', unsafe_allow_html=True)
                    id, topic, generated_content, user_name, created_at,humanize_content = row
                    

                    st.write(f"### Created By : {user_name} ")
                    datetime_object = datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
                    created_date = datetime_object.strftime("%B %d, %Y")
                    #created_date = created_at.strftime("%B %d, %Y")
                    st.write(f"### Created At :  {created_date} ")
                    

                    col1, col2 = st.columns([6, 1])
                    tone = f"tone_{id}"
                    tone = st.session_state.get(f"selected_tone_{id}", None)
                    
                    human_gen_check = False
                    check_btn = False
                    with col1:
                        jcol1, jcol2, jcol3, jcol4 = st.columns([1.2, 1.3, 1.5, 2])
                        with jcol1:
                            #st.markdown('<div class="my-special-button">', unsafe_allow_html=True)
                            view_btn = st.button("View Original Content", key=f"view_{id}")
                        with jcol2:    
                            check_btn = st.button("View Humanize Content", key=f"check_{id}")
                        with jcol3:    
                            human_gen_btn = st.button("Humanize Content Generator", key=f"human_gen_{id}")
                        # with jcol4:    
                        #     human_gen_check = st.button("Humanize Generator Check", key=f"human_gen_check_{id}")        
                          
                        if view_btn:
                            if generated_content:
                                try:
                                    generated_content = json.loads(generated_content)
                                except json.JSONDecodeError as e:
                                    st.error("Stored template is corrupted.")
                                    print("JSON ERROR:", e)
                                    return
                                for section, content in generated_content.items():
                                    with st.expander(section.title(), expanded=True):
                                        content = common.unescape_text(content)
                                        st.markdown(f"{content}", unsafe_allow_html=True)
                                
                            else:
                                st.info("No generated content available.")
                        elif check_btn:
                            if humanize_content:
                                humanize_content = json.loads(humanize_content)
                                
                                highlight_ai_segments.display_highlighted_text(humanize_content, html_view=True)
                                # try:
                                #     generated_content = json.loads(humanize_content)
                                # except json.JSONDecodeError as e:
                                #     st.error("Stored template is corrupted.")
                                #     print("JSON ERROR:", e)
                                #     return
                                #html_content = common.ai_to_html(humanize_content)
                                #st.markdown(f'<div class="json-container">{html_content}</div>', unsafe_allow_html=True)
                                
                            else:
                                st.info("No generated content available.")
                        #elif (human_gen_btn and tone) or st.session_state.get(f"selected_tone_{id}", None):        
                        elif (human_gen_btn):
                            open_form(id, generated_content)
                            
                        elif human_gen_check:
                            if generated_content:
                                humanized = zerogpt_api.humanize_content(generated_content)
                                st.markdown("### Humanized Content")
                                st.markdown(humanized)
                            else:
                                st.info("No generated content available.")        
                    with col2:
                        if st.button("Delete", key=f"delete_{id}"):
                            cursor.execute("DELETE FROM contents WHERE id=?", (id,))
                            conn.commit()
                            st.warning("Deleted successfully")
                            st.rerun()



                st.divider()
                #st.json(generated_content)


        else:
            st.info("No content generated yet.")
    else:
        st.info("Please select template type.")    

# ----------------------------
# GENERATE CONTENT PAGE
# ----------------------------
def get_template_types_by_id(template_id):

    cursor.execute("SELECT id, name FROM template_type ORDER BY name")
    rows = cursor.fetchall()
    conn.close()
    return rows

def generate_content_page(user_id):
    st.header("Generate Content")

    topic = st.text_input("Enter Topic")

    cursor.execute("SELECT id, template_title FROM templates WHERE user_id=?", (user_id,))
    templates = cursor.fetchall()

    template_select = st.selectbox("Choose Template", templates, format_func=lambda x: x[1])

    if 'bit' not in st.session_state:
        st.session_state['bit'] = 0
    bit = st.session_state['bit']
    
    if st.button("Generate") or bit == 2:
        with st.spinner("⏳ Generating content..."):
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

            st.session_state['bit'] = 2
            if generated and st.button("Save Content"):

                st.session_state['bit'] = 1
                cursor.execute("""
                    INSERT INTO contents (user_id, topic, template_id, generated_content)
                    VALUES (?, ?, ?, ?)
                """, (user_id, topic, template_id, generated))
                conn.commit()
                st.success("Content saved!")
                st.rerun()


@st.dialog("User Form", width="medium")
def open_form(id, generated_content=None):
    st.markdown("""
<style>
.case-study {
    background: #f9fafc;
    padding: 25px;
    border-radius: 12px;
    border: 1px solid #e5e7eb;
    font-family: Arial, sans-serif;
    line-height: 1.6;
}

.case-study strong {
    color: #ff4b4b;
}

.case-study ul {
    margin-bottom: 15px;
}
</style>
""", unsafe_allow_html=True)
    with st.form("popup_form"):
        try:
            generated_content = json.loads(generated_content)
        except json.JSONDecodeError as e:
            st.error("Stored template is corrupted.")
            print("JSON ERROR:", e)
            return
        generated_content = common.json_to_html(generated_content)
        html_content = common.html_to_ai(generated_content)

        html_content = html_content.replace("\\n", "\n")
        html_content = html_content.replace("\\*\\*", "**")

        edited_text = st.text_area(
            "",
            value=html_content,
            height=400,
            label_visibility="collapsed"
        )
        
        # tone = common.humanizer_tone(id)
        # st.session_state[f"selected_tone_{id}"] = tone
        hm_con = select_content_field_by_id(id, "humanize_content")

        if hm_con:
            button_label = "Regenerate Humanized Content"
        else:
            button_label = "Generate Humanized Content"

        if st.form_submit_button(button_label, key=f"human_gen_submit_{id}"):
            
            with st.spinner("Generating..."):
                #result = common.run_humanizer(edited_text, tone)
                #result = common.professional_humanizer_pipeline(edited_text)
                #result = common.humanize_content(edited_text)
                #result = common.adaptive_humanizer(edited_text, threshold=15)
                result, final_score, history = common.parallel_adaptive_pipeline(edited_text)
                print("FINAL SCORE:", final_score)
                print("HISTORY:", history)
                humanized = zerogpt_api.check_ai_content(result)
                update_content_field_by_id(id, "humanize_content", humanized)
                st.session_state.detection_humanized = humanized
            
        else:
            hm_con = json.loads(hm_con) if hm_con else None
            st.session_state.detection_humanized = hm_con
     
    if "detection_humanized" in st.session_state and st.session_state.detection_humanized is not None:
        st.markdown("### Humanized Content")
        #paragraph_editor.display_paragraphs_with_detection(st.session_state.detection_humanized)
        highlight_ai_segments.display_highlighted_text(st.session_state.detection_humanized, html_view=True)
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
