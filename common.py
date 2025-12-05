import streamlit as st
import sqlite3
import os
import json
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DATABASE_FILE = os.getenv("DATABASE_FILE")


def update_output_to_db(user_id, **fields):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    set_clause = ", ".join(f"{key} = ?" for key in fields.keys())
    values = list(fields.values())

    query = f"UPDATE content_history SET {set_clause} WHERE id = ?"
    cursor.execute(query, values + [user_id])

    conn.commit()
    conn.close()

# def update_output_to_db(id, topic, researcher_goal, researcher_backstory,
#                       writer_goal, writer_backstory,
#                       editor_goal, editor_backstory,
#                       final_output, detection_result):

#     conn = sqlite3.connect(DATABASE_FILE)
#     c = conn.cursor()

#     c.execute("""
#         UPDATE content_history SET
#             topic = ?, researcher_goal = ?, researcher_backstory = ?,
#             writer_goal = ?, writer_backstory = ?,
#             editor_goal = ?, editor_backstory = ?,
#             final_output = ?, detection_result = ?
#         WHERE id = ?
#     """, (
#         topic,
#         researcher_goal, researcher_backstory,
#         writer_goal, writer_backstory,
#         editor_goal, editor_backstory,
#         final_output, detection_result,
#         id
#     ))
#     conn.commit()
#     conn.close()

def save_to_db(source_type, source_value, result_json):
    # data = json.loads(result_json)

    # conn = sqlite3.connect(DATABASE_FILE)
    # cursor = conn.cursor()

    # cursor.execute("""
    #     INSERT INTO micro_roles
    #     (source_type, source_value, role, tone, style, patterns, generated_json, created_at)
    #     VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    # """, (
    #     source_type,
    #     source_value,
    #     json.dumps(data.get("roles")),
    #     data.get("tone"),
    #     data.get("style"),
    #     json.dumps(data.get("patterns")),
    #     result_json,
    #     datetime.now().isoformat()
    # ))
    user = st.session_state['user_info']
    user_id = user['id']

    role_json = json.dumps(result_json.get("roles"))
    patterns_json = json.dumps(result_json.get("patterns"))
    generated_json = json.dumps(result_json)  # Save full JSON as string

    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO micro_roles
        (source_type, source_value, role, tone, style, patterns, generated_json, created_at, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        source_type,
        source_value,
        role_json,
        result_json.get("tone"),
        result_json.get("style"),
        patterns_json,
        generated_json,
        datetime.now().isoformat(),
        user_id
    ))
    conn.commit()
    conn.close()


def navigate_to(page_name: str):
    st.query_params.clear()
    if page_name == "clear":
        st.rerun()
        return
    st.query_params.update({"page": page_name})
    st.rerun()



def get_selected_tones_by_user(user_id):
    """Retrieves all tones created by a specific user."""
    # user = st.session_state['user_info']
    # user_id = user['id']

    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    # Join tones with users to get the username for display

    c.execute("""
        SELECT p.generated_json
        FROM micro_roles p
        JOIN users u ON p.user_id = u.id
        WHERE p.user_id = ? and p.is_active = 1
        ORDER BY p.created_at DESC
    """, (user_id,))
    posts = c.fetchall()
    res = []
    for post in posts:
        role_json = json.loads(post[0])
        sposts = role_json.get("micro_agent_list") if isinstance(role_json, dict) else None
        res.append(sposts if sposts else None)
    #posts = [json.loads(row[0]) for row in posts]  # Parse JSON strings into Python objects
    #suggested_agents = role_json.get("micro_agent_list") if isinstance(role_json, dict) else None
    result = [item for arr in res for item in arr]
    #result = res.flat()
    conn.close()
    return result



def get_all_personalities(user_id=None):
    """Retrieves all tones created by a specific user."""
    # user = st.session_state['user_info']
    # user_id = user['id']
    user = st.session_state.get("user_info")
    #user = st.session_state['user_info']
    try:
        user_id = user['id']
    except TypeError:
        # This catches the 'NoneType' object is not subscriptable error
        print("Error: Failed to retrieve user data (variable 'user' is None).")
        user_id = None

    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    # Join tones with users to get the username for display

    c.execute("""
        SELECT p.generated_json
        FROM micro_roles p
        JOIN users u ON p.user_id = u.id
        WHERE p.user_id = ? and p.is_active = 1
        ORDER BY p.created_at DESC
    """, (user_id,))
    posts = c.fetchall()
    res = []
    for post in posts:
        role_json = json.loads(post[0])
        sposts = role_json.get("micro_agent_list") if isinstance(role_json, dict) else None
        res.append(sposts if sposts else None)
    #posts = [json.loads(row[0]) for row in posts]  # Parse JSON strings into Python objects
    #suggested_agents = role_json.get("micro_agent_list") if isinstance(role_json, dict) else None
    result = [item for arr in res for item in arr]
    #result = res.flat()
    conn.close()
    return result


def set_st_session(ss_vars=None,piroty=None):
    if ss_vars is not None and piroty is None:
        st.session_state['page'] = ss_vars
    elif ss_vars is not None and piroty is not None:
        st.session_state['page'] = piroty
