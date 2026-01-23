import os
import time
import streamlit as st
import json
import sqlite3
from dotenv import load_dotenv
load_dotenv()

DATABASE_FILE = os.getenv("DATABASE_FILE")

c = sqlite3.connect(DATABASE_FILE)

def pipe_list(text):
    return [i.strip() for i in text.split("|") if i.strip()]

def get_section(data, idx):
    try:
        return "|".join(data["content_structure"][idx]["fields"])
    except:
        return ""



def main():
    user = st.session_state['user_info']
    user_id = user['id']
    params = st.session_state['params'] if 'params' in st.session_state else {}
    subpage = params.get("subpage", "") if "subpage" in params else ""
    template_type_id = params.get("template_id", "") if "template_id" in params else ""
    #st.json(params)
    #st.markdown(f"---{template_type_id}")

    template_id = st.session_state.get("template_id", "")
    c = sqlite3.connect(DATABASE_FILE)
    conn = c.cursor()
    existing = {}
    if template_id:
        row = conn.execute(
            "SELECT data_json FROM templates_form WHERE id=?",
            (template_id,)
        ).fetchone()
        if row:
            existing = json.loads(row[0])

    st.title("🧩 Case Study Template Form")
    if st.button("⬅ Back to List"):
        st.session_state["params"]["current_page"] = "template_type"
        st.session_state["params"]["page"] = "template type"
        st.session_state["params"]["subpage"] = "template_list"
        st.rerun()
    with st.form("template_form"):
        template_title = st.text_input(
            "Template Title",
            existing.get("template_title", "")
        )

        use_case = st.text_input(
            "Use Case (, separated)",
            existing.get("use_case", "")
        )

        version = st.text_input(
            "Version",
            existing.get("version", "v1.0")
        )

        audience = st.text_area(
            "Audience (| separated)",
            "|".join(existing.get("audience", []))
        )

        st.subheader("Content Structure")

        meta = st.text_area("Meta Fields (| separated)", get_section(existing, 0))
        header = st.text_area("Header Fields (| separated)", get_section(existing, 1))
        intro = st.text_area("Introduction Fields (| separated)", get_section(existing, 2))
        main = st.text_area("Main Section Fields (| separated)", get_section(existing, 3))
        conclusion = st.text_area("Conclusion Fields (| separated)", get_section(existing, 4))
        cta = st.text_area("CTA Fields (| separated)", get_section(existing, 5))

        st.subheader("Tone & Style")

        voice = st.text_input(
            "Voice (, separated)",
            existing.get("tone_style", {}).get("voice", "")
        )

        readability = st.text_input(
            "Readability (, separated)",
            existing.get("tone_style", {}).get("readability", "")
        )

        avoid = st.text_area(
            "Avoid (| separated)",
            "|".join(existing.get("tone_style", {}).get("avoid", []))
        )

        submitted = st.form_submit_button("💾 Save Template")



    if submitted:
        output = {
            "template_title": template_title,
            "use_case": use_case,
            "version": version,
            "audience": pipe_list(audience),
            "content_structure": [
                {"section": "Meta Information", "fields": pipe_list(meta)},
                {"section": "Header", "fields": pipe_list(header)},
                {"section": "Introduction", "fields": pipe_list(intro)},
                {"section": "Main Sections", "fields": pipe_list(main)},
                {"section": "Conclusion", "fields": pipe_list(conclusion)},
                {"section": "CTA", "fields": pipe_list(cta)},
            ],
            "tone_style": {
                "voice": voice,
                "readability": readability,
                "avoid": pipe_list(avoid)
            }
        }

        if template_id:
            conn.execute("""
                UPDATE templates_form
                SET template_title=?, use_case=?, version=?, data_json=?
                WHERE id=?
            """, (
                template_title,
                use_case,
                version,
                json.dumps(output, indent=2),
                template_id
            ))
            st.success("Template updated")
        else:
            conn.execute("""
                INSERT INTO templates_form (template_type,template_title, use_case, version, data_json, user_id)
                VALUES (?,?,?,?,?,?)
            """, (
                template_type_id,
                template_title,
                use_case,
                version,
                json.dumps(output, indent=2),
                user_id
            ))
            st.success("Template created")

        c.commit()
        
        st.session_state["params"]["current_page"] = "template_type"
        st.session_state["params"]["page"] = "template type"
        st.session_state["params"]["subpage"] = "template_list"
        time.sleep(2)
        st.rerun()
