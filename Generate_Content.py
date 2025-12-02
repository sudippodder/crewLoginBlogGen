import streamlit as st
#from crew_pipeline import run_pipeline
from crew_pipeline_human import run_pipeline
from zerogpt_api import check_ai_content
import sqlite3
import os
from paragraph_editor import display_paragraphs_with_detection
from highlight_ai_segments import display_highlighted_text
import json
from dotenv import load_dotenv
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
    st.query_params.update({"id": record_id, "mode": "edit"})
    st.rerun()

def save_output_to_db(topic, researcher_goal, researcher_backstory,
                      writer_goal, writer_backstory,
                      editor_goal, editor_backstory,
                      final_output, detection_result):

    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()

    c.execute("""
        INSERT INTO content_history (
            topic, researcher_goal, researcher_backstory,
            writer_goal, writer_backstory,
            editor_goal, editor_backstory,
            final_output, detection_result
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        topic,
        researcher_goal, researcher_backstory,
        writer_goal, writer_backstory,
        editor_goal, editor_backstory,
        final_output, detection_result
    ))

    conn.commit()

    new_id = c.lastrowid
    conn.close()
    return new_id

def generate_content_page():
    params = st.query_params
    mode = params.get("mode", None)
    record_id = params.get("id", None)
    row = [None] * 10  # Default empty row with 8 elements
    if mode == "edit" and record_id:
        #st.markdown(record_id, unsafe_allow_html=True)
        row = load_record(record_id)
        #st.json(row)

    st.title("✍️ Generate AI Blog Content")

    topic = st.text_input("Enter your topic:", value=(row[1] != None and row[1] or ""), placeholder="e.g. AI tools for marketing")

    with st.expander("Researcher Settings", expanded=True):
        researcher_goal = st.text_area("Goal", value=(row[2] != None and row[2] or "Find and summarize useful content for the given topic."), placeholder="Find and summarize useful content for the given topic.")
        researcher_backstory = st.text_area("Backstory", value=(row[3] != None and row[3] or "You're great at finding relevant sources."), placeholder="You're great at finding relevant sources.")

    with st.expander("Writer Settings", expanded=True):
        writer_goal = st.text_area("Goal", value=(row[4] != None and row[4] or "Write a detailed, SEO-friendly blog post using the research."), placeholder="Write a detailed, SEO-friendly blog post using the research.")
        writer_backstory = st.text_area("Backstory", value=(row[5] != None and row[5] or "You're skilled at clarity and engagement."), placeholder="You're skilled at clarity and engagement.")

    with st.expander("Editor Settings", expanded=True):
        editor_goal = st.text_area("Goal", value=(row[6] != None and row[6] or "Polish and refine the blog content for tone, clarity, and grammar."), placeholder="Polish and refine the blog content for tone, clarity, and grammar.")
        editor_backstory = st.text_area("Backstory", value=(row[7] != None and row[7] or "You ensure it reads naturally and maintains tone."), placeholder="You ensure it reads naturally and maintains tone.")

    if "generated_content" not in st.session_state:
        st.session_state.generated_content = None
    if "detection_result" not in st.session_state:
        st.session_state.detection_result = None

      # --- Initialize session state ---
    # st.session_state.setdefault("generated_content", None)
    # st.session_state.setdefault("detection_result", None)
    st.session_state.setdefault("show_editor", False)
    st.session_state.setdefault("editable_text", "")
    # st.markdown(record_id, unsafe_allow_html=True)

    #st.markdown(f"{record_id} >> {mode}", unsafe_allow_html=True)



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
                    res = run_pipeline(
                        topic=topic,
                        researcher_goal=researcher_goal,
                        researcher_backstory=researcher_backstory,
                        writer_goal=writer_goal,
                        writer_backstory=writer_backstory,
                        editor_goal=editor_goal,
                        editor_backstory=editor_backstory,
                    )
                    #st.json(res)
                    results = res['result']

                    #st.markdown(results, unsafe_allow_html=True)
                    #json_res = json.loads(res)

                    #st.json(json_res)


                    #st.markdown(json_res['result'], unsafe_allow_html=True)
                    #st.json(json_res['result'])
                    # st.markdown(results, unsafe_allow_html=True)
                    # st.subheader("Metadata")
                    #st.json(out_map)



                    # ----- Save for editing -----
                    st.session_state.generated_content = results
                    st.session_state.editable_text = results
                    #st.json(results)
                    # ----- AI Detection (Send final text ONLY) -----
                    detection_result = check_ai_content(results)

                        #st.json(detection_result)

                    st.session_state.detection_result = detection_result
                    record_id = save_output_to_db(
                        topic,
                        researcher_goal, researcher_backstory,
                        writer_goal, writer_backstory,
                        editor_goal, editor_backstory,
                        results, json.dumps(detection_result)
                    )

                    # REDIRECT
                    #redirect_to_edit(record_id)
                    # if "error" in detection_result:
                    #     st.error(detection_result["error"])
                    # else:
                    #     display_highlighted_text(detection_result)
                    st.success("✅ Generation complete! Scroll down to see the AI detection results.")

                except Exception as e:
                    st.error(f"Error: {e}")
                # try:
                #     final, result = run_pipeline(
                #         topic=topic,
                #         researcher_goal=researcher_goal,
                #         researcher_backstory=researcher_backstory,
                #         writer_goal=writer_goal,
                #         writer_backstory=writer_backstory,
                #         editor_goal=editor_goal,
                #         editor_backstory=editor_backstory,
                #         tone="casual",
                #         creativity=0.95,
                #         humanizer_passes=10,
                #         entropy_strength=1.3,
                #         seo_keywords=["coffee", "caffeine", "sleep"],
                #         micro_intro=None,
                #         micro_body=None,
                #         micro_conclusion=None,
                #         ui=True,
                #     )
                #     st.subheader("Final Output")
                #     st.markdown(final, unsafe_allow_html=True)

                #     st.json(result)
                #     # file_path = "outputs/For_Audience_Engagement.txt"  # Replace with your file name or full path
                #     # # Open the file in read mode ('r')
                #     # with open(file_path, "r", encoding="utf-8") as file:
                #     #     content = file.read()

                #     # result = content

                #     #st.json(serper_tool)
                #     #return serper_tool

                #     #result = "Sample generated content based on the topic."
                #     st.session_state.generated_content = result
                #     st.session_state.editable_text = result
                #     #st.session_state.detection_result = check_ai_content(result)
                #     #display_paragraphs_with_detection(result)
                #     detection_result = check_ai_content(result)
                #     st.session_state.detection_result = detection_result

                #     # if "error" in detection_result:
                #     #     st.error(detection_result["error"])
                #     # else:
                #     #     display_highlighted_text(detection_result)

                #     st.success("✅ Generation complete! See below for AI detection results.")
                # except Exception as e:
                #     st.error(f"Error: {e}")
        else:
            st.warning("Please enter a topic first.")

    # if st.session_state.generated_content:
    #     st.subheader("📝 Generated Content")
    #     st.markdown(st.session_state.generated_content)
    #st.json(row[9])
    # if row[9] != None and row[9] != "":
    #     detection_result = json.loads(row[9])
    if row[9] != None and row[9] != "":
        #st.session_state.generated_content = results
        param = json.loads(row[9])
        data = param.get("data", {})
        input_text = data.get("input_text", "")
        st.session_state.editable_text = input_text
        display_highlighted_text(param)
    else:
        # st.session_state.get("detection_result")
        #st.markdown("---")
        #st.subheader("🧩 AI Detection Results")
        if st.session_state.detection_result:
            display_highlighted_text(st.session_state.detection_result)
