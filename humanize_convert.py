import streamlit as st
import sqlite3
import hashlib
import time
import pandas as pd
import json # Added for session persistence
import os
import common
import human_convert_pipeline
import zerogpt_api
import highlight_ai_segments
#import generatecontent

def list_gen_content():
    """Renders the Post creation and viewing page (NEW)."""
    user = st.session_state['user_info']
    user_id = user['id']
    username = user['username']

    #query_params = st.query_params
    #st.markdown(f"Mode: {query_params.get('mode')}")

    left, right = st.columns([8, 2])
    with left:
        st.title("✍️ My Generated Content List")
    #left.header(f"View Your Tones ({username})")  # optional text
    with right:
        if st.button("Generate Content", type="primary"):
            #common.navigate_to("gencontent")
            st.session_state['page'] = 'content'
            st.session_state['spage'] = 'gencontent'
            st.session_state.detection_result = ''
            st.session_state['content_id'] = ''
            st.rerun()
            #common.navigate_to("gencontent")


    st.markdown("---")

    # --- Post Viewing Section ---
    st.subheader("📝 Content List")

    user_content = common.get_content_by_user(user_id)
    #st.json(user_tones)

    # selected_tones = common.get_selected_tones_by_user(user_id)
    # st.json(selected_tones)
    #generated_json (7) created_at	is_active	user_id


    if user_content:
        for content_item in user_content:
            content_id = content_item[0]
            link_text = content_item[1]
            created_at = content_item[10]

            # Use st.columns to place the content title/link and the button side-by-side
            col_content, col_delete = st.columns([0.8, 0.2])

            with col_content:
                # Custom HTML/Markdown for the content card and edit link
                link_href = f"?id={content_id}&mode=edit&refresh=true"
                st.markdown(f"""
                    <div style="border: 1px solid #ffcc80; padding: 15px; margin-bottom: 15px; border-radius: 8px; background-color: #fff3e0;">
                        <h4 style="margin-top: 0; color: #e65100;">
                            <a href="/?refresh=true&page=content&id={content_id}&mode=edit" target="_self">{link_text}</a>
                        </h4>
                        <p style="font-size: 0.9em; color: #666; font-style: italic;">
                            Posted on {created_at}
                        </p>
                    </div>
                """, unsafe_allow_html=True)

            with col_delete:
                # Add the delete button with a unique key and the callback function
                # The button is placed slightly lower to align with the content card
                st.markdown("<div style='height: 25px;'></div>", unsafe_allow_html=True) # Spacer
                st.button(
                    "Delete 🗑️",
                    key=f"delete_btn_{content_id}",
                    on_click=handle_delete_content,
                    args=(content_id, user_id), # Pass content_id and user_id to the callback
                    type="secondary",
                    use_container_width=True
                )
    else:
        st.info("Content is not created yet!")


def generate_content_page():
    params = st.query_params
    mode = params.get("mode", None)
    user = st.session_state['user_info']
    user_id = user['id']
    record_id = params.get("id", None)
    row = [None] * 10  # Default empty row with 8 elements
    # if mode == "edit" and record_id:
    #     #st.markdown(record_id, unsafe_allow_html=True)
    #     row = load_record(record_id)
    # elif st.session_state.get('spage', '') == 'gencontent' and st.session_state.get('content_id', None):
    #     row = load_record(st.session_state.get('content_id'))

    st.title("✍️ Humanize Content")
    Tones = common.get_custom_tone(user_id)
    #st.json(Tones[:, 0])
    if Tones is not None and len(Tones) > 0:
        single_t = convert_to_single_line(Tones)
    else:
        single_t = None

    #st.json(single_t)
    #st.json(common.get_all_personalities())


    st.dataframe({'Tones':common.get_all_personalities()})
    #topic = st.text_input("Enter your topic:", value=(row and row[1] if row and row[1] is not None else ""), placeholder="e.g. AI tools for marketing")
    topic = st.text_area("Content", value="", placeholder="")
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
                    res, task_description = human_convert_pipeline.run_pipeline(
                        topic=topic,
                        researcher_goal=researcher_goal,
                        researcher_backstory=researcher_backstory,
                        writer_goal=writer_goal,
                        writer_backstory=writer_backstory,
                        editor_goal=editor_goal,
                        editor_backstory=editor_backstory,
                    )
                    #st.json(res)
                    #results = res['result']
                    results = task_description
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
                    #st.markdown("### 🧩 {results}".format(results="AI Detection Results")   )
                    detection_result = zerogpt_api.check_ai_content(results)

                    #st.json(detection_result)
                    #st.markdown("### 🧩 {detection_result}".format(detection_result="AI Detection Results"))
                    st.session_state.detection_result = detection_result
                    # record_id = save_output_to_db(
                    #     topic,
                    #     researcher_goal, researcher_backstory,
                    #     writer_goal, writer_backstory,
                    #     editor_goal, editor_backstory,
                    #     results, json.dumps(detection_result)
                    # )

                    # REDIRECT
                    #redirect_to_edit(record_id)
                    # if "error" in detection_result:
                    #     st.error(detection_result["error"])
                    # else:
                    #     display_highlighted_text(detection_result)
                    st.success("✅ Generation complete! Scroll down to see the AI detection results.")

                except Exception as e:
                    st.error(f"Error: {e}")

        else:
            st.warning("Please enter a topic first.")




    if row and row[9] is not None and row[9] != "":
        #st.session_state.generated_content = results
        param = json.loads(row[9])
        data = param.get("data", {})
        input_text = data.get("input_text", "")
        st.session_state.editable_text = input_text
        highlight_ai_segments.display_highlighted_text(param)
    else:
        # st.session_state.get("detection_result")
        #st.markdown("---")
        #st.subheader("🧩 AI Detection Results")
        if st.session_state.detection_result:
            highlight_ai_segments.display_highlighted_text(st.session_state.detection_result)
    return


def show_post_content():
    """Renders the Post creation and viewing page (NEW)."""
    user = st.session_state['user_info']
    user_id = user['id']
    username = user['username']


    #st.header(f"Create and View Your Content ({username})", divider='orange')
    left, right = st.columns([8, 2])
    with left:
        st.title("✍️ Humanize Content with Tones")
    #left.header(f"View Your Tones ({username})")  # optional text
    # with right:
    #     if st.button("List", type="primary"):
    #         st.session_state['spage'] = ''
    #         st.session_state['page'] = 'content'
    #         st.rerun()
            #common.navigate_to("content")

    if "detection_result" not in st.session_state:
        st.session_state.detection_result = None

    if "last_edit_time" not in st.session_state:
        st.session_state.last_edit_time = {}

    if "edit_cache" not in st.session_state:
        st.session_state.edit_cache = {}


    #st.title("🧠 AI Content Agent v1.0.4")

    st.markdown(f"""
    <b>Enter your topic, then define each agent's role and backstory to get targeted, comprehensive output. The more specific you are, the better your content in terms of depth, angle, and completeness.</b>\n"""
    """
    This multi-agent system can be used anywhere content needs to be created, refined, and published regularly. Some examples include: SEO-friendly blogs and articles, generating social media posts, newsletters, campaign content , product descriptions, guides, promotional blogs, newsletters, announcements, reports.
    """, unsafe_allow_html=True)
    st.markdown("---")
    #st.markdown(generatecontent.__file__)
    # --- GENERATE BUTTON ---
    generate_content_page()
    # --- Post Creation Form ---

    st.markdown("---")
