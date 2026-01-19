import os
import time
import streamlit as st
import json
import sqlite3
import casestudy
from dotenv import load_dotenv
load_dotenv()

DATABASE_FILE = os.getenv("DATABASE_FILE")

c = sqlite3.connect(DATABASE_FILE)

def pipe_list(text):
    return [i.strip() for i in text.split("|") if i.strip()]

def get_section(data, idx):
    try:
        return "|".join(data["content_structure"][idx]["fields"])
    except:
        return ""

@st.cache_data
def load_template():
    #st.markdown("Loading Article template...--ai_blog_template.json")
    with open("ai_blog_template.json", "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    user = st.session_state['user_info']
    user_id = user['id']
    params = st.session_state['params'] if 'params' in st.session_state else {}
    subpage = params.get("subpage", "") if "subpage" in params else ""
    template_type_id = params.get("template_id", "") if "template_id" in params else ""
    template_frm_id = params.get("template_frm_id", "") if "template_frm_id" in params else ""
    #st.json(params)
    # st.markdown(f"---{template_type_id}")
    # st.markdown(f"---{template_frm_id}")
    template_id = template_frm_id
    c = sqlite3.connect(DATABASE_FILE)
    conn = c.cursor()
    existing = {}
    if template_id:
        row = conn.execute(
            "SELECT id, template_title, version, data_json FROM templates_form WHERE id=?",
            (template_id,)
        ).fetchone()
        if row:
            existing = json.loads(row[3])
    st.title("🧩 Blog Form")
    if st.button("⬅ Back to List"):
        st.session_state["params"]["current_page"] = "template_type"
        st.session_state["params"]["page"] = "template type"
        st.session_state["params"]["subpage"] = "ai_blog_template"
        st.rerun()
    with st.form("template_form"):
        #st.markdown(f"### Edit Case Study Template -- {template_id} -- {existing}")
        if template_id:
            template = existing
        else:
            template = load_template()

        edited_template = {}
        template_title = st.text_input(
            "Template Title",
            existing.get("template_title", row[1] if template_id else "")
        )



        version = st.text_input(
            "Version",
            existing.get("version", row[2] if template_id else "v1.0")
        )

        #st.json(template)
        for section_name, cfg in template.items():
            with st.expander(section_name.upper(), expanded=False):

                st.subheader("🎯 Goal")
                goaltitle = section_name + ' goal'
                goaltitle = goaltitle.title()
                goal = st.text_area(
                    f"{goaltitle}",
                    value=cfg.get("goal", ""),
                    height=80
                )

                st.subheader("📐 Structure")
                structuretitle = section_name + ' structure'
                structuretitle = structuretitle.title()
                structure = st.text_area(
                    f"{structuretitle}",
                    value="\n".join(cfg.get("structure", [])),
                    height=300,
                    help="One item per line"
                ).splitlines()

                st.subheader("✍️ Writing Rules")
                writing_rules = {}
                for rule_key, rule_val in cfg.get("writing_rules", {}).items():
                    if isinstance(rule_val, list):
                        structurewriterule = section_name + ' write ' + rule_key
                        structurewriterule = structurewriterule.title()
                        writing_rules[rule_key] = st.text_area(
                            f"{structurewriterule}",
                            value="\n".join(rule_val),
                            height=300,
                            help="One item per line"
                        ).splitlines()
                    else:
                        structurewriterule = section_name + ' write ' + rule_key
                        structurewriterule = structurewriterule.title()
                        writing_rules[rule_key] = st.text_area(
                            f"{structurewriterule}",
                            value="\n".join(rule_val),
                            height=300,
                            help="One item per line"
                        ).splitlines()

                st.subheader("👥 Agents (CrewAI Compatible)")
                agents = {}
                for agent_type, agent_cfg in cfg.get("agents", {}).items():
                    st.markdown(f"**{agent_type.title()} Agent**")
                    structureagentrole = section_name + ' '+ agent_type + ' role'
                    structureagentrole = structureagentrole.title()

                    structureagentgoal = section_name + ' '+ agent_type + ' Goal'
                    structureagentgoal = structureagentgoal.title()

                    structureagentbackstory = section_name + ' '+ agent_type + ' Backstory'
                    structureagentbackstory = structureagentbackstory.title()

                    structureagentfocus = section_name + ' '+ agent_type + ' Focus'
                    structureagentfocus = structureagentfocus.title()

                    structureagentinstruction = section_name + ' '+ agent_type + ' Instruction'
                    structureagentinstruction = structureagentinstruction.title()

                    agents[agent_type] = {
                        "role": st.text_input(
                            f"{structureagentrole}",
                            value=agent_cfg.get("role", "")
                        ),
                        "goal": st.text_area(
                            f"{structureagentgoal}",
                            value=agent_cfg.get("goal", ""),
                            height=60
                        ),
                        "backstory": st.text_area(
                            f"{structureagentbackstory}",
                            value=agent_cfg.get("backstory", ""),
                            height=80
                        ),
                        "focus": st.text_area(
                            f"{structureagentfocus}",
                            value=agent_cfg.get("focus", ""),
                            height=80
                        ),
                        "instruction": st.text_area(
                            f"{structureagentinstruction}",
                            value=agent_cfg.get("instruction", ""),
                            height=80
                        )
                    }

                st.subheader("🎨 Tone & Limits")
                sectionnametone = section_name + ' tone'
                sectionnametone = sectionnametone.title()
                tone = st.text_input(
                    f"{sectionnametone}",
                    value=cfg.get("tone", "")
                )
                sectionnamewordlimit = section_name + ' word limit'
                sectionnamewordlimit = sectionnamewordlimit.title()
                word_limit = st.number_input(
                    f"{sectionnamewordlimit}",
                    value=int(cfg.get("word_limit", 0)),
                    step=10
                )

                # Build section JSON
                edited_template[section_name] = {
                    "goal": goal,
                    "structure": [s for s in structure if s.strip()],
                    "writing_rules": writing_rules,
                    "agents": agents,
                    "tone": tone,
                    "word_limit": word_limit
                }

        

        submitted = st.form_submit_button("💾 Save Template")

        #st.json(edited_template)

    if submitted:
        if not template_title:
            st.warning("Please enter a template title.")
            st.stop()
        if not version:
            st.warning("Please enter a version.")
            st.stop()
       
        output = edited_template
        use_case = ""
        #st.json(edited_template)
        if template_id:
            conn.execute("""
                UPDATE templates_form
                SET template_title=?, use_case=?, version=?, data_json=?
                WHERE id=?
            """, (
                template_title,
                use_case,
                version,
                json.dumps(output, indent=2),
                template_id
            ))
            st.success("Template updated")
        else:
            conn.execute("""
                INSERT INTO templates_form (template_type,template_title, use_case, version, data_json, user_id)
                VALUES (?,?,?,?,?,?)
            """, (
                template_type_id,
                template_title,
                use_case,
                version,
                json.dumps(output, indent=2),
                user_id
            ))
            st.success("Template created")

        c.commit()
        #st.session_state.page = "list"
        st.session_state["params"]["current_page"] = "template_type"
        st.session_state["params"]["page"] = "template type"
        st.session_state["params"]["subpage"] = "ai_blog_template"
        time.sleep(2)
        st.rerun()
