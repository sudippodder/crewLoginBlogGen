import csv
import json
import streamlit as st
import os

current_directory = os.getcwd()

from dotenv import load_dotenv
load_dotenv()

from crewai import Agent, Task, Crew, Process




# st.set_page_config(page_title="CrewAI Blog Generator", layout="wide")
# st.title("🧠 CrewAI Blog Content Generator")

# -------------------------------
# Load Template
# -------------------------------
@st.cache_data
def load_template():
    st.info("Loading blog template...--case_study_template")
    with open("case_study_template.json", "r", encoding="utf-8") as f:
        return json.load(f)

#TEMPLATE = load_template()

# -------------------------------
# Agent Factory
# -------------------------------
def build_agents(section_name, cfg):
    agent_cfg = cfg["agents"]["researcher"]
    researcher = Agent(
        role=agent_cfg["role"],
        goal=cfg["goal"],
        backstory=cfg["agents"]["researcher"]["focus"],
        llm_config={"model": "gpt-4o-mini"},
        verbose=False
    )

    writer = Agent(
        role=cfg["agents"]["writer"]["role"],
        goal=f"Write {section_name} section",
        backstory=cfg["agents"]["writer"]["instruction"],
        llm_config={"model": "gpt-4o-mini"},
        verbose=False
    )

    editor = Agent(
        role=cfg["agents"]["editor"]["role"],
        goal=f"Edit {section_name} section",
        backstory=cfg["agents"]["editor"]["instruction"],
        llm_config={"model": "gpt-4o-mini"},
        verbose=False
    )

    return researcher, writer, editor

# -------------------------------
# Task Factory
# -------------------------------
def build_tasks(section_name, cfg, topic):
    researcher, writer, editor = build_agents(section_name, cfg)

    research_task = Task(
        description=f"""
Research for section: {section_name}

Topic:
{topic}

Goal:
{cfg['goal']}

Structure:
{cfg['structure']}
""",
        expected_output="Structured research notes",
        agent=researcher
    )

    write_task = Task(
        description=f"""
Write the {section_name} section.

Topic:
{topic}

Goal:
{cfg['goal']}

Required Structure:
{cfg['structure']}

Writing Rules:
{cfg['writing_rules']}

Tone:
{cfg['tone']}

Word Limit:
{cfg['word_limit']} words

IMPORTANT:
- Plain text only
- Follow structure exactly
- Do not exceed word limit
""",
        expected_output=f"Max {cfg['word_limit']} words",
        agent=writer,
        context=[research_task]
    )

    edit_task = Task(
        description=f"""
Edit the {section_name} section.

Rules:
- Maintain tone: {cfg['tone']}
- Respect word limit: {cfg['word_limit']}
- Improve clarity and flow
- Do NOT add new information
""",
        expected_output="Final polished section content",
        agent=editor,
        context=[write_task]
    )

    # ✅ RETURN TASKS, NOT AGENT
    return research_task, write_task, edit_task

# -------------------------------
# Generate Blog
# -------------------------------
def generate_blog(topic,template_sections):
    all_tasks = []
    all_agents = []
    final_edit_tasks = {}
    #st.json(template_sections)
    template_sections = json.loads(template_sections)
    #st.json(template_sections)
    for section_name, cfg in template_sections.items():
        research_task, write_task, edit_task = build_tasks(section_name, cfg, topic)

        all_tasks.extend([research_task, write_task, edit_task])
        all_agents.extend([
            research_task.agent,
            write_task.agent,
            edit_task.agent
        ])

        # ✅ STORE EDIT TASK
        final_edit_tasks[section_name] = edit_task

    crew = Crew(
        agents=list({id(a): a for a in all_agents}.values()),
        tasks=all_tasks,
        process=Process.sequential
    )

    crew.kickoff()

    output = {}
    for section, task in final_edit_tasks.items():
        output[section] = task.output.raw   # ✅ task.output exists

    return output

# -------------------------------
# UI
# -------------------------------
# topic = st.text_input("Enter Blog Topic", "India travel guide")

# if st.button("🚀 Generate Blog"):
#     with st.spinner("Generating blog content..."):
#         blog_output = generate_blog(topic)

#     st.success("Blog generated successfully!")

#     for section, content in blog_output.items():
#         with st.expander(section.title(), expanded=True):
#             st.write(content)

#     st.download_button(
#         "⬇ Download Blog JSON",
#         json.dumps(blog_output, indent=2),
#         file_name="blog_output.json",
#         mime="application/json"
#     )
