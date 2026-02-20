import streamlit as st
import sqlite3
import os
import json
import time
from datetime import datetime
from dotenv import load_dotenv
from crewai import LLM, Agent, Task, Crew, Process
import markdown
from markdownify import markdownify as md
from bs4 import BeautifulSoup

from concurrent.futures import ThreadPoolExecutor
import zerogpt_api 
from concurrent.futures import ThreadPoolExecutor

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



def save_to_db(source_type, source_value, result_json):

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
    result = [item for arr in res for item in arr]

    if not result:
        result = [
            'sarcastic friend','nostalgic storyteller','curious teacher','chaotic thinker','casual confidant',
            'skeptical critic','optimistic mentor','grumpy old-timer','chatty neighbor','daydreamer'
        ]
    conn.close()
    return result



def get_all_personalities(user_id=None):
    """Retrieves all tones created by a specific user."""
    user = st.session_state.get("user_info")
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
    result = [item for arr in res for item in arr]
    if not result:
        result = [
            'sarcastic friend','nostalgic storyteller','curious teacher','chaotic thinker','casual confidant',
            'skeptical critic','optimistic mentor','grumpy old-timer','chatty neighbor','daydreamer'
        ]
    conn.close()
    return result


def go_to(page, **params):
    qs = st.query_params
    for k, v in params.items():
        qs[k] = v

    st.switch_page(page)

def set_st_session(ss_vars=None,piroty=None):
    if ss_vars is not None and piroty is None:
        st.session_state['page'] = ss_vars
    elif ss_vars is not None and piroty is not None:
        st.session_state['page'] = piroty



def get_content_by_user(user_id):
    """Retrieves all tones created by a specific user."""
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    # Join tones with users to get the username for display

    c.execute("""
        SELECT p.*
        FROM content_history p
        JOIN users u ON p.user_id = u.id
        WHERE p.user_id = ?
        ORDER BY p.created_at DESC
    """, (user_id,))
    posts = c.fetchall()
    conn.close()
    return  posts


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


def insert_custom_tone(user_id, name, details):
    conn = sqlite3.connect(DATABASE_FILE)
    conn.execute("INSERT INTO tones (user_id, name, details) VALUES (?, ?, ?)", (user_id, name, details))
    conn.commit()
    conn.close()

# Fetch All Records
def get_custom_tone(user_id=None):
    conn = sqlite3.connect(DATABASE_FILE)
    users = conn.execute("SELECT id, name, details, active FROM tones where user_id=?", (user_id,)).fetchall()
    conn.close()
    return users

# Update Record
def update_custom_tone(user_id, name, details):
    conn = sqlite3.connect(DATABASE_FILE)
    conn.execute("UPDATE tones SET name=?, details=? WHERE id=?", (name, details, user_id))
    conn.commit()
    conn.close()

# Toggle Active
def toggle_active_custom_tone(user_id, current_status):
    new_status = 0 if current_status == 1 else 1
    conn = sqlite3.connect(DATABASE_FILE)
    conn.execute("UPDATE tones SET active=? WHERE id=?", (new_status, user_id))
    conn.commit()
    conn.close()

# Delete Record
def delete_custom_tone(user_id):
    conn = sqlite3.connect(DATABASE_FILE)
    conn.execute("DELETE FROM tones WHERE id=?", (user_id,))
    conn.commit()
    conn.close()


def get_conn():
    return sqlite3.connect(DATABASE_FILE, check_same_thread=False)

def get_row_conn():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def unescape_text(text):
    return bytes(text, "utf-8").decode("unicode_escape")


def file_type_exist_check():
    conn = get_row_conn()
    c = conn.cursor()
    # Join tones with users to get the username for display

    c.execute("""
        SELECT slug
        FROM template_type 
        ORDER BY id DESC
    """)
    
    
    #st.json(posts)
    
    

    return [row[0] for row in c.fetchall()]


def json_to_html(data):
    if isinstance(data, dict):
        html = "<ul>"
        for key, value in data.items():
            html += f"<li><strong>{key}:</strong> {json_to_html(value)}</li>"
        html += "</ul>"
        return html

    elif isinstance(data, list):
        html = "<ul>"
        for item in data:
            html += f"<li>{json_to_html(item)}</li>"
        html += "</ul>"
        return html

    else:
        return str(data)

def run_humanizer(text, selected_tone):
    # Agent 1: The Stylist
    stylist = Agent(
        role='Linguistic Stylist',
        goal=f'Rewrite text to sound like a human in a {selected_tone} tone.',
        backstory="Expert editor who avoids AI clichés and varies sentence structure.",
        allow_delegation=False,
        verbose=True
    )

    # Agent 2: Quality Control
    qc = Agent(
        role='Integrity Specialist',
        goal='Ensure meaning remains 100% identical to the source.',
        backstory="A strict fact-checker who prevents the stylist from changing the message.",
        verbose=True
    )

    task = Task(
        description=f"Humanize this text: {text}. Ensure the tone is {selected_tone}. Do not change the core meaning.",
        expected_output="A polished, human-like version of the input text.",
        agent=stylist
    )

    crew = Crew(agents=[stylist, qc], tasks=[task], process=Process.sequential)
     
    crew_result = crew.kickoff()  
    humanized_text = crew_result.raw      
    return humanized_text
def humanizer_tone(idx=None):
    return st.selectbox("Select Tone", ["Professional", "Conversational", "Academic", "Storytelling"],key=f"tone_selector_{idx}")

def html_to_ai(html):
    if not html:
        return ""
    if not isinstance(html, str):
        html = str(html)

    soup = BeautifulSoup(html, 'html.parser')
    for noise in soup(['nav', 'footer', 'script', 'style']):
        noise.decompose()

    # Step 2: Convert the remaining "meat" to Markdown
    clean_markdown = md(str(soup), heading_style="ATX")

    return clean_markdown




def professional_humanizer_pipeline(original_text):
    llm = LLM(
        model="gpt-4o-mini",
        temperature=0.8
    )
    # 1️⃣ Humanizer Agent
    humanizer = Agent(
        role="Senior Human Content Rewriter",
        goal="Rewrite AI text to sound naturally human while preserving meaning.",
        backstory=(
            "You specialize in rewriting AI-generated content to sound "
            "natural, fluent, and professionally written by a human."
        ),
        llm=llm
    )

    # 2️⃣ Style Enhancer Agent
    stylist = Agent(
        role="Professional Editorial Stylist",
        goal="Improve flow, clarity, and sentence variation.",
        backstory=(
            "You refine content by improving rhythm, sentence structure "
            "diversity, and readability without changing meaning."
        ),
        llm=llm
    )

    # 3️⃣ AI Pattern Optimizer
    anti_ai = Agent(
        role="AI Detection Optimization Specialist",
        goal="Reduce AI-detection probability by eliminating robotic patterns.",
        backstory=(
            "You identify repetitive AI patterns and rewrite them to "
            "increase human unpredictability while preserving intent."
        ),
        llm=llm
    )

    # 4️⃣ Final Reviewer
    reviewer = Agent(
        role="Chief Editorial Reviewer",
        goal="Ensure meaning accuracy and high human authenticity.",
        backstory=(
            "You validate that the final content keeps the exact meaning, "
            "is coherent, and sounds 90%+ human."
        ),
        llm=llm
    )

    # TASKS

    task1 = Task(
        description=f"""
Rewrite the following content to sound naturally written by a human.
Preserve meaning exactly. Do not remove facts.

Content:
{original_text}
""",
        expected_output="Humanized content with preserved meaning.",
        agent=humanizer
    )

    task2 = Task(
        description="Improve sentence variety, flow, and readability without altering meaning.",
        agent=stylist,
        expected_output="Improved stylistic version of the humanized content.",
        context=[task1] 
    )

    task3 = Task(
        description="Reduce AI-detection patterns. Increase natural variation and subtle human nuance.",
        expected_output="Final polished human-like content.",
        agent=anti_ai,
        context=[task2] 
    )

    task4 = Task(
        description="Review final content. Ensure meaning is unchanged and human authenticity exceeds 90%. Output final polished version only.",
        expected_output="Final polished human-like content with preserved meaning.",
        agent=reviewer,
        context=[task3] 
    )

    crew = Crew(
        agents=[humanizer, stylist, anti_ai, reviewer],
        tasks=[task1, task2, task3, task4],
        process="sequential",
        verbose=False
    )

    result = crew.kickoff()

    return result.raw   
def ai_to_html(text):
    # Fix escaped newlines from DB
    text = text.replace("\\n", "\n")

    # Convert Markdown to HTML
    html = markdown.markdown(
        text,
        extensions=["extra", "sane_lists"]
    )

    return html





















def humanize_content(ai_content: str) -> str:
    """
    Main function to humanize AI-generated content using CrewAI
    
    Args:
        ai_content: The AI-generated content to humanize
        
    Returns:
        Humanized version of the content
    """
    llm = LLM(
        model="gpt-4o-mini",
        temperature=0.8
    )
    

    content_analyzer = Agent(
        role="Content Analyzer",
        goal="Analyze AI-generated content to identify robotic patterns, repetitive phrases, and unnatural language structures",
        backstory="""You are an expert in identifying AI-generated text patterns. 
        You can spot overly formal language, repetitive sentence structures, 
        lack of personality, and other telltale signs of machine-generated content.""",
        verbose=True,
        allow_delegation=False,
        llm=llm
    )

    # Agent 2: Human Writer
    human_writer = Agent(
        role="Human Writer",
        goal="Rewrite content to sound natural, conversational, and authentically human",
        backstory="""You are a skilled creative writer with years of experience 
        in crafting engaging, natural-sounding content. You understand tone, voice, 
        personality, and how real humans communicate. You add variety in sentence 
        structure, use contractions, include occasional imperfections, and write 
        with genuine emotion and personality.""",
        verbose=True,
        allow_delegation=False,
        llm=llm
    )

    # Agent 3: Style Enhancer
    style_enhancer = Agent(
        role="Style Enhancer",
        goal="Add personality, emotion, and human touches like anecdotes, humor, and relatable examples",
        backstory="""You specialize in making content more engaging and relatable. 
        You add storytelling elements, personal touches, conversational asides, 
        and authentic human elements that make readers connect with the content.""",
        verbose=True,
        allow_delegation=False,
        llm=llm
    )

    # Agent 4: Quality Checker
    quality_checker = Agent(
        role="Quality Checker",
        goal="Ensure the humanized content maintains accuracy while sounding completely natural",
        backstory="""You are a meticulous editor who ensures content sounds human 
        while preserving the original message and accuracy. You check for flow, 
        readability, and authenticity.""",
        verbose=True,
        allow_delegation=False,
        llm=llm
    )

    # Task 1: Analyze the content
    analyze_task = Task(
        description=f"""Analyze this AI-generated content and identify:
        1. Robotic or overly formal language patterns
        2. Repetitive sentence structures
        3. Lack of personality or emotion
        4. Unnatural transitions
        5. Areas that need human touches
        
        Content to analyze:
        {ai_content}
        
        Provide a detailed analysis with specific examples.""",
        agent=content_analyzer,
        expected_output="A detailed analysis report identifying AI patterns and areas for improvement"
    )
    
    # Task 2: Rewrite the content
    rewrite_task = Task(
        description=f"""Based on the analysis, rewrite this content to sound natural and human:
        
        Original content:
        {ai_content}
        
        Guidelines:
        - Use conversational tone
        - Vary sentence length and structure
        - Include contractions (I'm, you're, don't, etc.)
        - Add personality and voice
        - Make it flow naturally
        - Remove robotic patterns
        - Keep the core message intact""",
        agent=human_writer,
        expected_output="A naturally rewritten version of the content that sounds human",
        context=[analyze_task]
    )
    
    # Task 3: Enhance with human touches
    enhance_task = Task(
        description="""Enhance the rewritten content with human elements:
        - Add relatable examples or brief anecdotes where appropriate
        - Include conversational asides or thoughts
        - Add subtle humor or warmth where fitting
        - Use more vivid, natural language
        - Make it engaging and personable
        
        Don't overdo it - keep it authentic and natural.""",
        agent=style_enhancer,
        expected_output="Enhanced content with natural human touches and personality",
        context=[rewrite_task]
    )
    
    # Task 4: Final quality check
    quality_task = Task(
        description="""Review the humanized content and:
        1. Ensure it sounds completely natural and human
        2. Verify the original message is preserved
        3. Check for good flow and readability
        4. Make any final minor adjustments needed
        5. Provide the final polished version
        
        Output ONLY the final humanized content, no explanations.""",
        agent=quality_checker,
        expected_output="Final polished humanized content ready to use",
        context=[enhance_task]
    )
    
    # Create the crew
    crew = Crew(
        agents=[content_analyzer, human_writer, style_enhancer, quality_checker],
        tasks=[analyze_task, rewrite_task, enhance_task, quality_task],
        process=Process.sequential,
        verbose=True
    )
    
    # Execute the crew
    result = crew.kickoff()
    
    return result.raw


##########################################################################################
def humanize_once(text):
    llm = LLM(
        model="gpt-4o",
        temperature=1.1
    )
    agent = Agent(
        role="Human Content Editor",
        goal="Rewrite AI content naturally while preserving meaning.",
        backstory="Expert at humanizing AI-generated content.",
        llm=llm
    )

    task = Task(
        description=f"""
Rewrite this content to feel naturally written by a human expert.

IMPORTANT:
- Break predictable structure.
- Vary sentence length aggressively.
- Use a mix of short and long sentences.
- Avoid formulaic transitions like "Ultimately", "By clearly".
- Slightly relax overly formal tone while staying professional.
- Introduce natural pacing.
- Preserve exact meaning.
- Do NOT summarize.

Content:
{text}
""",
        expected_output="Humanized content.",
        agent=agent
    )

    crew = Crew(
        agents=[agent],
        tasks=[task],
        process="sequential",
        verbose=False
    )

    result = crew.kickoff()
    return result.raw

def run_parallel_humanizers(original_text, runs=5):

    with ThreadPoolExecutor(max_workers=runs) as executor:
        futures = [
            executor.submit(humanize_once, original_text)
            for _ in range(runs)
        ]

        results = [f.result() for f in futures]

    return results


def get_ai_score(text):
    response = zerogpt_api.check_ai_content(text)
    return response["data"]["fakePercentage"]

def parallel_adaptive_pipeline(original_text, threshold=20, max_attempts=3):

    history = []
    current_text = original_text
    best_text = original_text
    best_score = 100

    for attempt in range(max_attempts):

        print(f"\n--- Attempt {attempt+1} ---")

        # Run parallel humanizers
        variations = run_parallel_humanizers(current_text, runs=3)

        for text in variations:
            score = get_ai_score(text)

            history.append({
                "attempt": attempt + 1,
                "score": score
            })

            if score < best_score:
                best_score = score
                best_text = text

        print(f"Best score so far: {best_score}%")

        if best_score <= threshold:
            break

        current_text = best_text

    return best_text, best_score, history


