"""
Compact Optimized CrewAI v3 — Human-likeness focused pipeline (structure B)
Target: 85-95% human-likeness

Features:
- Compact, detector-resistant ordering
- Researcher -> Writer -> 3 Micro Humanizers -> MemoryNoise -> RhythmBreaker -> Overthinker -> EntropyBreaker -> Imperfection-friendly Editor -> Final Disorder -> Publisher
- Model-mixing entropy pass (different LLM) to break model signatures
- Tunable parameters at top for fast experimentation

Drop-in: replace your current pipeline with this file. Tune PASSES_PER_SECTION, MICRO_COUNTS, and model names.
"""

import os
import time
import uuid
import random
import logging
import threading
from dotenv import load_dotenv
import streamlit as st
import json

import common
from crewai import Agent, Task, Crew
from tools.serper_tool import SerperTool
from crew_safe_llm import CrewSafeLLM

# ---------------- Utilities ----------------
logging.basicConfig(level=logging.INFO)
load_dotenv()


def _uniq(name: str) -> str:
    return f"{name}-{uuid.uuid4().hex[:6]}"

def safe_output_to_json(result):
    try:
        if hasattr(result, 'raw'):
            return {'result': result.raw}
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        return {'result': str(result)}
    except Exception as e:
        return {'error': str(e)}




# Assuming the run_pipeline and CrewAI setup are in place...



PROGRESS_LOG = []

def run_safe_pipeline_with_progress(crew, tasks):
    """
    Corrected version of V8. Runs the CrewAI pipeline with task-by-task progress.
    Fixes the 'Task Log' appending issue by using a dedicated placeholder inside the container.
    """

    global PROGRESS_LOG
    PROGRESS_LOG = [] # Reset the log for a new run
    total = len(tasks)

    result_container = {'result': None}

    # 1. DEFINE PERMANENT UI ELEMENTS
    st.markdown("## 📋 Pipeline Execution Log")
    detailed_log_container = st.container()

    # Define the placeholder once inside the permanent container
    with detailed_log_container:
        st.markdown("### Task Details") # Keep the heading static
        task_list_placeholder = st.empty() # THIS is the element we will update repeatedly

    def run_crew_sequential():
        # ... (run_crew_sequential remains the same as in V7/V8)
        nonlocal result_container

        for i, task in enumerate(tasks):
            agent_name = task.agent.role
            task_desc = task.description

            PROGRESS_LOG.append({'status': 'STARTING', 'index': i, 'agent': agent_name, 'desc': task_desc})

            # NOTE: Create a minimal crew to run only this single task (required for logging between tasks)
            single_task_crew = Crew(agents=[task.agent], tasks=[task], verbose=False)

            try:
                task_result = single_task_crew.kickoff(inputs={})

                PROGRESS_LOG.append({'status': 'FINISHED', 'index': i, 'agent': agent_name, 'result': task_result})

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
                    markdown_list += f"* **▶️ Working:** **{task.agent.role}: {task.description}**\n"
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
    return final_result



# def run_safe_pipeline_with_progress(crew, tasks):
#     #global PERSONALITIES
#     """Lightweight Streamlit progress UI used by examples."""

#     st.subheader("🚀 Running Compact Humanized Pipeline")
#     progress = st.progress(0)
#     status = st.empty()
#     logs = st.empty()
#     log_text = ""
#     total = len(tasks)
#     #st.json(PERSONALITIES)
#     #st.dataframe(PERSONALITIES)
#     # for  item in enumerate(PERSONALITIES, start=1):
#     #     st.write(f"{item}")
#     # quick preview
#     for i, t in enumerate(tasks):
#         status.markdown(f"**Preparing Task {i+1}/{total}:** {getattr(t.agent,'role','Unknown')}")
#         log_text += f"\n- {t.description}"
#         logs.markdown(log_text)
#         progress.progress((i+1)/total * 0.2)
#         time.sleep(0.12)

#     status.markdown("**Executing pipeline...**")
#     result_container = {'result': None}
#     #st.stop()
#     # run in thread to keep UI responsive
#     def run_crew():
#         try:
#             result_container['result'] = crew.kickoff()
#         except Exception as e:
#             result_container['result'] = f"⚠ Crew kickoff failed: {e}"

#     thread = threading.Thread(target=run_crew)
#     thread.start()

#     p = int(total * 0.2 * 100)
#     while thread.is_alive():
#         p = min(p + random.randint(1,4), 98)
#         progress.progress(p/100)
#         status.markdown(f"**Running... {p}%**")
#         time.sleep(0.25)

#     thread.join()
#     progress.progress(1.0)
#     status.markdown("**Pipeline complete**")
#     logs.markdown(log_text + "\n\n**Finished.**")
#     return safe_output_to_json(result_container['result'])

# ---------------- Config (tune these) ----------------
# MICRO_INTRO = 2
# MICRO_BODY = 4
# MICRO_CONCLUSION = 2
# PASSES_PER_SECTION = int(os.getenv('HUMANIZER_REFINEMENTS', 1))
# MAX_REAL_TASKS = 40
MICRO_INTRO = 2
MICRO_BODY = 4
MICRO_CONCLUSION = 2
PASSES_PER_SECTION = int(os.getenv('HUMANIZER_REFINEMENTS', 1))
MAX_REAL_TASKS = 40

PERSONALITIES = [
        'sarcastic friend','nostalgic storyteller','curious teacher','chaotic thinker','casual confidant',
        'skeptical critic','optimistic mentor','grumpy old-timer','chatty neighbor','daydreamer'
    ]
if "user_info" not in st.session_state:
    PERSONALITIES = [
        'sarcastic friend','nostalgic storyteller','curious teacher','chaotic thinker','casual confidant',
        'skeptical critic','optimistic mentor','grumpy old-timer','chatty neighbor','daydreamer'
    ]
else:
    user = st.session_state.get("user_info")
    #user = st.session_state['user_info']
    try:
        user_id = user['id']
    except TypeError:
        # This catches the 'NoneType' object is not subscriptable error
        print("Error: Failed to retrieve user data (variable 'user' is None).")
        user_id = None
    #user_id = user['id']
    selected_tones = common.get_selected_tones_by_user(user_id)
    PERSONALITIES = selected_tones if selected_tones else PERSONALITIES






PRIMARY_MODEL = os.getenv('PRIMARY_MODEL', 'gpt-4.1-mini')
ENTROPY_MODEL = os.getenv('ENTROPY_MODEL', 'gpt-4o-mini')

# ---------------- Pipeline builder (compact B) ----------------
# st.json(PERSONALITIES)

def run_pipeline(topic: str,
                         researcher_goal: str,
                         writer_goal: str,
                         editor_goal: str,
                         researcher_backstory: str = "Experienced researcher",
                         writer_backstory: str = "Practical messy writer",
                         editor_backstory: str = "Editor preserving human flaws"):
    """Builds and executes the compact, optimized pipeline for a given topic."""

    serper = SerperTool()
    primary_llm = CrewSafeLLM(model=PRIMARY_MODEL, temperature=1.0)
    entropy_llm = CrewSafeLLM(model=ENTROPY_MODEL, temperature=1.7)

    # 1) Researcher: messy interpretive notes
    researcher = Agent(
        role='Researcher',
        goal=(researcher_goal + " Provide messy interpretive research notes with doubt and short opinions."),
        backstory=researcher_backstory,
        tools=[serper],
        verbose=True,
        llm=primary_llm,
        llm_config={'temperature':1.05,'presence_penalty':0.5,'frequency_penalty':0.45}
    )

    # 2) Writer: messy first draft
    writer = Agent(
        role='Content Writer',
        goal=(writer_goal + " Produce a messy human-first draft with tangents, rhetorical questions, and uneven sentences."),
        backstory=writer_backstory,
        verbose=True,
        llm=primary_llm,
        llm_config={'temperature':1.15,'presence_penalty':0.9,'frequency_penalty':0.75}
    )

    # 3) Micro-humanizers (3 small agents with different personas)
    micro_agents = []
    micro_tasks = []
    def make_micro(section, i):
        persona = random.choice(PERSONALITIES)
        name = _uniq(f"Micro-{section}-{i}")
        a = Agent(
            role=name,
            goal=(f"Rewrite assigned micro-section ({section}#{i}) with persona: {persona}. Inject small digressions, rhetorical Qs, mild grammar breaks."),
            backstory=f"You are a {persona}",
            verbose=True,
            llm=primary_llm,
            llm_config={'temperature':1.3,'presence_penalty':1.05}
        )
        return a

    # create small set of micro agents
    idx = 1
    for i in range(1, MICRO_INTRO+1):
        a = make_micro('intro', i); micro_agents.append(a); micro_tasks.append(Task(description=f"Rewrite micro-intro {i}", expected_output=f"intro-{i}", agent=a))
    for i in range(1, MICRO_BODY+1):
        a = make_micro('body', i); micro_agents.append(a); micro_tasks.append(Task(description=f"Rewrite micro-body {i}", expected_output=f"body-{i}", agent=a))
    for i in range(1, MICRO_CONCLUSION+1):
        a = make_micro('conclusion', i); micro_agents.append(a); micro_tasks.append(Task(description=f"Rewrite micro-conclusion {i}", expected_output=f"conclusion-{i}", agent=a))

    # 4) Memory noise agent (global small inconsistencies)
    memory_noise = Agent(
        role='MemoryNoise',
        goal='Introduce 2-4 tiny human memory inconsistencies (dates, small numbers) without breaking key facts.',
        backstory='You misremember little details occasionally.',
        verbose=True,
        llm=primary_llm,
        llm_config={'temperature':1.25}
    )

    # 5) Rhythm breaker (cadence changes)
    rhythm = Agent(
        role='RhythmBreaker',
        goal='Change sentence rhythm: short line, then long run-on, then medium. Break regular cadence across paragraphs.',
        backstory='You speak with uneven cadence.',
        verbose=True,
        llm=primary_llm,
        llm_config={'temperature':1.35}
    )

    # 6) Human Overthinker (global messy pass)
    overthink = Agent(
        role='HumanOverthinker',
        goal=('Rewrite ENTIRE draft with readable human flaws: second thoughts, mild contradictions, micro-digressions.'),
        backstory='You think out loud and write in a messy way.',
        verbose=True,
        llm=primary_llm,
        llm_config={'temperature':1.45,'presence_penalty':1.25}
    )

    # 7) Entropy breaker (different LLM pass) — model mix
    entropy = Agent(
        role='EntropyBreaker',
        goal='Rewrite draft using alternate phrasing, unexpected idioms, and different world choices to break model signature.',
        backstory='You are impulsive and different from the main writer.',
        verbose=True,
        llm=entropy_llm,
        llm_config={'temperature':1.7,'presence_penalty':1.4}
    )

    # 8) Editor: preserve imperfections
    editor = Agent(
        role='Editor',
        goal=(editor_goal + ' Fix only clarity issues. Preserve voice, tangents and mild contradictions. Do NOT sanitize.'),
        backstory=editor_backstory,
        verbose=True,
        llm=primary_llm,
        llm_config={'temperature':0.6}
    )

    # 9) Final disorder (polish randomness but keep readable)
    final_disorder = Agent(
        role='FinalDisorder',
        goal='Make final small readable unpredictable edits: interjections, small contradictions, interruptions.',
        backstory='You are the last humanizer.',
        verbose=True,
        llm=primary_llm,
        llm_config={'temperature':1.5}
    )

    # 10) Publisher (format only)
    publisher = Agent(
        role='Publisher',
        goal='Format the final article to markdown/HTML without altering voice or content meaning.',
        backstory='You are purely a formatter.',
        verbose=True,
        llm=primary_llm,
        llm_config={'temperature':0.5}
    )

    # ---------------- Build tasks ----------------
    tasks = [
        Task(description=f"Research '{topic}' with interpretive notes.", expected_output='research-notes', agent=researcher),
        Task(description=f"Write messy raw draft for '{topic}'.", expected_output='raw-draft', agent=writer),
        Task(description='Light edit (keep voice).', expected_output='light-edited', agent=editor),
    ]

    # micro rewrite tasks
    tasks.extend(micro_tasks)

    # local micro refinement passes (light)
    refinement_tasks = []
    for idx, m in enumerate(micro_agents, start=1):
        for p in range(1, PASSES_PER_SECTION+1):
            if len(refinement_tasks) < MAX_REAL_TASKS:
                refinement_tasks.append(Task(description=f"Refine micro {idx} pass {p}: add small digression/hesitancy.", expected_output=f"micro-{idx}-p{p}", agent=m))
    tasks.extend(refinement_tasks)

    # injectors: memory noise + rhythm
    tasks.append(Task(description='Introduce tiny memory inconsistencies across the draft.', expected_output='memory-noise', agent=memory_noise))
    tasks.append(Task(description='Apply rhythm changes across draft to break sentence length regularity.', expected_output='rhythm-changed', agent=rhythm))

    # merge & global passes: overthink -> entropy -> final disorder -> publisher
    tasks.append(Task(description='Overthink full-document messy pass.', expected_output='overthought-draft', agent=overthink))
    tasks.append(Task(description='Entropy model-mix rewrite to break model fingerprints.', expected_output='entropy-draft', agent=entropy))
    tasks.append(Task(description='Final readable disorder pass.', expected_output='final-disorder', agent=final_disorder))
    tasks.append(Task(description='Format article for publish (markdown).', expected_output='publish-ready', agent=publisher))

    # assemble agents list
    agents = [
        researcher, writer, editor,
        *micro_agents,
        memory_noise, rhythm,
        overthink, entropy,
        final_disorder, publisher
    ]
    # st.json({'total_agents': len(agents), 'total_tasks': len(tasks)})
    # st.json(agents)
    # st.json(tasks)
    # ---------------- Run crew ----------------
    crew = Crew(agents=agents, tasks=tasks, verbose=True)
    return run_safe_pipeline_with_progress(crew, tasks)

# ---------------- Example run helper (Streamlit UI) ----------------
if __name__ == '__main__':
    st.title('Compact CrewAI v3 — Humanized Pipeline (B)')
    topic = st.text_input('Topic', 'Artificial Intelligence (AI) & Machine Learning')
    if st.button('Run Pipeline'):
        out = run_pipeline(
            topic=topic,
            researcher_goal='Investigate this topic in a messy but accurate way.',
            writer_goal='Write a first messy draft about the topic.',
            editor_goal='Lightly edit for clarity but preserve mess.'
        )
        st.json(out)

# End of file
