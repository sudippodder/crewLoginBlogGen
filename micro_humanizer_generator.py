"""
Micro Humanizer Role Generator (Complete Script)
- Streamlit UI: input URL OR paste text OR upload local file
- Content extraction (newspaper3k + BeautifulSoup fallback)
- NLP analysis (spaCy + TextBlob + textstat)
- LLM-based JSON role generator (OpenAI ChatCompletion)
- Fallback template JSON generator if OPENAI_API_KEY is not set
- Saves generated role JSON to local file and displays formatted output

Drop into a file and run:
    streamlit run micro_humanizer_generator.py
"""

import os
import json
import re
import time
from typing import Dict, Any, Optional
from openai import OpenAI

import streamlit as st
from dotenv import load_dotenv
# Content extraction
from newspaper import Article
from bs4 import BeautifulSoup
import requests

# NLP
try:
    import spacy
except Exception:
    spacy = None  # spaCy missing; fall back to lighter processing
# later, guard usage:
if spacy:
    nlp = spacy.load("en_core_web_sm")
else:
    # fallback processing or skip spaCy-specific behavior
    nlp = None
from textblob import TextBlob
import textstat

# LLM
import openai
import common
load_dotenv()
# Setup ----
st.set_page_config(page_title="Micro Humanizer Role Generator", layout="wide")
#nlp = spacy.load("en_core_web_sm")

DATABASE_FILE = os.getenv("DATABASE_FILE")
# Developer-provided uploaded file path from earlier session (included as example)
SAMPLE_LOCAL_PATH = '/mnt/data/A_flowchart_titled_"CrewAI_Multi-Agent_System"_ill.png'
openai_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY")
#st.markdown(f"---{openai_key}")
# Utility functions ----
def clean_whitespace(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()

def fetch_article_text(url: str, timeout: int = 10) -> str:
    """Try newspaper3k first; fallback to requests + BeautifulSoup."""
    try:
        art = Article(url)
        art.download()
        art.parse()
        txt = art.text
        if txt and len(txt) > 50:
            return clean_whitespace(txt)
    except Exception:
        pass

    # Fallback
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent":"Mozilla/5.0"})
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        # remove scripts/styles
        for s in soup(["script","style","noscript"]):
            s.extract()
        # pick article tag if present
        article = soup.find("article")
        body_text = article.get_text(separator=" ") if article else soup.get_text(separator=" ")
        return clean_whitespace(body_text)
    except Exception as e:
        raise RuntimeError(f"Failed to fetch URL: {e}")

def load_local_text_file(path: str) -> str:
    """Load text/markdown file if available; otherwise error."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Local file not found: {path}")
    # If binary (image), we return empty to indicate not text
    ext = os.path.splitext(path)[1].lower()
    if ext in (".txt", ".md", ".markdown"):
        with open(path, "r", encoding="utf-8") as f:
            return clean_whitespace(f.read())
    # For other filetypes (image, pdf) we return empty; app will handle preview
    return ""

# Text analysis ----
def analyze_text_features(text: str) -> Dict[str, Any]:
    doc = nlp(text[:20000])  # limit for speed
    sentences = list(doc.sents)
    sent_texts = [s.text.strip() for s in sentences if s.text.strip()]
    words = [token.text for token in doc if token.is_alpha]
    avg_sentence_len = sum(len(s.split()) for s in sent_texts) / max(1, len(sent_texts))
    sentence_var = (sum((len(s.split()) - avg_sentence_len)**2 for s in sent_texts) / max(1, len(sent_texts)))**0.5
    lexical_diversity = len(set(words))/max(1, len(words))
    polarity = TextBlob(text).sentiment.polarity
    subjectivity = TextBlob(text).sentiment.subjectivity
    flesch = textstat.flesch_reading_ease(text) if len(text.split())>100 else None
    common_transitions = []
    # small heuristic: find frequent transition phrases
    transitions = ["however","therefore","meanwhile","in reality","that said","on the other hand","but then"]
    lowered = text.lower()
    for t in transitions:
        if lowered.count(t) > 0:
            common_transitions.append(t)
    # simple top keywords (by frequency)
    token_freq = {}
    for w in words:
        token_freq[w.lower()] = token_freq.get(w.lower(), 0) + 1
    top_keywords = sorted(token_freq.items(), key=lambda x: x[1], reverse=True)[:20]
    return {
        "word_count": len(words),
        "sentence_count": len(sent_texts),
        "avg_sentence_length": round(avg_sentence_len, 2),
        "sentence_length_stddev": round(sentence_var, 2),
        "lexical_diversity": round(lexical_diversity, 3),
        "polarity": round(polarity, 3),
        "subjectivity": round(subjectivity, 3),
        "flesch_reading_ease": round(flesch,2) if flesch is not None else None,
        "common_transitions": common_transitions,
        "top_keywords": [k for k,v in top_keywords],
    }

# Micro humanizer template fallback (non-LLM) ----
def build_role_template(text_stats: Dict[str, Any], topic: Optional[str]=None) -> Dict[str, Any]:
    tone_guess = "neutral"
    pol = text_stats.get("polarity", 0)
    subj = text_stats.get("subjectivity", 0)
    if pol > 0.15:
        tone_guess = "positive / upbeat"
    elif pol < -0.15:
        tone_guess = "negative / cautionary"
    if subj > 0.5:
        tone_guess += ", subjective"
    else:
        tone_guess += ", objective"

    style = "formal" if (text_stats.get("flesch_reading_ease") and text_stats["flesch_reading_ease"] < 50) else "conversational"
    avg_len = text_stats.get("avg_sentence_length", 14)
    sentence_pattern = "short/varied" if avg_len < 14 else "medium/long sentences"
    role = {
        "role": "Micro Humanizer",
        "topic_hint": topic or "unspecified",
        "goal": f"Transform AI-structured text into natural human-like prose matching the source tone ({tone_guess}).",
        "backstory": f"Derived from the author's writing fingerprint: {style} style, {sentence_pattern}, common transitions: {', '.join(text_stats.get('common_transitions', []) or ['none'])}.",
        "tasks": [
            "Preserve the author's voice and emotional pacing.",
            "Inject small human-like imperfections: pauses, hesitations, micro-digressions.",
            "Vary sentence lengths and punctuation distribution to match source variability.",
            "Avoid overwriting factual content; do not introduce hallucinations.",
        ],
        "tone": tone_guess,
        "style": style,
        "patterns": {
            "avg_sentence_length": text_stats.get("avg_sentence_length"),
            "sentence_length_stddev": text_stats.get("sentence_length_stddev"),
            "lexical_diversity": text_stats.get("lexical_diversity"),
            "common_transitions": text_stats.get("common_transitions"),
        },
        "micro_agent_suggestions": [
            "ToneMatcher",
            "SentenceVariabilityAdjuster",
            "FlowEnhancer",
            "HumanErrorInjector"
        ]
    }
    return role


def process_content(text, url=""):
    source_type = "url" if url else "content"
    source_value = url if url else text[:500]  # small preview snippet

    print("⏳ Generating micro-humanizer roles...")
    result_json = extract_micro_humanizer(text)

    print("💾 Saving into SQLite DB...")
    save_to_db(source_type, source_value, result_json)

    print("✅ Stored Successfully!")
    print(result_json)
# =====================================================
# MAIN PROCESS (URL or Raw Content)
# =====================================================

# LLM-based JSON generation ----
def generate_role_with_llm(text: str, stats: Dict[str,Any], topic: Optional[str]=None) -> Dict[str,Any]:
    """
    Use OpenAI ChatCompletion to produce a JSON with fields:
    role, goal, backstory, tasks, tone, style, patterns, micro_agent_list
    """
    openai_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY")
    #st.markdown(f"---{openai_key}")
    if not openai_key:
        # fallback
        return {"warning": "OPENAI_API_KEY not set; returned template fallback", **build_role_template(stats, topic)}

    openai.api_key = openai_key

    system = (
        "You are an expert 'micro humanizer' role generator. "
        "Given blog text and extracted statistics, produce a JSON object (no extra text) "
        "with fields: role, goal, backstory, tasks (array), tone, style, patterns (dict), micro_agent_list (array)."
        "Keep values concise and practical for programmatic ingestion."
    )
    prompt = f"""
    Blog text (first 4000 chars):
    {text[:4000]}

    Extracted stats:
    {json.dumps(stats, indent=2)}

    Produce a JSON object only (no surrounding prose) with:
    - role (short string)
    - goal (one-sentence goal)
    - backstory (short, 1-2 lines)
    - tasks (array of 4-8 short task descriptions)
    - tone (few words)
    - style (few words)
    - patterns (dict with avg_sentence_length, sentence_length_stddev, lexical_diversity, common_transitions, top_keywords)
    - micro_agent_list (array of suggested micro-agent role names)

    The JSON must be parseable.
    """
    try:

        client = OpenAI()

        # try to find JSON inside response
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL","gpt-4o-mini"),
            messages=[
                {"role":"system", "content": system},
                {"role":"user", "content": prompt}
            ],
            temperature=0.9,
            max_tokens=700,
        )
        content = resp.choices[0].message.content
        # try to find JSON inside response
        # naive extraction: find first "{" and last "}"
        first = content.find("{")
        last = content.rfind("}")
        if first != -1 and last != -1 and last > first:
            json_text = content[first:last+1]
            parsed = json.loads(json_text)
            return parsed
        # otherwise attempt to parse whole content
        return json.loads(content)
    except Exception as e:
        # return fallback with error note
        fb = build_role_template(stats, topic)
        fb["_error"] = f"LLM call failed: {e}"
        return fb

# Streamlit UI ----
def default_view():
    st.title("Micro Humanizer Role Generator ")
    col1, col2 = st.columns([2,1])
    st.session_state['page'] = "micro_humanizer_generator"
    with col1:
        st.markdown("### Input")
        #, "Upload local text file", "Use sample local path"
        source_type = st.selectbox("Input type", ["URL", "Paste content"])
        url = ""
        uploaded_text = ""
        local_path = ""
        if source_type == "URL":
            url = st.text_input("Blog URL", "")
        elif source_type == "Paste content":
            uploaded_text = st.text_area("Paste blog text (or part of it)", height=300)
        elif source_type == "Upload local text file":
            uploaded_file = st.file_uploader("Choose a local .txt/.md file", type=["txt","md","markdown"])
            if uploaded_file:
                try:
                    uploaded_text = uploaded_file.read().decode("utf-8")
                except Exception:
                    uploaded_text = uploaded_file.getvalue().decode("utf-8","ignore")
        else:
            local_path = st.text_input("Local path (sample provided)", SAMPLE_LOCAL_PATH)

        st.markdown("---")
        st.text_input("Topic hint (optional)", key="topic_hint")
        coll1, coll2 = st.columns(2)
        #st.text_input("Optional: OpenAI model to use (env override)", value=os.getenv("OPENAI_MODEL","gpt-4o-mini"), key="model_override")
        with coll1:
            generate_btn = st.button("Generate Micro Humanizer Role")
        with coll2:
            if st.button("Back"):
                common.navigate_to("clear")
                st.session_state['page'] = "tone"
                st.rerun()

    with col2:
        st.markdown("### Settings & Info")
        st.markdown("- Uses `newspaper3k` + `BeautifulSoup` to extract text from URLs.")
        st.markdown("- Uses spaCy + TextBlob + textstat to compute features.")
        st.markdown("- Uses OpenAI ChatCompletion (if OPENAI_API_KEY is set) or fallback template.")
        # st.markdown("### Example local path (from upload):")
        # st.code(SAMPLE_LOCAL_PATH)

    # Generation flow ----
    role_json = st.session_state.get('role_json')
    if generate_btn or role_json:
        st.markdown("### Running analysis...")
        raw_text = ""
        try:
            if source_type == "URL":
                if not url:
                    st.error("Please enter a URL.")
                    st.stop()
                raw_text = fetch_article_text(url)
            elif source_type == "Paste content":
                if not uploaded_text or len(uploaded_text.strip()) < 30:
                    st.error("Please paste at least some text.")
                    st.stop()
                raw_text = uploaded_text
            elif source_type == "Upload local text file":
                if uploaded_file is None:
                    st.error("Please upload a local .txt or .md file.")
                    st.stop()
                raw_text = uploaded_text
            else:
                if not local_path:
                    st.error("Please provide a local path.")
                    st.stop()
                try:
                    raw_text = load_local_text_file(local_path)
                    if not raw_text:
                        st.warning("Local path is not a text file or file is empty. If it's an image/PDF the app will show preview only.")
                except FileNotFoundError as e:
                    st.error(str(e))
                    st.stop()
        except Exception as e:
            st.error(f"Failed to load content: {e}")
            st.stop()

        # st.markdown("#### Extracted Preview (first 1000 chars)")
        # st.code((raw_text[:1000] + "...") if len(raw_text) > 1000 else raw_text)

        # Analyze
        with st.spinner("Analyzing text features..."):
            stats = analyze_text_features(raw_text)
        #st.success("Analysis complete")
        #st.json(stats)

        # Ask LLM to generate micro-humanizer role JSON
        with st.spinner("Generating Micro Humanizer Role via LLM / fallback..."):
            topic_hint = st.session_state.get("topic_hint") or None
            os.environ["OPENAI_MODEL"] = st.session_state.get("model_override") or os.getenv("OPENAI_MODEL","gpt-4o-mini")
            if not role_json:
                role_json = generate_role_with_llm(raw_text, stats, topic_hint)
                st.session_state['role_json'] = role_json
        # st.markdown("### Generated Micro Humanizer Role (JSON)")
        # st.json(role_json)

        # Save JSON to file
        safe_topic = (topic_hint or "topic").replace(" ", "_")[:40]
        ts = int(time.time())
        out_path = f"micro_humanizer_{safe_topic}_{ts}.json"
        # try:
        #     with open(out_path, "w", encoding="utf-8") as f:
        #         json.dump(role_json, f, indent=2)
        #     st.success(f"Saved role JSON to `{out_path}`")
        # except Exception as e:
        #     st.warning(f"Could not save JSON to disk: {e}")

        # Provide suggested micro-agent definitions in YAML-ish format for quick copy
        st.markdown("### Suggested micro-agent list (quick starter)")
        suggested_agents = role_json.get("micro_agent_list") if isinstance(role_json, dict) else None
        if not suggested_agents:
            suggested_agents = ["ToneMatcher","SentenceVariabilityAdjuster","FlowEnhancer","HumanErrorInjector"]
        for a in suggested_agents:
            st.write(f"- **{a}** — role: {a}; goal: implement the micro-behavior described in role JSON; backstory: derived from blog fingerprint.")

        st.markdown("---")
        st.markdown("Done. Use this output to instantiate your micro-agents dynamically in your CrewAI pipeline.")
        # save_btn = st.button("Save")
        if st.button("Save To SQLite DB"):
            #st.markdown(f"""### Saving to local SQLite DB...{source_type} role_json > {raw_text}""")
            #st.stop()
            if source_type == "URL":
                source_type = 'URL : ' + url
            try:
                common.save_to_db(source_type, raw_text, role_json)
                st.success("✅ Stored Successfully!")
                time.sleep(4)
                st.rerun()
            except Exception as e:
                st.error(f"Failed to store in DB: {e}")
                time.sleep(4)
                st.rerun()
