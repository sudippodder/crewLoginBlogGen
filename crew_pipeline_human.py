import os
import time
import uuid
import random
import logging
import threading
from dotenv import load_dotenv
import streamlit as st
import json

# Assuming 'common', 'tools.serper_tool', and 'crew_safe_llm' modules exist
import common
from crewai import Agent, Task, Crew
from tools.serper_tool import SerperTool
from crew_safe_llm import CrewSafeLLM

# ---------------- Utilities ----------------
logging.basicConfig(level=logging.INFO)
load_dotenv()

session_id = str(uuid.uuid4())
os.environ['CREW_SESSION_ID'] = session_id

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

# Global log for progress tracking
PROGRESS_LOG = []

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


# ---------------- Config (tune these) ----------------
MICRO_INTRO = 1
MICRO_BODY = 0
MICRO_CONCLUSION = 0
#PASSES_PER_SECTION = int(os.getenv('HUMANIZER_REFINEMENTS', 1))

PASSES_PER_SECTION = 0
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
    try:
        user_id = user['id']
    except TypeError:
        print("Error: Failed to retrieve user data (variable 'user' is None).")
        user_id = None
    selected_tones = common.get_selected_tones_by_user(user_id)
    PERSONALITIES = selected_tones if selected_tones else PERSONALITIES


PRIMARY_MODEL = os.getenv('PRIMARY_MODEL', 'gpt-4.1-mini')
ENTROPY_MODEL = os.getenv('ENTROPY_MODEL', 'gpt-4o-mini')

# ---------------- Pipeline builder (compact B) ----------------

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
        goal=researcher_goal,
        backstory=researcher_backstory,
        tools=[serper],
        verbose=True,
        llm=primary_llm,
        llm_config={'temperature':1.05,'presence_penalty':0.5,'frequency_penalty':0.45}
    )

    # 2) Writer: messy first draft
    writer = Agent(
        role='Content Writer',
        goal=writer_goal,
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
    # 🌟 FIX 6: Update task description to reference {{draft_content}}
    for i in range(1, MICRO_INTRO+1):
        a = make_micro('intro', i); micro_agents.append(a); micro_tasks.append(Task(description=f"Rewrite micro-intro {i} of the draft: {{draft_content}}", expected_output=f"intro-{i}", agent=a))
    for i in range(1, MICRO_BODY+1):
        a = make_micro('body', i); micro_agents.append(a); micro_tasks.append(Task(description=f"Rewrite micro-body {i} of the draft: {{draft_content}}", expected_output=f"body-{i}", agent=a))
    for i in range(1, MICRO_CONCLUSION+1):
        a = make_micro('conclusion', i); micro_agents.append(a); micro_tasks.append(Task(description=f"Rewrite micro-conclusion {i} of the draft: {{draft_content}}", expected_output=f"conclusion-{i}", agent=a))

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
        goal=editor_goal,
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
        # Task 0 (Researcher): Needs topic. Output is passed to Task 1 as {{draft_content}}.
        Task(description=f"Research '{{topic}}' with interpretive notes. Output ONLY the interpretive notes.", expected_output='research-notes', agent=researcher),

        # Task 1 (Writer): Needs topic and research notes ({{draft_content}}). Output is the raw draft.
        Task(description=f"Write messy raw draft for '{{topic}}' using the following research notes: {{draft_content}}.", expected_output='raw-draft', agent=writer),

        # Task 2 (Editor): Needs draft ({{draft_content}}).
        #Task(description='Light edit (keep voice) of the following draft: {{draft_content}}.', expected_output='light-edited', agent=editor),
    ]

    # micro rewrite tasks
    tasks.extend(micro_tasks)

    # local micro refinement passes (light)
    # refinement_tasks = []
    # for idx, m in enumerate(micro_agents, start=1):
    #     for p in range(1, PASSES_PER_SECTION+1):
    #         if len(refinement_tasks) < MAX_REAL_TASKS:
    #             # 🌟 FIX 6: Update task description to reference {{draft_content}}
    #             refinement_tasks.append(Task(description=f"Refine micro {idx} pass {p}: add small digression/hesitancy to the draft: {{draft_content}}.", expected_output=f"micro-{idx}-p{p}", agent=m))
    # tasks.extend(refinement_tasks)

    # injectors: memory noise + rhythm
    # 🌟 FIX 6: Update task description to reference {{draft_content}}
    #tasks.append(Task(description='Introduce tiny memory inconsistencies across the draft: {{draft_content}}.', expected_output='memory-noise', agent=memory_noise))
    #tasks.append(Task(description='Apply rhythm changes across draft to break sentence length regularity. Draft: {{draft_content}}.', expected_output='rhythm-changed', agent=rhythm))

    # merge & global passes: overthink -> entropy -> final disorder -> publisher
    # 🌟 FIX 6: Update task description to reference {{draft_content}}
    #tasks.append(Task(description='Overthink full-document messy pass on draft: {{draft_content}}.', expected_output='overthought-draft', agent=overthink))
    #tasks.append(Task(description='Entropy model-mix rewrite to break model fingerprints. Draft: {{draft_content}}.', expected_output='entropy-draft', agent=entropy))
    #tasks.append(Task(description='Final readable disorder pass on draft: {{draft_content}}.', expected_output='final-disorder', agent=final_disorder))
    #tasks.append(Task(description='Format article for publish (markdown). Draft: {{draft_content}}.', expected_output='publish-ready', agent=publisher))

    # assemble agents list
    agents = [
        researcher, writer, editor,
        *micro_agents,
        #memory_noise, rhythm,
        #overthink,
        #final_disorder
    ]
    # ---------------- Run crew ----------------


    crew = Crew(agents=agents, tasks=tasks, verbose=True, process="sequential", tracing=True)
    # 🌟 FIX 7: Pass the topic to the progress function so it can be used in kickoff
    result, task_description = run_safe_pipeline_with_progress(crew, tasks, topic=topic)
    return result, task_description

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
