import streamlit as st
from crew_pipeline_human import run_pipeline
from zerogpt_api import check_ai_content
import sqlite3
import os
from paragraph_editor import display_paragraphs_with_detection
from highlight_ai_segments import display_highlighted_text
import json
from dotenv import load_dotenv
import common
load_dotenv()

DATABASE_FILE = os.getenv("DATABASE_FILE")

def load_record(record_id):

    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM content_history WHERE id=?", (record_id,))
    row = c.fetchone()
    conn.close()
    return row

#from tools.serper_tool import SerperTool
def redirect_to_edit(record_id):
    st.query_params.update({"refresh": "true", "page": "content", "id": record_id, "mode": "edit"})
    st.rerun()

def save_output_to_db(topic, researcher_goal, researcher_backstory,
                      writer_goal, writer_backstory,
                      editor_goal, editor_backstory,
                      final_output, detection_result):
    user = st.session_state['user_info']
    user_id = user['id']
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()

    c.execute("""
        INSERT INTO content_history (
            topic, researcher_goal, researcher_backstory,
            writer_goal, writer_backstory,
            editor_goal, editor_backstory,
            final_output, detection_result,
            user_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        topic,
        researcher_goal, researcher_backstory,
        writer_goal, writer_backstory,
        editor_goal, editor_backstory,
        final_output, detection_result,
        user_id
    ))

    conn.commit()

    new_id = c.lastrowid
    conn.close()
    return new_id
def convert_to_single_line(posts):
    res = []

    for post in posts:
        res.append(post[1])  # Assuming the text is in the second column

    return res

def generate_content_page():
    params = st.query_params
    mode = params.get("mode", None)
    user = st.session_state['user_info']
    user_id = user['id']
    record_id = params.get("id", None)
    row = [None] * 10  # Default empty row with 8 elements
    if mode == "edit" and record_id:
        row = load_record(record_id)
    elif st.session_state.get('spage', '') == 'gencontent' and st.session_state.get('content_id', None):
        row = load_record(st.session_state.get('content_id'))

    st.title("✍️ Generate AI Blog Content")
    Tones = common.get_custom_tone(user_id)
    if Tones is not None and len(Tones) > 0:
        single_t = convert_to_single_line(Tones)
    else:
        single_t = None


    st.dataframe({'Tones':common.get_all_personalities()})
    topic = st.text_input("Enter your topic:", value=(row and row[1] if row and row[1] is not None else ""), placeholder="e.g. AI tools for marketing")

    with st.expander("Researcher Settings", expanded=True):
        researcher_goal = st.text_area("Goal", value=(row and row[2] if row and row[2] is not None else "Find and summarize useful content for the given topic."), placeholder="Find and summarize useful content for the given topic.")
        researcher_backstory = st.text_area("Backstory", value=(row and row[3] if row and row[3] is not None else "You're great at finding relevant sources."), placeholder="You're great at finding relevant sources.")
    with st.expander("Writer Settings", expanded=True):
        writer_goal = st.text_area("Goal", value=(row and row[4] if row and row[4] is not None else "Write a detailed, SEO-friendly blog post using the research."), placeholder="Write a detailed, SEO-friendly blog post using the research.")
        writer_backstory = st.text_area("Backstory", value=(row and row[5] if row and row[5] is not None else "You're skilled at clarity and engagement."), placeholder="You're skilled at clarity and engagement.")
    with st.expander("Editor Settings", expanded=True):
        editor_goal = st.text_area("Goal", value=(row and row[6] if row and row[6] is not None else "Polish and refine the blog content for tone, clarity, and grammar."), placeholder="Polish and refine the blog content for tone, clarity, and grammar.")
        editor_backstory = st.text_area("Backstory", value=(row and row[7] if row and row[7] is not None else "You ensure it reads naturally and maintains tone."), placeholder="You ensure it reads naturally and maintains tone.")

    if "generated_content" not in st.session_state:
        st.session_state.generated_content = None
    if "detection_result" not in st.session_state:
        st.session_state.detection_result = None

      # --- Initialize session state ---
    st.session_state.setdefault("show_editor", False)
    st.session_state.setdefault("editable_text", "")

    if st.button("🚀 Generate Content"):


        missing_fields = []
        if not topic.strip():
            missing_fields.append("Topic")
        if not researcher_goal.strip():
            missing_fields.append("Researcher Goal")
        if not researcher_backstory.strip():
            missing_fields.append("Researcher Backstory")
        if not writer_goal.strip():
            missing_fields.append("Writer Goal")
        if not writer_backstory.strip():
            missing_fields.append("Writer Backstory")
        if not editor_goal.strip():
            missing_fields.append("Editor Goal")
        if not editor_backstory.strip():
            missing_fields.append("Editor Backstory")

        if missing_fields:
            st.warning(f"Please fill out all required fields: {', '.join(missing_fields)}")
            st.stop()



        if topic.strip():
            with st.spinner("🤖 Generating content..."):
                try:
                    res, task_description = run_pipeline(
                        topic=topic,
                        researcher_goal=researcher_goal,
                        researcher_backstory=researcher_backstory,
                        writer_goal=writer_goal,
                        writer_backstory=writer_backstory,
                        editor_goal=editor_goal,
                        editor_backstory=editor_backstory,
                    )

                    results = task_description

                    # ----- Save for editing -----
                    st.session_state.generated_content = results
                    st.session_state.editable_text = results
                    detection_result = check_ai_content(results)
                    st.session_state.detection_result = detection_result
                    record_id = save_output_to_db(
                        topic,
                        researcher_goal, researcher_backstory,
                        writer_goal, writer_backstory,
                        editor_goal, editor_backstory,
                        results, json.dumps(detection_result)
                    )

                    # REDIRECT
                    st.success("✅ Generation complete! Scroll down to see the AI detection results.")

                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.warning("Please enter a topic first.")



    if row and row[9] is not None and row[9] != "":
        param = json.loads(row[9])
        data = param.get("data", {})
        input_text = data.get("input_text", "")
        st.session_state.editable_text = input_text
        display_highlighted_text(param)
    else:
        if st.session_state.detection_result:
            display_highlighted_text(st.session_state.detection_result)
    return
