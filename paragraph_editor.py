import streamlit as st
from zerogpt_api import check_ai_content
import textwrap

def split_text_into_paragraphs(text, max_length=500):
    """Split text into paragraphs or ~500-char chunks for display/editing."""
    paragraphs = []
    for paragraph in text.split("\n\n"):
        if len(paragraph.strip()) == 0:
            continue
        if len(paragraph) > max_length:
            # further split long paragraphs
            chunks = textwrap.wrap(paragraph, max_length)
            paragraphs.extend(chunks)
        else:
            paragraphs.append(paragraph)
    return paragraphs


def display_paragraphs_with_detection(content):
    """
    Display content paragraph-by-paragraph with detection highlights and inline edit support.
    Returns the updated merged content after edits.
    """
    paragraphs = split_text_into_paragraphs(content)

    if "paragraph_edits" not in st.session_state:
        st.session_state.paragraph_edits = {}
    if "edit_mode" not in st.session_state:
        st.session_state.edit_mode = {}

    updated_paragraphs = []
    st.subheader("📜 Generated Content Review")

    for i, para in enumerate(paragraphs):
        key = f"para_{i}"
        st.divider()

        # Initialize session states
        st.session_state.edit_mode.setdefault(key, False)
        st.session_state.paragraph_edits.setdefault(key, para)

        if not st.session_state.edit_mode[key]:
            # Detect this paragraph
            with st.spinner(f"Analyzing paragraph {i+1}..."):
                result = check_ai_content(para)
            data = result.get("data", {}) if result else {}
            fake_percentage = data.get("fakePercentage", 0)
            is_human = data.get("isHuman", 0)

            bg_color = "#ffcccc" if is_human == 0 else "#eaffea"
            label = "🧠 AI" if is_human == 0 else "🧍 Human"
            feedback = data.get("feedback", "No feedback.")

            with st.container():
                st.markdown(
                    f"""
                    <div style="background:{bg_color};padding:15px;border-radius:10px;margin-bottom:10px;">
                        <p style="white-space: pre-wrap;">{para}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.write(f"**Result:** {label} | **AI Probability:** {fake_percentage:.2f}%")
                st.caption(feedback)

                col1, col2 = st.columns([0.15, 0.85])
                with col1:
                    if st.button("✏️ Edit", key=f"edit_{key}"):
                        st.session_state.edit_mode[key] = True
                        st.session_state.paragraph_edits[key] = para
                        st.rerun()

        else:
            # Editable mode
            edited_text = st.text_area(
                f"✏️ Edit Paragraph {i+1}",
                value=st.session_state.paragraph_edits[key],
                height=150,
                key=f"textarea_{key}",
            )

            col1, col2 = st.columns([0.2, 0.8])
            with col1:
                if st.button("✅ Update", key=f"update_{key}"):
                    with st.spinner("Rechecking updated paragraph..."):
                        result = check_ai_content(edited_text)
                    data = result.get("data", {})
                    fake_percentage = data.get("fakePercentage", 0)
                    is_human = data.get("isHuman", 0)
                    label = "🧠 AI" if is_human == 0 else "🧍 Human"
                    feedback = data.get("feedback", "No feedback.")
                    bg_color = "#ffcccc" if is_human == 0 else "#eaffea"

                    # Update paragraph and reset edit mode
                    st.session_state.paragraph_edits[key] = edited_text
                    st.session_state.edit_mode[key] = False

                    st.markdown(
                        f"""
                        <div style="background:{bg_color};padding:15px;border-radius:10px;margin-bottom:10px;">
                            <p style="white-space: pre-wrap;">{edited_text}</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    st.write(f"**Result:** {label} | **AI Probability:** {fake_percentage:.2f}%")
                    st.caption(feedback)
                    st.success("✅ Paragraph updated successfully.")
                    st.rerun()

            with col2:
                if st.button("❌ Cancel", key=f"cancel_{key}"):
                    st.session_state.edit_mode[key] = False
                    st.rerun()

        updated_paragraphs.append(st.session_state.paragraph_edits[key])

    st.divider()
    full_text = "\n\n".join(updated_paragraphs)
    return full_text
