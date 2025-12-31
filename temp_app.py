from urllib import response
import streamlit as st
import sqlite3
import os
from datetime import datetime
import json
#import openai  # or your preferred LLM
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()
# ----------------------------
# DATABASE INITIALIZATION
# ----------------------------
openai_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY")
DATABASE_FILE = os.getenv("DATABASE_FILE")
conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    template_title TEXT,
    audience TEXT,
    tone_style TEXT,
    content_structure TEXT,
    notes_for_editors TEXT,
    expected_length TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS contents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    topic TEXT,
    template_id INTEGER,
    generated_content TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
""")

conn.commit()

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

# ----------------------------
# LLM GENERATION
# ----------------------------
def generate_content(topic, template_json):
    #openai.api_key = openai_key
    client = OpenAI()
    prompt = f"""
Generate detailed content on the topic: "{topic}"

Template:
Audience: {template_json['audience']}
Tone Style: {template_json['tone_style']}
Content Structure: {template_json['content_structure']}
Expected Length: {template_json['expected_length']}
Notes for Editors: {template_json['notes_for_editors']}

Format your response as well-structured headings.
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    # response = openai.ChatCompletion.create(
    #     model="gpt-4o-mini",
    #     messages=[{"role": "user", "content": prompt}]
    # )

    #return response["choices"][0]["message"]["content"]
    return response.choices[0].message.content

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
    conn = sqlite3.connect(DATABASE_FILE, check_same_thread=False)
    cursor = conn.cursor()
    # if st.button("Save Content"):
    #     topic = "test topic"
    #     template_id = 1
    #     generated = """
    #         {
    #         "banner": "Mobility startup launched Uber-like app on schedule, reducing costs 40% using VE\u2019s remote team",
    #         "metadata": "Mobile app development for mobility industry, including Android, iOS, backend, and quality assurance services.",
    #         "context overview": "The client, a North American mobility startup, operated in a competitive and regulated ride-hailing market. Rapid deployment was critical to comply with transportation and data laws while effectively serving riders, drivers, and admins. Delays risked lost market share and investor trust.",
    #         "project": "The client, a North American ride-hailing startup, required the simultaneous development of integrated rider, driver, and admin applications across Android, iOS, backend, and QA platforms. Their goal was to launch a scalable, multi-role Uber-like platform within six months to secure market entry and investor confidence. Facing limited in-house engineering capacity and stringent regulatory requirements, the project demanded a coordinated approach to deliver comprehensive functionality while ensuring compliance and scalability for the North American market.",
    #         "challenge": "The project faced significant constraints, including limited in-house engineering capacity to develop rider, driver, and admin apps across Android, iOS, and backend platforms within a six-month timeline. Core features had to be built from scratch due to the absence of existing APIs or documentation. Compliance with regional regulations restricted third-party integrations. Critical deliverables such as real-time tracking, secure in-app payments, and driver onboarding demanded rapid development. Remote team coordination and a mandate to reduce costs by nearly 40% versus local hiring added complexity, all while maintaining app stability and feature completeness.",
    #         "solution": "Virtual Employee (VE) provided the mobility startup with a dedicated remote team of ten specialized developers to address limited in-house engineering capacity and meet an aggressive six-month launch deadline. Leveraging VE enabled quick onboarding of niche expertise across Android, iOS, backend, QA, and product coordination, bypassing delays typical of local recruitment.\n\nThis approach supported the parallel development of rider, driver, and admin applications, critical to adhering to the strict timeline. As project complexity increased, VE\u2019s flexible staffing model allowed rapid adjustment of team composition\u2014scaling backend or QA roles as required\u2014maintaining development velocity and quality without jeopardizing deadlines.\n\nCompared to assembling an internal team, this remote, dedicated model offered faster delivery and greater viability by eliminating lengthy recruitment and onboarding periods. It also reduced development costs by approximately 40%, an important factor given budget limitations. Initially providing support-level capacity, VE\u2019s team quickly assumed deep technical ownership, managing vital components such as real-time tracking and in-app payments with high reliability.\n\nThis model enabled the startup to launch a fully functional, stable ride-hailing platform within 5.5 months, illustrating how rapid access to specialized talent, adaptable team structure, accelerated timelines, and progressive ownership effectively overcame the startup\u2019s primary challenges.",
    #         "technical build": "**Technical Build**\n\nThe ride-hailing system was architected as a multi-component platform consisting of three interconnected applications: a rider app, a driver app, and an admin portal. Native development frameworks\u2014Kotlin for Android and Swift for iOS\u2014were employed to optimize performance and ensure platform-specific user experiences. The admin interface was implemented as a responsive web portal using React, enabling operations staff to manage drivers, trips, and system configurations in real time.\n\nThe backend utilized a scalable microservices architecture developed in Node.js and deployed on a cloud platform to support elasticity under variable demand. Core services included ride matching, GPS-based location tracking, fare calculation, driver onboarding, and in-app payment processing. Communication between client applications and backend services was handled via RESTful APIs secured with OAuth 2.0 authentication, providing secure and low-latency data exchange.\n\nReal-time location updates and trip status notifications were managed through an event-driven messaging system based on Apache Kafka. This decoupled data ingestion from processing, facilitating efficient management of high-throughput GPS streams and timely updates across rider, driver, and admin applications. Backend services calculated routes and estimated arrival times in real time by integrating mapping APIs and geo-fencing logic to meet precision and responsiveness requirements.\n\nDue to regional regulatory requirements, the in-app payment system integrated with a custom-built PCI DSS-compliant payment gateway applying encryption and tokenization. This bespoke solution replaced standard third-party processors, ensuring protection of sensitive financial data while maintaining seamless transaction flows within the ecosystem.\n\nThe admin portal featured user role management, driver verification modules, trip auditing tools, and dashboards displaying operational metrics sourced directly from backend APIs. This interface provided near-real-time insights into system performance and allowed configuration changes without service interruption.\n\nTo manage parallel development across iOS, Android, backend, and quality assurance teams, an API-first strategy was adopted. This facilitated independent development tracks based on agreed interface contracts, reducing integration dependencies and supporting simultaneous progress. Continuous integration and continuous deployment (CI/CD) pipelines automated testing and deployment workflows, enabling early detection of integration issues and maintaining consistent build quality.\n\nThe development team structure included three Android developers focusing on native UI responsiveness and real-time location features; three iOS developers responsible for feature parity and adherence to platform conventions; two backend engineers handling microservices, APIs, and data security; one QA engineer overseeing automated and manual testing; and one product coordinator managing sprint planning and cross-team coordination. This allocation optimized resources to meet a six-month delivery timeline.\n\nAutomated testing encompassed unit tests, UI functional tests, and API contract validations integrated within the CI pipeline. Crash reporting and performance monitoring tools were incorporated from initial builds to monitor stability and responsiveness, with proactive triaging to maintain system robustness. Security measures included penetration testing and audits concentrating on payment processes and protection of personally identifiable information across the technology stack.\n\nThe backend infrastructure was hosted on a cloud service offering autoscaling, supported by API gateways and load balancers to distribute incoming mobile requests evenly and ensure high availability. These infrastructure choices guaranteed backend responsiveness and reliability under varying operational loads.\n\nThis build strategy addressed the challenges of concurrent development of rider, driver, and admin applications, management of complex real-time data flows, enforcement of stringent security and regulatory compliance, and maintenance of application stability. By structuring the system with modular, independent services and leveraging native platform development, the project achieved efficient parallel workflows and realized a maintainable, extensible codebase suited for future enhancements.",
    #         "result": "The MVP launched in 5.5 months, beating the 6-month deadline, with 99.8% crash-free sessions. Core features\u2014tracking, payments, onboarding\u2014were delivered on schedule, reducing development costs by ~40% through parallel multi-platform development.",
    #         "testimonial": "The MVP launched in 5.5 months, beating our 6-month target, and achieved 99.8% crash-free sessions. Key features like tracking, payments, and onboarding were delivered on time, enabling us to reduce development costs by around 40% thanks to parallel multi-platform development."
    #         }
    #     """
    #     st.session_state['bit'] = 1
    #     cursor.execute("""
    #         INSERT INTO contents (user_id, topic, template_id, generated_content)
    #         VALUES (?, ?, ?, ?)
    #     """, (user_id, topic, template_id, generated))
    #     conn.commit()
    #     st.success("Content saved!")
    #     st.session_state["page"] = "content list"

    #     st.rerun()

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


def content_list(user_id):
    st.header("Generated Content List")

    cursor.execute("""
        SELECT id, topic, generated_content
        FROM contents
        WHERE contents.user_id=?
    """, (user_id,))

    rows = cursor.fetchall()
    if rows:
        for row in rows:

            id, topic, generated_content = row
            st.write(f"### {topic} ")

            #st.json(generated_content)

            col1, col2 = st.columns(2)
            with col1:
                if st.button("View", key=f"view_{id}"):
                    if generated_content:
                        # clean_template = sanitize_for_json(generated_content)
                        # json_string = json.dumps(clean_template, ensure_ascii=False)
                        # generated_content = json.loads(json_string)
                        try:
                            generated_content = json.loads(generated_content)
                        except json.JSONDecodeError as e:
                            st.error("Stored template is corrupted.")
                            print("JSON ERROR:", e)
                            return
                        for section, content in generated_content.items():
                            with st.expander(section.title(), expanded=True):
                                st.write(content)
                        #st.markdown(template_dict)
                    else:
                        st.info("No generated content available.")
            with col2:
                if st.button(f"Delete"):
                    cursor.execute("DELETE FROM contents WHERE id=?", (id,))
                    conn.commit()
                    st.warning("Deleted successfully")
                    st.rerun()
    else:
        st.info("No content generated yet.")


# ----------------------------
# GENERATE CONTENT PAGE
# ----------------------------
def generate_content_page(user_id):
    st.header("Generate Content")

    topic = st.text_input("Enter Topic")

    cursor.execute("SELECT id, template_title FROM templates WHERE user_id=?", (user_id,))
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

            cursor.execute("SELECT * FROM templates WHERE id=?", (template_id,))
            t = cursor.fetchone()

            template_json = {
                "template_title": t[2],
                "audience": t[3].split("|"),
                "tone_style": t[4].split("|"),
                "content_structure": t[5].split("|"),
                "notes_for_editors": t[6].split("|"),
                "expected_length": t[7].split("|"),
            }

            st.subheader("Template (JSON View)")
            st.markdown(json_to_html(template_json), unsafe_allow_html=True)

            generated = generate_content(topic, template_json)
            st.subheader("Generated Content")
            st.markdown(generated)

            st.session_state['bit'] = 2
            if generated and st.button("Save Content"):

                st.session_state['bit'] = 1
                cursor.execute("""
                    INSERT INTO contents (user_id, topic, template_id, generated_content)
                    VALUES (?, ?, ?, ?)
                """, (user_id, topic, template_id, generated))
                conn.commit()
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
