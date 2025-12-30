from urllib import response
import streamlit as st
import sqlite3
import os
from datetime import datetime
import json
import threading
#import openai  # or your preferred LLM
from openai import OpenAI
from dotenv import load_dotenv
from crewai import Agent , Task , Crew , Process
import common
import time
import crew_casestudy
from bs4 import BeautifulSoup
load_dotenv()
# ----------------------------
# DATABASE INITIALIZATION
# ----------------------------
openai_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY")
#conn = sqlite3.connect("app.db", check_same_thread=False)
# DATABASE_FILE = os.getenv("DATABASE_FILE")
# conn = sqlite3.connect(DATABASE_FIL, check_same_thread=False)
# cursor = conn.cursor()

# cursor.execute("""
# CREATE TABLE IF NOT EXISTS users (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     username TEXT UNIQUE,
#     password TEXT
# );
# """)

# cursor.execute("""
# CREATE TABLE IF NOT EXISTS templates (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     user_id INTEGER,
#     template_title TEXT,
#     audience TEXT,
#     tone_style TEXT,
#     content_structure TEXT,
#     notes_for_editors TEXT,
#     expected_length TEXT,
#     created_at DATETIME DEFAULT CURRENT_TIMESTAMP
# );
# """)

# cursor.execute("""
# CREATE TABLE IF NOT EXISTS contents (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,
#     user_id INTEGER,
#     topic TEXT,
#     template_id INTEGER,
#     generated_content TEXT,
#     created_at DATETIME DEFAULT CURRENT_TIMESTAMP
# );
# """)

#conn.commit()

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


# def blog_json_to_html(data):
#     import json

#     # 🔒 SAFETY: Convert string → dict
#     if isinstance(data, str):
#         data = json.loads(data)

#     article = data.get("article", {})

#     html = ["<article>"]

#     # Header
#     header = article.get("header", {})
#     if header:
#         html.append("<header>")
#         if "h1" in header:
#             html.append(f"<h1>{header['h1']}</h1>")
#         if "p" in header:
#             html.append(f"<p>{header['p']}</p>")
#         html.append("</header>")

#     # Sections
#     for section in article.get("sections", []):
#         section_id = section.get("id", "section")
#         html.append(f"<section id='{section_id}'>")

#         if "h2" in section:
#             html.append(f"<h2>{section['h2']}</h2>")
#         if "p" in section:
#             html.append(f"<p>{section['p']}</p>")

#         if "ul" in section:
#             html.append("<ul>")
#             for item in section["ul"]:
#                 html.append(f"<li>{item.get('li','')}</li>")
#             html.append("</ul>")

#         html.append("</section>")

#     # Footer
#     footer = article.get("footer", {})
#     if footer:
#         html.append("<footer>")
#         if "p" in footer:
#             html.append(f"<p>{footer['p']}</p>")
#         html.append("</footer>")

#     html.append("</article>")
#     return "\n".join(html)

def blog_json_to_html(data):
    import json

    # Safety: JSON string → dict
    if isinstance(data, str):
        data = json.loads(data)

    article = data.get("article", {})
    html = ["<article>"]

    # -------------------------
    # Header
    # -------------------------
    header = article.get("header", {})
    if header:
        html.append("<header>")
        if "h1" in header:
            html.append(f"<h1>{header['h1']}</h1>")
        if "p" in header:
            html.append(f"<p>{header['p']}</p>")
        html.append("</header>")

    # -------------------------
    # Sections
    # -------------------------
    for section in article.get("sections", []):
        sec_id = section.get("id", "section")
        html.append(f"<section id='{sec_id}'>")

        # Case 1: content is plain text (intro, conclusion)
        if isinstance(section.get("content"), str):
            html.append(f"<p>{section['content']}</p>")

        # Case 2: subsections exist (main content)
        if isinstance(section.get("subsections"), list):
            for block in section["subsections"]:

                if "h2" in block:
                    html.append(f"<h2>{block['h2']}</h2>")

                if "p" in block:
                    html.append(f"<p>{block['p']}</p>")

                if "ul" in block:
                    html.append("<ul>")
                    for li in block["ul"]:
                        # li already contains <strong> HTML
                        html.append(f"<li>{li}</li>")
                    html.append("</ul>")

        html.append("</section>")

    # -------------------------
    # Footer
    # -------------------------
    footer = article.get("footer", {})
    if footer:
        html.append("<footer>")
        if "p" in footer:
            html.append(f"<p>{footer['p']}</p>")
        html.append("</footer>")

    html.append("</article>")
    return "\n".join(html)

def safe_output_to_json(result):
    try:
        if hasattr(result, 'raw'):
            return {'result': result.raw}
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        return {'result': str(result)}
    except Exception as e:
        return {'error': str(e)}

def run_safe_pipeline_with_progress(crew, tasks, topic: str):
    """
    FIXED: Runs the CrewAI pipeline with task-by-task progress, ensuring the output
    of the previous task is fed as input to the next one to maintain the draft continuity.
    """

    global PROGRESS_LOG
    PROGRESS_LOG = [] # Reset the log for a new run
    total = len(tasks)

    result_container = {'result': None}
    # 🌟 FIX 1: Variable to hold the intermediate result (the evolving article draft)
    intermediate_draft = ""

    # 1. DEFINE PERMANENT UI ELEMENTS
    st.markdown("## 📋 Pipeline Execution Log")
    detailed_log_container = st.container()

    with detailed_log_container:
        st.markdown("### Task Details")
        task_list_placeholder = st.empty()

    def run_crew_sequential():
        nonlocal result_container
        # 🌟 FIX 2: Allow modification of the draft variable
        nonlocal intermediate_draft

        for i, task in enumerate(tasks):
            agent_name = task.agent.role
            task_desc = task.description

            PROGRESS_LOG.append({'status': 'STARTING', 'index': i, 'agent': agent_name, 'desc': task_desc})

            # NOTE: Create a minimal crew to run only this single task (required for logging between tasks)
            single_task_crew = Crew(agents=[task.agent], tasks=[task], verbose=True, process="sequential",tracing=True )

            # 🌟 FIX 3: Prepare inputs dynamically based on task index
            if i == 0:
                # Task 0 (Researcher): Needs only the original topic
                task_inputs = {'topic': topic}
            elif i == 1:
                # Task 1 (Writer): Needs the topic and the research notes (intermediate_draft)
                task_inputs = {'topic': topic, 'draft_content': intermediate_draft}
            else:
                # All subsequent tasks operate on the modified article/draft.
                task_inputs = {'draft_content': intermediate_draft}

            try:
                # 🌟 FIX 4: Pass the prepared inputs to the isolated task kickoff
                task_result = single_task_crew.kickoff(inputs=task_inputs)

                PROGRESS_LOG.append({'status': 'FINISHED', 'index': i, 'agent': agent_name, 'result': task_result})

                # 🌟 FIX 5: Update the intermediate draft for the next agent
                intermediate_draft = str(task_result)

                if i == total - 1:
                    result_container['result'] = task_result

            except Exception as e:
                PROGRESS_LOG.append({'status': 'FAILED', 'index': i, 'agent': agent_name, 'error': str(e)})
                result_container['result'] = f"⚠ Pipeline failed at {agent_name}: {e}"
                return

        PROGRESS_LOG.append({'status': 'COMPLETE'})


    thread = threading.Thread(target=run_crew_sequential)

    # 2. Block the UI with st.spinner
    with st.spinner("Initializing Crew and Agents..."):

        # Placeholders for Visualization (defined *inside* spinner for easy clearing)
        progress_bar = st.progress(0)
        status_text = st.empty()

        thread.start()

        # --- Progress Monitoring Loop (Reads the PROGRESS_LOG) ---

        while thread.is_alive() or len([log for log in PROGRESS_LOG if log.get('status') == 'FINISHED']) < total:

            current_finished_count = len([log for log in PROGRESS_LOG if log.get('status') == 'FINISHED'])
            current_task_index = current_finished_count

            start_log = next((log for log in PROGRESS_LOG if log.get('status') == 'STARTING' and log.get('index') == current_task_index), None)

            percent = (current_finished_count / total) * 100

            progress_bar.progress(percent / 100)

            # Update the status text
            if start_log:
                status_text.markdown(f"""
                    ### 🛠️ Executing Task {current_task_index + 1}/{total}
                    **Agent:** **{start_log['agent']}**
                    **Task:** *{start_log['desc']}*
                """)
            elif percent >= 100:
                status_text.success("✅ Pipeline Complete: Compiling Final Result.")
            else:
                 status_text.info(f"Preparing to start Task 1...")

            # 3. Update the detailed task list using the placeholder

            markdown_list = ""
            for i, task in enumerate(tasks):
                log_status = next((log['status'] for log in PROGRESS_LOG if log.get('index') == i), 'PENDING')

                if log_status == 'FINISHED':
                    markdown_list += f"* **✅ Done:** ~~{task.agent.role}: {task.description}~~\n"
                elif log_status == 'STARTING':
                    markdown_list += f"* **▶️ Executed:** **{task.agent.role}: {task.description}**\n"
                elif log_status == 'FAILED':
                    markdown_list += f"* **❌ Failed:** {task.agent.role}: {task.description}\n"
                else:
                    markdown_list += f"* **⚪ Pending:** {task.agent.role}: {task.description}\n"

            # Use the placeholder's markdown method to replace its contents
            task_list_placeholder.markdown(markdown_list)

            time.sleep(0.5)

        thread.join()

    # --- Finalization ---
    st.balloons()
    progress_bar.progress(1.0)
    status_text.success("🎉 **Pipeline Complete:** The final humanized article is ready.")

    final_result = safe_output_to_json(result_container['result'])
    return final_result, task.description

def blog_html_to_json(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    article = soup.find("article")

    result = {"article": {"header": {}, "sections": [], "footer": {}}}

    # Header
    header = article.find("header")
    if header:
        h1 = header.find("h1")
        p = header.find("p")
        if h1:
            result["article"]["header"]["h1"] = h1.get_text(strip=True)
        if p:
            result["article"]["header"]["p"] = p.get_text(strip=True)

    # Sections
    for sec in article.find_all("section"):
        section = {"id": sec.get("id", "section")}

        h2 = sec.find("h2")
        p = sec.find("p")
        ul = sec.find("ul")

        if h2:
            section["h2"] = h2.get_text(strip=True)
        if p:
            section["p"] = p.get_text(strip=True)
        if ul:
            section["ul"] = [{"li": li.get_text(strip=True)} for li in ul.find_all("li")]

        result["article"]["sections"].append(section)

    # Footer
    footer = article.find("footer")
    if footer:
        p = footer.find("p")
        if p:
            result["article"]["footer"]["p"] = p.get_text(strip=True)

    return result
# ----------------------------
# LLM GENERATION
# ----------------------------
def generate_content(topic, template_json):
    conn = common.get_conn()
    #openai.api_key = openai_key
    client = OpenAI()
    BLOG_TEMPLATE = template_json


    ##----------------------Agent Setup----------------------##
    seo_researcher = Agent(
        role="SEO Research Analyst",
        goal="Identify keywords, search intent, and key insights for the topic",
        backstory=(
            "You are an expert SEO analyst specializing in B2B and educational content. "
            "You understand search intent, keyword clustering, and ranking factors."
        ),
        llm_config={"model": "gpt-4o-mini"},
        verbose=True
    )
    content_writer = Agent(
        role="Senior SEO Content Writer",
        goal="Write long-form blog content strictly following the provided template",
        backstory=(
            "You are a senior content writer who produces SEO-optimized, "
            "reader-focused blog articles with strong structure and clarity."
        ),
        llm_config={"model": "gpt-4o-mini"},
        verbose=True
    )
    seo_editor = Agent(
        role="SEO Content Editor",
        goal="Optimize content for SEO, clarity, and readability without changing meaning",
        backstory=(
            "You are a professional editor ensuring content meets SEO and "
            "editorial standards while remaining engaging."
        ),
        llm_config={"model": "gpt-4o-mini"},
        verbose=True
    )
    html_editor = Agent(
        role="HTML Validator",
        goal="Ensure output is valid, clean HTML",
        backstory="Expert frontend engineer specializing in semantic HTML.",
        llm_config={"model": "gpt-4o-mini"},
        verbose=True
    )

    ##----------------------Agent Setup----------------------##
    ##----------------------Task Setup----------------------##

    research_task = Task(
        description=f"""
    Research the topic and prepare SEO inputs.

    Topic:
    {{topic}}

    Audience:
    {BLOG_TEMPLATE['audience']}

    Provide:
    - Primary & secondary keywords
    - Search intent
    - Key insights
    - Examples or data points
    """,
        expected_output="Structured SEO research notes",
        agent=seo_researcher
    )
    HTML_RULES = """
OUTPUT FORMAT RULES (STRICT):
- Output ONLY valid HTML
- NO Markdown
- NO explanations
- NO comments
- NO triple backticks
- Root container MUST be <article>

ALLOWED TAGS ONLY:
<article>, <section>, <header>, <footer>,
<h1>, <h2>, <h3>,
<p>, <ul>, <ol>, <li>,
<strong>, <em>, <a>, <img>, <meta>

RULES:
- All tags must be properly closed
- Use <section> for each major block
- Use <h2> for main sections
- Bullet points must use <ul><li>
- SEO meta must use <meta> tags
"""
    HTML_SKELETON = """
<article>

<header>
  <h1><<MAIN_HEADLINE>></h1>
  <p><<SUB_HEADLINE>></p>
</header>

<section id="intro">
  <p><<INTRO_PARAGRAPH>></p>
</section>

<section id="content">
  <h2><<SECTION_TITLE>></h2>
  <p><<SECTION_TEXT>></p>
  <ul>
    <li><<POINT_1>></li>
    <li><<POINT_2>></li>
  </ul>
</section>

<section id="conclusion">
  <p><<SUMMARY>></p>
</section>

<footer>
  <p><<CTA>></p>
</footer>

</article>
"""


    # writing_task = Task(
    #     description=f"""
    # Using the research provided, write a full blog article
    # STRICTLY following this template:

    # Template Structure:
    # {BLOG_TEMPLATE['content_structure']}

    # Tone & Style Rules:
    # {BLOG_TEMPLATE['tone_style']}

    # IMPORTANT:
    # - Fill EVERY field
    # - Output must be VALID JSON
    # - Keys must match section/field names
    # - Do NOT mention AI
    # """,
    #     expected_output="Template-compliant blog JSON",
    #     agent=content_writer,
    #     context=[research_task]
    # )
    writing_task = Task(
    description=f"""
    Generate a complete blog article using ONLY valid HTML.

    Topic:
    {{topic}}

    STRICTLY follow this HTML skeleton:
    {HTML_SKELETON}

    {HTML_RULES}

    CONTENT RULES:
    - Audience: {BLOG_TEMPLATE['audience']}
    - Tone: {BLOG_TEMPLATE['tone_style']['voice']}
    - Avoid: {BLOG_TEMPLATE['tone_style']['avoid']}
    """,
        expected_output="Valid HTML article",
        agent=content_writer,
        context=[research_task]
    )

    editing_task = Task(
        description=f"""
    Edit the blog content for:
    - SEO optimization
    - Clarity & scannability
    - Tone consistency

    Rules:
    - Preserve JSON structure
    - Do not remove fields
    - Improve wording where needed
    """,
        expected_output="Final SEO-optimized blog JSON",
        agent=seo_editor,
        context=[writing_task]
    )
    html_fix_task = Task(
        description="""
    Validate and repair the HTML:
    - Fix broken tags
    - Remove invalid elements
    - Ensure semantic correctness
    - Output ONLY clean HTML
    """,
        expected_output="Valid semantic HTML",
        agent=html_editor,
        context=[writing_task]
    )

    ##----------------------Task Setup----------------------##
    agents=[seo_researcher, content_writer, html_editor, seo_editor]
    tasks=[research_task, writing_task, html_fix_task, editing_task]
    # crew = Crew(
    #     agents=[seo_researcher, content_writer, html_editor, seo_editor],
    #     tasks=[research_task, writing_task, html_fix_task, editing_task],
    #     process=Process.sequential
    # )
    crew = Crew(agents=agents, tasks=tasks, verbose=True, process="sequential", tracing=True)
    result, task_description = run_safe_pipeline_with_progress(crew, tasks, topic=topic)
    result = crew.kickoff(inputs={"topic": topic})
    #st.json(result.to_dict())
    return result.raw


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

def as_dict(value):
    return value if isinstance(value, dict) else {}

def as_list(value):
    return value if isinstance(value, list) else []

def as_str(value):
    return value if isinstance(value, str) else ""

# def blog_json_to_html(blog_json: dict) -> str:
#     html = []

#     # --- SEO Meta (commented for CMS use) ---
#     meta = as_dict(blog_json.get("Meta Information", {}))
#     html.append(f"<!-- SEO Title: {meta.get('SEO Title','')} -->")
#     html.append(f"<!-- SEO Description: {meta.get('SEO Description','')} -->")
#     html.append(f"<!-- Primary Keywords: {', '.join(meta.get('Primary Keywords', []))} -->")

#     # --- Header ---
#     header = as_dict(blog_json.get("Header", {}))
#     html.append(f"<h1>{header.get('Main Headline','')}</h1>")
#     if header.get("Subheadline"):
#         html.append(f"<h2>{header.get('Subheadline')}</h2>")
#     if header.get("Hero Image URL"):
#         html.append(f"<img src='{header['Hero Image URL']}' alt='{header.get('Main Headline','')}' />")

#     # --- Introduction ---
#     intro = as_dict(blog_json.get("Introduction", {}))
#     for key in ["Hook sentence", "Context", "Why this topic matters", "Learning outcome"]:
#         if intro.get(key):
#             html.append(f"<p>{intro[key]}</p>")

#     # --- Main Sections ---
#     sections = as_list(blog_json.get("Main Sections"))
#     for section in sections:
#         section = as_dict(section)
#         html.append(f"<h2>{as_str(section.get('H2: Key Insight',''))}</h2>")
#         html.append(f"<p>{as_str(section.get('Explanation paragraph',''))}</p>")

#         bullets = as_list(section.get("Bullets"))
#         if bullets:
#             html.append("<ul>")
#             for bullet in bullets:
#                 html.append(f"<li>{as_str(bullet)}</li>")
#             html.append("</ul>")

#         if section.get("Example"):
#             html.append(f"<blockquote>{section['Example']}</blockquote>")

#     # --- Conclusion ---
#     conclusion = as_dict(blog_json.get("Conclusion", {}))
#     html.append("<h2>Conclusion</h2>")
#     for key in ["Summary", "Action steps", "Final takeaway"]:
#         if conclusion.get(key):
#             html.append(f"<p>{conclusion[key]}</p>")

#     # --- CTA ---
#     cta = blog_json.get("CTA", {})
#     html.append("<div class='cta'>")
#     if cta.get("Primary CTA"):
#         html.append(f"<p><strong>{cta['Primary CTA']}</strong></p>")
#     if cta.get("Secondary CTA"):
#         html.append(f"<p>{cta['Secondary CTA']}</p>")
#     html.append("</div>")

#     return "\n".join(html)


def blog_json_to_markdown(blog_json: dict) -> str:
    md = []

    # --- Header ---
    header = blog_json.get("Header", {})
    md.append(f"# {header.get('Main Headline','')}")
    if header.get("Subheadline"):
        md.append(f"## {header['Subheadline']}")
    if header.get("Hero Image URL"):
        md.append(f"![Hero Image]({header['Hero Image URL']})")

    # --- Introduction ---
    intro = blog_json.get("Introduction", {})
    for key in ["Hook sentence", "Context", "Why this topic matters", "Learning outcome"]:
        if intro.get(key):
            md.append(intro[key])

    # --- Main Sections ---
    for section in blog_json.get("Main Sections", []):
        md.append(f"## {section.get('H2: Key Insight','')}")
        md.append(section.get("Explanation paragraph",""))

        bullets = section.get("Bullets", [])
        for bullet in bullets:
            md.append(f"- {bullet}")

        if section.get("Example"):
            md.append(f"> {section['Example']}")

    # --- Conclusion ---
    conclusion = blog_json.get("Conclusion", {})
    md.append("## Conclusion")
    for key in ["Summary", "Action steps", "Final takeaway"]:
        if conclusion.get(key):
            md.append(conclusion[key])

    # --- CTA ---
    cta = blog_json.get("CTA", {})
    if cta.get("Primary CTA"):
        md.append(f"**{cta['Primary CTA']}**")
    if cta.get("Secondary CTA"):
        md.append(cta["Secondary CTA"])

    return "\n\n".join(md)

# ----------------------------
# GENERATE CONTENT PAGE
# ----------------------------
def generate_content_page(user_id):
    conn = common.get_conn()
    cursor = conn.cursor()
    st.header("Generate Content")

    topic = st.text_input("Enter Topic")

    cursor.execute("SELECT id, template_title FROM templates_form WHERE user_id=?", (user_id,))
    templates = cursor.fetchall()

    template_select = st.selectbox("Choose Template", templates, format_func=lambda x: x[1])

    #st.session_state['bit'] = 0
    if 'bit' not in st.session_state:
        st.session_state['bit'] = 0
    bit = st.session_state['bit']
    #st.markdown(f"---{bit}---")
    if st.button("Generate") or bit == 2:
        with st.spinner("⏳ Generating content..."):
            template_id = template_select[0]

            cursor.execute("SELECT * FROM templates_form WHERE id=?", (template_id,))
            t = cursor.fetchone()
            #st.json(t[5])
            st.stop()
            template_json = t[5]
            template_json = json.loads(template_json)
            st.subheader("Template (JSON View)")
            st.markdown(json_to_html(template_json), unsafe_allow_html=True)
            #st.stop()
            generated = generate_content(topic, template_json)
            #st.json(generated)
            #blog_json = json.loads(generated)
            #generated = '[{"section":"Meta Information","fields":{"SEO Title":"India Travel Guide for Business Leaders: Essential Tips & Insights","Slug":"india-travel-guide-business-leaders","SEO Description":"Comprehensive India travel guide tailored for business leaders. Discover visa info, cultural etiquette, key hubs, safety tips, and logistics for successful corporate trips.","Primary Keywords":"India travel guide, Business travel India, India travel tips for executives, India corporate travel guide, India business destination guide, Travel India for business leaders, India business trip planning, India travel essentials for entrepreneurs, Corporate travel India guide","Secondary Keywords":"Best places to visit in India for business travelers, India travel safety for business professionals, India business etiquette and culture, Airport guide India (delhi, mumbai, bengaluru), India visa information for business travelers, India business events and conferences, Hotel recommendations for business travelers in India, Transportation options in India for executives, India travel logistics for entrepreneurs, How to prepare for a business trip to India"}},{"section":"Header","fields":{"Main Headline":"Your Ultimate India Travel Guide for Business Leaders","Subheadline":"Navigate India’s corporate landscape with expert insights on travel, culture, and logistics","Hero Image URL":"https://example.com/images/india-business-travel-hero.jpg"}},{"section":"Introduction","fields":{"Hook sentence":"Planning a business trip to India? Get equipped with everything you need to succeed.","Context":"India is rapidly emerging as a global business hub, with thriving technology, finance, and government sectors attracting entrepreneurs and executives from around the world.","Why this topic matters":"For business leaders, understanding India’s unique travel requirements, cultural nuances, and logistical landscape is essential to maximize productivity and build strong professional partnerships.","Learning outcome":"By the end of this guide, you’ll be fully prepared to plan your India business trip, navigate cultural etiquette, choose optimal business hubs and accommodations, and maintain safety and comfort throughout your journey."}},{"section":"Main Sections","fields":{"H2: Key Insight":"Visa and Travel Essentials for Business Professionals","Explanation paragraph":"Securing the appropriate visa and preparing thoroughly for your trip are crucial first steps for smooth business travel to India. Knowing your visa options, understanding health advisories, and meeting insurance requirements will help you avoid delays and complications.","Bullets":["Apply for the e-Business Visa, which allows multiple entries over a one-year period for short business trips.","Ensure your passport remains valid for at least six months beyond your intended entry date.","Consult a healthcare provider for recommended vaccinations and carry any necessary prescriptions.","Purchase comprehensive travel insurance that covers health issues and travel disruptions.","Keep both digital and physical copies of important documents, including your visa, passport, and insurance."],"Example":"For instance, an entrepreneur attending multiple conferences in Mumbai and Bengaluru within six months can benefit from the e-Business Visa’s flexibility, eliminating the need for repeated visa applications."}},{"section":"Main Sections","fields":{"H2: Key Insight":"Navigating India’s Business Hubs and Transportation","Explanation paragraph":"India’s major business centers each offer distinct advantages and transportation options, enabling efficient travel and productive business operations.","Bullets":["Mumbai: The financial capital of India, hosting major stock exchanges (BSE & NSE) and numerous corporate headquarters.","Bengaluru: Known as India’s tech hub, with a vibrant startup ecosystem and plenty of co-working spaces.","Delhi NCR: The political and administrative center, home to many government offices and multinational corporations.","Use metro systems in Delhi and Bengaluru for efficient urban travel during peak hours.","Rely on trusted ride-hailing services like Ola and Uber for convenient, app-based transportation.","Major airports such as Indira Gandhi International (Delhi), Chhatrapati Shivaji Maharaj (Mumbai), and Kempegowda (Bengaluru) feature business lounges and offer direct international connections."],"Example":"A business leader arriving at Mumbai airport can quickly take a pre-booked Uber to a downtown meeting, then use the local metro system to navigate the city efficiently while avoiding traffic congestion."}},{"section":"Main Sections","fields":{"H2: Key Insight":"Cultural Etiquette and Business Practices in India","Explanation paragraph":"Respecting India’s cultural nuances and business etiquette is vital for smooth communication and building lasting professional relationships.","Bullets":["Address senior executives with proper titles and surnames, such as Mr., Ms., or Dr., to show respect.","Expect indirect communication styles; carefully interpret politeness and pauses during discussions.","Recognize hierarchical decision-making structures; exercise patience during negotiations.","Dress formally and conservatively for business meetings.","Avoid sensitive topics such as politics or religion in conversations.","Be punctual but prepared for minor delays; flexibility helps maintain positive relationships."],"Example":"At a pitch meeting in Delhi, using formal titles and attentively observing subtle cues helped a founder earn trust and successfully secure a partnership."}},{"section":"Main Sections","fields":{"H2: Key Insight":"Safety Tips and Health Considerations for Business Travel","Explanation paragraph":"While India is generally safe for business travelers, staying vigilant and well-prepared can significantly enhance your security and overall experience.","Bullets":["Stay alert in crowded areas, especially in major cities ranked mid-level on the Global Peace Index 2023.","Use hotel safes for valuables and avoid openly displaying expensive electronics or jewelry in public.","Drink only bottled or filtered water; avoid street food unless trusted sources recommend it.","Review travel advisories before and during your trip.","Keep emergency contacts and local embassy information readily accessible.","Carry a basic medical kit and familiarize yourself with nearby hospital options."],"Example":"An executive staying in Bengaluru chose a hotel near the tech park and booked airport transfers through the hotel to avoid unvetted taxis, ensuring smooth and secure transportation."}},{"section":"Main Sections","fields":{"H2: Key Insight":"Optimizing Your Business Trip: Accommodation and Networking Opportunities","Explanation paragraph":"Selecting suitable accommodations and actively engaging in networking events enhance both comfort and business growth during your trip.","Bullets":["Choose hotels offering business amenities, such as meeting rooms, reliable Wi-Fi, and executive lounges.","Consider properties located near key business districts like BKC in Mumbai or Whitefield in Bengaluru.","Utilize co-working spaces for flexible meeting venues and collaboration opportunities.","Attend major industry conferences and business events scheduled during your visit.","Plan meetings within India’s workweek (Monday to Friday), avoiding local holidays.","Use hotel concierge services to arrange local business support or transportation."],"Example":"An entrepreneur staying at the Hilton Mumbai International Airport hotel gained convenient access to conferences and networking lounges, boosting daily productivity."}},{"section":"Conclusion","fields":{"Summary":"India presents dynamic opportunities for business leaders, with thriving hubs, rich culture, and expanding infrastructure. Thoughtful preparation—including visa arrangements, travel logistics, cultural understanding, and safety practices—ensures every business trip is successful and productive.","Action steps":"Begin by applying for the correct visa well in advance, book accommodations close to your business hubs, familiarize yourself with local cultural norms, and plan your transportation ahead. Keep safety top of mind and leverage networking events to broaden your professional connections.","Final takeaway":"With the right planning and approach, your business journey to India can unlock valuable partnerships and lead to lasting success."}},{"section":"CTA","fields":{"Primary CTA":"Download Our India Business Travel Checklist Now","Secondary CTA":"Subscribe for Weekly Business Travel Tips and Updates"}}]'
            #st.json(generated)
            for section, content in generated.items():
                with st.expander(section.title(), expanded=True):
                    st.write(content)

            blog_json = generated
            st.rerun()
            # if isinstance(blog_json, str):
            #     blog_json = json.loads(blog_json)
            # if isinstance(blog_json, list):
            #     if len(blog_json) > 0 and isinstance(blog_json[0], dict):
            #         blog_json = blog_json[0]
            #     else:
            #         st.error("Invalid blog JSON structure")
            #         return
            # if isinstance(blog_json, str):
            #     blog_json = json.loads(blog_json)
            # st.subheader("📄 HTML Preview")

            # st.markdown(blog_json_to_html(blog_json), unsafe_allow_html=True)

            # st.subheader("📝 Markdown Output")
            # st.code(blog_json_to_markdown(blog_json), language="markdown")
            # st.stop()
            # st.subheader("Generated Content")
            # st.markdown(generated)

            # st.session_state['bit'] = 2
            # if generated and st.button("Save Content"):

            #     st.session_state['bit'] = 1
            #     cursor.execute("""
            #         INSERT INTO contents (user_id, topic, template_id, generated_content)
            #         VALUES (?, ?, ?, ?)
            #     """, (user_id, topic, template_id, generated))
            #     conn.commit()
            #     st.success("Content saved!")
            #     st.rerun()
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


def generate_casestudy_content_page(user_id):
    conn = common.get_conn()
    cursor = conn.cursor()
    st.header("Generate Content")
    #st.markdown(f"Use your {st.session_state.get('page', 'Dashboard')}")
    topic = st.text_input("Enter Topic")

    #cursor.execute("SELECT id, template_title FROM templates_form WHERE user_id=?", (user_id,))
    cursor.execute("SELECT id, template_title FROM templates_form")
    templates = cursor.fetchall()

    template_select = st.selectbox("Choose Template", templates, format_func=lambda x: x[1])

    #st.session_state['bit'] = 0
    if 'bit' not in st.session_state:
        st.session_state['bit'] = 0
    bit = st.session_state['bit']
    #st.markdown(f"---{bit}---")
    if st.button("Generate") :
        with st.spinner("⏳ Generating content..."):
            template_id = template_select[0]

            cursor.execute("SELECT * FROM templates_form WHERE id=?", (template_id,))
            t = cursor.fetchone()
            # st.json(t[5])
            # st.stop()
            template_json = t[5]

            #st.subheader("Template (JSON View)")
            #st.markdown(json_to_html(template_json), unsafe_allow_html=True)
            #st.stop()
            #generated = generate_content(topic, template_json)
            generated = crew_casestudy.generate_blog(topic=topic,template_sections=template_json)
            #st.json(generated)
            #st.stop()
            st.success("Case study generated successfully!")
            st.session_state["temp_generated"] = generated
            st.session_state["temp_topic"] = topic
            st.session_state["temp_template_id"] = template_id

            # for section, content in generated.items():
            #     with st.expander(section.title(), expanded=True):
            #         st.write(content)

            st.download_button(
                "⬇ Download Blog JSON",
                json.dumps(generated, indent=2),
                file_name="blog_output.json",
                mime="application/json"
            )
            #blog_json = json.loads(generated)
            #generated = '[{"section":"Meta Information","fields":{"SEO Title":"India Travel Guide for Business Leaders: Essential Tips & Insights","Slug":"india-travel-guide-business-leaders","SEO Description":"Comprehensive India travel guide tailored for business leaders. Discover visa info, cultural etiquette, key hubs, safety tips, and logistics for successful corporate trips.","Primary Keywords":"India travel guide, Business travel India, India travel tips for executives, India corporate travel guide, India business destination guide, Travel India for business leaders, India business trip planning, India travel essentials for entrepreneurs, Corporate travel India guide","Secondary Keywords":"Best places to visit in India for business travelers, India travel safety for business professionals, India business etiquette and culture, Airport guide India (delhi, mumbai, bengaluru), India visa information for business travelers, India business events and conferences, Hotel recommendations for business travelers in India, Transportation options in India for executives, India travel logistics for entrepreneurs, How to prepare for a business trip to India"}},{"section":"Header","fields":{"Main Headline":"Your Ultimate India Travel Guide for Business Leaders","Subheadline":"Navigate India’s corporate landscape with expert insights on travel, culture, and logistics","Hero Image URL":"https://example.com/images/india-business-travel-hero.jpg"}},{"section":"Introduction","fields":{"Hook sentence":"Planning a business trip to India? Get equipped with everything you need to succeed.","Context":"India is rapidly emerging as a global business hub, with thriving technology, finance, and government sectors attracting entrepreneurs and executives from around the world.","Why this topic matters":"For business leaders, understanding India’s unique travel requirements, cultural nuances, and logistical landscape is essential to maximize productivity and build strong professional partnerships.","Learning outcome":"By the end of this guide, you’ll be fully prepared to plan your India business trip, navigate cultural etiquette, choose optimal business hubs and accommodations, and maintain safety and comfort throughout your journey."}},{"section":"Main Sections","fields":{"H2: Key Insight":"Visa and Travel Essentials for Business Professionals","Explanation paragraph":"Securing the appropriate visa and preparing thoroughly for your trip are crucial first steps for smooth business travel to India. Knowing your visa options, understanding health advisories, and meeting insurance requirements will help you avoid delays and complications.","Bullets":["Apply for the e-Business Visa, which allows multiple entries over a one-year period for short business trips.","Ensure your passport remains valid for at least six months beyond your intended entry date.","Consult a healthcare provider for recommended vaccinations and carry any necessary prescriptions.","Purchase comprehensive travel insurance that covers health issues and travel disruptions.","Keep both digital and physical copies of important documents, including your visa, passport, and insurance."],"Example":"For instance, an entrepreneur attending multiple conferences in Mumbai and Bengaluru within six months can benefit from the e-Business Visa’s flexibility, eliminating the need for repeated visa applications."}},{"section":"Main Sections","fields":{"H2: Key Insight":"Navigating India’s Business Hubs and Transportation","Explanation paragraph":"India’s major business centers each offer distinct advantages and transportation options, enabling efficient travel and productive business operations.","Bullets":["Mumbai: The financial capital of India, hosting major stock exchanges (BSE & NSE) and numerous corporate headquarters.","Bengaluru: Known as India’s tech hub, with a vibrant startup ecosystem and plenty of co-working spaces.","Delhi NCR: The political and administrative center, home to many government offices and multinational corporations.","Use metro systems in Delhi and Bengaluru for efficient urban travel during peak hours.","Rely on trusted ride-hailing services like Ola and Uber for convenient, app-based transportation.","Major airports such as Indira Gandhi International (Delhi), Chhatrapati Shivaji Maharaj (Mumbai), and Kempegowda (Bengaluru) feature business lounges and offer direct international connections."],"Example":"A business leader arriving at Mumbai airport can quickly take a pre-booked Uber to a downtown meeting, then use the local metro system to navigate the city efficiently while avoiding traffic congestion."}},{"section":"Main Sections","fields":{"H2: Key Insight":"Cultural Etiquette and Business Practices in India","Explanation paragraph":"Respecting India’s cultural nuances and business etiquette is vital for smooth communication and building lasting professional relationships.","Bullets":["Address senior executives with proper titles and surnames, such as Mr., Ms., or Dr., to show respect.","Expect indirect communication styles; carefully interpret politeness and pauses during discussions.","Recognize hierarchical decision-making structures; exercise patience during negotiations.","Dress formally and conservatively for business meetings.","Avoid sensitive topics such as politics or religion in conversations.","Be punctual but prepared for minor delays; flexibility helps maintain positive relationships."],"Example":"At a pitch meeting in Delhi, using formal titles and attentively observing subtle cues helped a founder earn trust and successfully secure a partnership."}},{"section":"Main Sections","fields":{"H2: Key Insight":"Safety Tips and Health Considerations for Business Travel","Explanation paragraph":"While India is generally safe for business travelers, staying vigilant and well-prepared can significantly enhance your security and overall experience.","Bullets":["Stay alert in crowded areas, especially in major cities ranked mid-level on the Global Peace Index 2023.","Use hotel safes for valuables and avoid openly displaying expensive electronics or jewelry in public.","Drink only bottled or filtered water; avoid street food unless trusted sources recommend it.","Review travel advisories before and during your trip.","Keep emergency contacts and local embassy information readily accessible.","Carry a basic medical kit and familiarize yourself with nearby hospital options."],"Example":"An executive staying in Bengaluru chose a hotel near the tech park and booked airport transfers through the hotel to avoid unvetted taxis, ensuring smooth and secure transportation."}},{"section":"Main Sections","fields":{"H2: Key Insight":"Optimizing Your Business Trip: Accommodation and Networking Opportunities","Explanation paragraph":"Selecting suitable accommodations and actively engaging in networking events enhance both comfort and business growth during your trip.","Bullets":["Choose hotels offering business amenities, such as meeting rooms, reliable Wi-Fi, and executive lounges.","Consider properties located near key business districts like BKC in Mumbai or Whitefield in Bengaluru.","Utilize co-working spaces for flexible meeting venues and collaboration opportunities.","Attend major industry conferences and business events scheduled during your visit.","Plan meetings within India’s workweek (Monday to Friday), avoiding local holidays.","Use hotel concierge services to arrange local business support or transportation."],"Example":"An entrepreneur staying at the Hilton Mumbai International Airport hotel gained convenient access to conferences and networking lounges, boosting daily productivity."}},{"section":"Conclusion","fields":{"Summary":"India presents dynamic opportunities for business leaders, with thriving hubs, rich culture, and expanding infrastructure. Thoughtful preparation—including visa arrangements, travel logistics, cultural understanding, and safety practices—ensures every business trip is successful and productive.","Action steps":"Begin by applying for the correct visa well in advance, book accommodations close to your business hubs, familiarize yourself with local cultural norms, and plan your transportation ahead. Keep safety top of mind and leverage networking events to broaden your professional connections.","Final takeaway":"With the right planning and approach, your business journey to India can unlock valuable partnerships and lead to lasting success."}},{"section":"CTA","fields":{"Primary CTA":"Download Our India Business Travel Checklist Now","Secondary CTA":"Subscribe for Weekly Business Travel Tips and Updates"}}]'
            # print(json.dumps(generated, indent=2))
            # st.json(generated)

            # blog_json = generated
            # # if isinstance(blog_json, str):
            # #     blog_json = json.loads(blog_json)
            # # if isinstance(blog_json, list):
            # #     if len(blog_json) > 0 and isinstance(blog_json[0], dict):
            # #         blog_json = blog_json[0]
            # #     else:
            # #         st.error("Invalid blog JSON structure")
            # #         return
            # if isinstance(blog_json, str):
            #     blog_json = json.loads(blog_json)
            # st.subheader("📄 HTML Preview")

            # st.markdown(blog_json_to_html(blog_json), unsafe_allow_html=True)

            # st.subheader("📝 Markdown Output")
            # st.code(blog_json_to_markdown(blog_json), language="markdown")
            # st.stop()
            # st.subheader("Generated Content")
            # st.markdown(generated)

            st.session_state['bit'] = 2
    if "temp_generated" in st.session_state and st.session_state['temp_generated'] not in [None, ""]:
        st.markdown("### Generated Content Preview")
        topic = st.session_state.get("temp_topic", "")
        st.markdown(f"**Topic:** {topic}")
        if "temp_generated" in st.session_state:
            #st.markdown(f"**Template ID:** {st.session_state['temp_generated']}")
            for section, content in st.session_state['temp_generated'].items():
                with st.expander(section.title(), expanded=True):
                    st.write(content)

    if ("temp_generated" in st.session_state and st.session_state['temp_generated'] not in [None, ""]) and st.button("Save Content"):
    #if st.button("Save Content"):
        #topic = st.session_state["temp_topic"]
        topic = st.session_state.get("temp_topic", "None")
        temp_template_id = st.session_state.get("temp_template_id", "1")
        clean_template = sanitize_for_json(st.session_state['temp_generated'])

        json_string = json.dumps(clean_template, ensure_ascii=False)

        cursor.execute("""
            INSERT INTO contents (user_id, topic, template_id, generated_content)
            VALUES (?, ?, ?, ?)
        """, (user_id, topic, temp_template_id, json_string))
        conn.commit()

        st.session_state['temp_generated'] = None
        st.session_state['temp_topic'] = ""
        st.session_state['temp_template_id'] = ""
        #st.session_state['page'] = "content list"
        st.success("Content saved!")
        st.rerun()

def admin_generate_casestudy_content_page(user_id):
    conn = common.get_conn()
    cursor = conn.cursor()
    st.header("Generate Content")
    #st.markdown(f"Use your {st.session_state.get('page', 'Dashboard')}")
    topic = st.text_input("Enter Topic")

    cursor.execute("SELECT id, template_title FROM templates_form WHERE user_id=?", (user_id,))
    templates = cursor.fetchall()

    template_select = st.selectbox("Choose Template", templates, format_func=lambda x: x[1])

    #st.session_state['bit'] = 0
    if 'bit' not in st.session_state:
        st.session_state['bit'] = 0
    bit = st.session_state['bit']
    #st.markdown(f"---{bit}---")
    if st.button("Generate") :
        with st.spinner("⏳ Generating content..."):
            template_id = template_select[0]

            cursor.execute("SELECT * FROM templates_form WHERE id=?", (template_id,))
            t = cursor.fetchone()
            # st.json(t[5])
            # st.stop()
            template_json = t[5]

            #st.subheader("Template (JSON View)")
            #st.markdown(json_to_html(template_json), unsafe_allow_html=True)
            #st.stop()
            #generated = generate_content(topic, template_json)
            generated = crew_casestudy.generate_blog(topic=topic,template_sections=template_json)
            #st.json(generated)
            #st.stop()
            st.success("Case study generated successfully!")
            st.session_state["temp_generated"] = generated
            st.session_state["temp_topic"] = topic
            st.session_state["temp_template_id"] = template_id

            # for section, content in generated.items():
            #     with st.expander(section.title(), expanded=True):
            #         st.write(content)

            st.download_button(
                "⬇ Download Blog JSON",
                json.dumps(generated, indent=2),
                file_name="blog_output.json",
                mime="application/json"
            )
            #blog_json = json.loads(generated)
            #generated = '[{"section":"Meta Information","fields":{"SEO Title":"India Travel Guide for Business Leaders: Essential Tips & Insights","Slug":"india-travel-guide-business-leaders","SEO Description":"Comprehensive India travel guide tailored for business leaders. Discover visa info, cultural etiquette, key hubs, safety tips, and logistics for successful corporate trips.","Primary Keywords":"India travel guide, Business travel India, India travel tips for executives, India corporate travel guide, India business destination guide, Travel India for business leaders, India business trip planning, India travel essentials for entrepreneurs, Corporate travel India guide","Secondary Keywords":"Best places to visit in India for business travelers, India travel safety for business professionals, India business etiquette and culture, Airport guide India (delhi, mumbai, bengaluru), India visa information for business travelers, India business events and conferences, Hotel recommendations for business travelers in India, Transportation options in India for executives, India travel logistics for entrepreneurs, How to prepare for a business trip to India"}},{"section":"Header","fields":{"Main Headline":"Your Ultimate India Travel Guide for Business Leaders","Subheadline":"Navigate India’s corporate landscape with expert insights on travel, culture, and logistics","Hero Image URL":"https://example.com/images/india-business-travel-hero.jpg"}},{"section":"Introduction","fields":{"Hook sentence":"Planning a business trip to India? Get equipped with everything you need to succeed.","Context":"India is rapidly emerging as a global business hub, with thriving technology, finance, and government sectors attracting entrepreneurs and executives from around the world.","Why this topic matters":"For business leaders, understanding India’s unique travel requirements, cultural nuances, and logistical landscape is essential to maximize productivity and build strong professional partnerships.","Learning outcome":"By the end of this guide, you’ll be fully prepared to plan your India business trip, navigate cultural etiquette, choose optimal business hubs and accommodations, and maintain safety and comfort throughout your journey."}},{"section":"Main Sections","fields":{"H2: Key Insight":"Visa and Travel Essentials for Business Professionals","Explanation paragraph":"Securing the appropriate visa and preparing thoroughly for your trip are crucial first steps for smooth business travel to India. Knowing your visa options, understanding health advisories, and meeting insurance requirements will help you avoid delays and complications.","Bullets":["Apply for the e-Business Visa, which allows multiple entries over a one-year period for short business trips.","Ensure your passport remains valid for at least six months beyond your intended entry date.","Consult a healthcare provider for recommended vaccinations and carry any necessary prescriptions.","Purchase comprehensive travel insurance that covers health issues and travel disruptions.","Keep both digital and physical copies of important documents, including your visa, passport, and insurance."],"Example":"For instance, an entrepreneur attending multiple conferences in Mumbai and Bengaluru within six months can benefit from the e-Business Visa’s flexibility, eliminating the need for repeated visa applications."}},{"section":"Main Sections","fields":{"H2: Key Insight":"Navigating India’s Business Hubs and Transportation","Explanation paragraph":"India’s major business centers each offer distinct advantages and transportation options, enabling efficient travel and productive business operations.","Bullets":["Mumbai: The financial capital of India, hosting major stock exchanges (BSE & NSE) and numerous corporate headquarters.","Bengaluru: Known as India’s tech hub, with a vibrant startup ecosystem and plenty of co-working spaces.","Delhi NCR: The political and administrative center, home to many government offices and multinational corporations.","Use metro systems in Delhi and Bengaluru for efficient urban travel during peak hours.","Rely on trusted ride-hailing services like Ola and Uber for convenient, app-based transportation.","Major airports such as Indira Gandhi International (Delhi), Chhatrapati Shivaji Maharaj (Mumbai), and Kempegowda (Bengaluru) feature business lounges and offer direct international connections."],"Example":"A business leader arriving at Mumbai airport can quickly take a pre-booked Uber to a downtown meeting, then use the local metro system to navigate the city efficiently while avoiding traffic congestion."}},{"section":"Main Sections","fields":{"H2: Key Insight":"Cultural Etiquette and Business Practices in India","Explanation paragraph":"Respecting India’s cultural nuances and business etiquette is vital for smooth communication and building lasting professional relationships.","Bullets":["Address senior executives with proper titles and surnames, such as Mr., Ms., or Dr., to show respect.","Expect indirect communication styles; carefully interpret politeness and pauses during discussions.","Recognize hierarchical decision-making structures; exercise patience during negotiations.","Dress formally and conservatively for business meetings.","Avoid sensitive topics such as politics or religion in conversations.","Be punctual but prepared for minor delays; flexibility helps maintain positive relationships."],"Example":"At a pitch meeting in Delhi, using formal titles and attentively observing subtle cues helped a founder earn trust and successfully secure a partnership."}},{"section":"Main Sections","fields":{"H2: Key Insight":"Safety Tips and Health Considerations for Business Travel","Explanation paragraph":"While India is generally safe for business travelers, staying vigilant and well-prepared can significantly enhance your security and overall experience.","Bullets":["Stay alert in crowded areas, especially in major cities ranked mid-level on the Global Peace Index 2023.","Use hotel safes for valuables and avoid openly displaying expensive electronics or jewelry in public.","Drink only bottled or filtered water; avoid street food unless trusted sources recommend it.","Review travel advisories before and during your trip.","Keep emergency contacts and local embassy information readily accessible.","Carry a basic medical kit and familiarize yourself with nearby hospital options."],"Example":"An executive staying in Bengaluru chose a hotel near the tech park and booked airport transfers through the hotel to avoid unvetted taxis, ensuring smooth and secure transportation."}},{"section":"Main Sections","fields":{"H2: Key Insight":"Optimizing Your Business Trip: Accommodation and Networking Opportunities","Explanation paragraph":"Selecting suitable accommodations and actively engaging in networking events enhance both comfort and business growth during your trip.","Bullets":["Choose hotels offering business amenities, such as meeting rooms, reliable Wi-Fi, and executive lounges.","Consider properties located near key business districts like BKC in Mumbai or Whitefield in Bengaluru.","Utilize co-working spaces for flexible meeting venues and collaboration opportunities.","Attend major industry conferences and business events scheduled during your visit.","Plan meetings within India’s workweek (Monday to Friday), avoiding local holidays.","Use hotel concierge services to arrange local business support or transportation."],"Example":"An entrepreneur staying at the Hilton Mumbai International Airport hotel gained convenient access to conferences and networking lounges, boosting daily productivity."}},{"section":"Conclusion","fields":{"Summary":"India presents dynamic opportunities for business leaders, with thriving hubs, rich culture, and expanding infrastructure. Thoughtful preparation—including visa arrangements, travel logistics, cultural understanding, and safety practices—ensures every business trip is successful and productive.","Action steps":"Begin by applying for the correct visa well in advance, book accommodations close to your business hubs, familiarize yourself with local cultural norms, and plan your transportation ahead. Keep safety top of mind and leverage networking events to broaden your professional connections.","Final takeaway":"With the right planning and approach, your business journey to India can unlock valuable partnerships and lead to lasting success."}},{"section":"CTA","fields":{"Primary CTA":"Download Our India Business Travel Checklist Now","Secondary CTA":"Subscribe for Weekly Business Travel Tips and Updates"}}]'
            # print(json.dumps(generated, indent=2))
            # st.json(generated)

            # blog_json = generated
            # # if isinstance(blog_json, str):
            # #     blog_json = json.loads(blog_json)
            # # if isinstance(blog_json, list):
            # #     if len(blog_json) > 0 and isinstance(blog_json[0], dict):
            # #         blog_json = blog_json[0]
            # #     else:
            # #         st.error("Invalid blog JSON structure")
            # #         return
            # if isinstance(blog_json, str):
            #     blog_json = json.loads(blog_json)
            # st.subheader("📄 HTML Preview")

            # st.markdown(blog_json_to_html(blog_json), unsafe_allow_html=True)

            # st.subheader("📝 Markdown Output")
            # st.code(blog_json_to_markdown(blog_json), language="markdown")
            # st.stop()
            # st.subheader("Generated Content")
            # st.markdown(generated)

            st.session_state['bit'] = 2
    if "temp_generated" in st.session_state:
        st.markdown("### Generated Content Preview")
        topic = st.session_state.get("temp_topic", "")
        st.markdown(f"**Topic:** {topic}")
        for section, content in st.session_state['temp_generated'].items():
            with st.expander(section.title(), expanded=True):
                st.write(content)
    if "temp_generated" in st.session_state and st.button("Save Content"):
    #if st.button("Save Content"):
        #topic = st.session_state["temp_topic"]
        topic = st.session_state.get("temp_topic", "None")
        temp_template_id = st.session_state.get("temp_template_id", "1")
        clean_template = sanitize_for_json(st.session_state['temp_generated'])

        json_string = json.dumps(clean_template, ensure_ascii=False)

        cursor.execute("""
            INSERT INTO contents (user_id, topic, template_id, generated_content)
            VALUES (?, ?, ?, ?)
        """, (user_id, topic, temp_template_id, json_string))
        conn.commit()

        st.session_state['temp_generated'] = None
        st.session_state['temp_topic'] = ""
        st.session_state['temp_template_id'] = ""
        #st.session_state['page'] = "content list"
        st.success("Content saved!")
        st.rerun()

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
