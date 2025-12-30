import streamlit as st
import json

# st.set_page_config(page_title="Blog Template Builder", layout="wide")
# st.title("🧠 Dynamic Blog Template Builder (CrewAI Ready)")

# ----------------------------------------
# Load Template
# ----------------------------------------
@st.cache_data
def load_template():
    with open("blog_template_structure.json", "r", encoding="utf-8") as f:
        return json.load(f)



def main():
    template = load_template()

    edited_template = {}

    # ----------------------------------------
    # UI
    # ----------------------------------------
    for section_name, cfg in template.items():
        with st.expander(section_name.upper(), expanded=False):

            st.subheader("🎯 Goal")
            goal = st.text_area(
                f"{section_name}_goal",
                value=cfg.get("goal", ""),
                height=80
            )

            st.subheader("📐 Structure")
            structure = st.text_area(
                f"{section_name}_structure",
                value="\n".join(cfg.get("structure", [])),
                height=100,
                help="One item per line"
            ).splitlines()

            st.subheader("✍️ Writing Rules")
            writing_rules = {}
            for rule_key, rule_val in cfg.get("writing_rules", {}).items():
                if isinstance(rule_val, list):
                    writing_rules[rule_key] = st.text_area(
                        f"{section_name}_wr_{rule_key}",
                        value="\n".join(rule_val),
                        height=80,
                        help="One item per line"
                    ).splitlines()
                else:
                    writing_rules[rule_key] = st.text_input(
                        f"{section_name}_wr_{rule_key}",
                        value=str(rule_val)
                    )

            st.subheader("👥 Agents (CrewAI Compatible)")
            agents = {}
            for agent_type, agent_cfg in cfg.get("agents", {}).items():
                st.markdown(f"**{agent_type.title()} Agent**")
                agents[agent_type] = {
                    "role": st.text_input(
                        f"{section_name}_{agent_type}_role",
                        value=agent_cfg.get("role", "")
                    ),
                    "goal": st.text_area(
                        f"{section_name}_{agent_type}_goal",
                        value=agent_cfg.get("goal", ""),
                        height=60
                    ),
                    "backstory": st.text_area(
                        f"{section_name}_{agent_type}_backstory",
                        value=agent_cfg.get("backstory", ""),
                        height=80
                    )
                }

            st.subheader("🎨 Tone & Limits")
            tone = st.text_input(
                f"{section_name}_tone",
                value=cfg.get("tone", "")
            )
            word_limit = st.number_input(
                f"{section_name}_word_limit",
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

    # ----------------------------------------
    # OUTPUT
    # ----------------------------------------
    st.divider()
    st.subheader("📦 Final JSON Output")

    #st.json(edited_template)

    st.download_button(
        "⬇ Download Template JSON",
        json.dumps(edited_template, indent=2),
        file_name="blog_template_structure_updated.json",
        mime="application/json"
    )
    return template, edited_template
