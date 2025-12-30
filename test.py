import csv
import json
import streamlit as st
import os

current_directory = os.getcwd()

from dotenv import load_dotenv
load_dotenv()

from crewai import Agent, Task, Crew, Process

CSV_PATH = current_directory + "/Case_Study_Template.csv"
st.write(CSV_PATH)
TOPIC = "India travel guide"

# ------------------------------------------------
# Load CSV Template
# ------------------------------------------------
def load_template(csv_path):
    import csv

    sections = []

    with open(csv_path, newline="", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Normalize keys & values
            clean_row = {k.strip(): (v.strip() if isinstance(v, str) else v)
                         for k, v in row.items()}
            sections.append(clean_row)

    return sections



# ------------------------------------------------
# Agent Factory
# ------------------------------------------------
def build_agents(section):
    researcher = Agent(
        role=f"{section['section_name']} Researcher",
        goal=section["section_goal"],
        backstory="You are an expert researcher providing accurate, structured insights.",
        llm_config={"model": "gpt-4o-mini"},
        verbose=False
    )

    writer = Agent(
        role=f"{section['section_name']} Writer",
        goal="Write high-quality section content",
        backstory=f"You write content with tone: {section['tone']}",
        llm_config={"model": "gpt-4o-mini"},
        verbose=False
    )

    editor = Agent(
        role=f"{section['section_name']} Editor",
        goal="Polish content while respecting constraints",
        backstory="Senior editor ensuring clarity, tone consistency, and word limits.",
        llm_config={"model": "gpt-4o-mini"},
        verbose=False
    )

    return researcher, writer, editor


# ------------------------------------------------
# Task Factory
# ------------------------------------------------
def build_tasks(section, topic):
    researcher, writer, editor = build_agents(section)

    research_task = Task(
        description=f"""
Research for section: {section['section_name']}

Topic:
{topic}

Research Focus:
{section['research_focus']}

Goal:
{section['section_goal']}
""",
        expected_output="Structured research notes",
        agent=researcher
    )

    writing_task = Task(
        description=f"""
Write the section: {section['section_name']}

Instructions:
{section['writing_instruction']}

Tone:
{section['tone']}

Word Limit:
{section['word_limit']} words

IMPORTANT:
- Stay within word limit
- Plain text only
""",
        expected_output=f"Max {section['word_limit']} words",
        agent=writer,
        context=[research_task]
    )

    editing_task = Task(
        description=f"""
Edit the section: {section['section_name']}

Editing Instructions:
{section['editing_instruction']}

Rules:
- Maintain tone: {section['tone']}
- Do NOT increase length
- Improve clarity and flow
""",
        expected_output="Final polished section content",
        agent=editor,
        context=[writing_task]
    )

    return research_task, writing_task, editing_task


# ------------------------------------------------
# Generate Blog
# ------------------------------------------------
def generate_blog(topic):

    template_sections = load_template(CSV_PATH)
    all_tasks = []
    final_output = {}
    st.write(template_sections)
    for section in template_sections:
        research_task, writing_task, editing_task = build_tasks(section, topic)
        all_tasks.extend([research_task, writing_task, editing_task])

        final_output[section["section_name"]] = {
            "goal": section["section_goal"],
            "tone": section["tone"],
            "word_limit": section["word_limit"],
            "content_task": editing_task  # placeholder
        }
    st.json(final_output)
    crew = Crew(
        agents=[],  # agents are bound to tasks
        tasks=all_tasks,
        process=Process.sequential
    )

    #crew.kickoff()

    # Collect outputs
    for section in template_sections:
        section_name = section["section_name"]
        task = next(
            t for t in all_tasks
            if t.agent.role.startswith(section_name)
            and "Editor" in t.agent.role
        )

        final_output[section_name]["content"] = task.output

    return final_output


# ------------------------------------------------
# Run
# ------------------------------------------------
if __name__ == "__main__":
    blog = generate_blog(TOPIC)

    print(json.dumps(blog, indent=2))
