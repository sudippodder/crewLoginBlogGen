import importlib
import streamlit as st
import sqlite3
import hashlib
import time
import pandas as pd
import json # Added for session persistence
import os   # Added for file path management
import generatecontent
import temp_app
importlib.reload(generatecontent)
import urllib.parse
from dotenv import load_dotenv
import micro_humanizer_generator
import common
import sqlite
from streamlit_cookies_manager import EncryptedCookieManager
import humanize_convert
ENCRYPTION_PASSWORD = "your_strong_secret_key_here"
# Key under which the user data will be stored in the cookie
USER_COOKIE_KEY = "user_session_data"
# Expiry time (in days) for the persistent login
COOKIE_EXPIRY_DAYS = 30
#st.markdown(f"{st.session_state}")

cookies = EncryptedCookieManager(prefix="myapp", password="adminapp123")
if not cookies.ready():
    st.info("Loading cookies...")
    st.stop()

# --- Configuration ---
load_dotenv()

DATABASE_FILE = os.getenv("DATABASE_FILE")
SESSION_FILE = os.getenv("SESSION_FILE") # File to store persistent login data
DEFAULT_USER_ROLE = os.getenv("DEFAULT_USER_ROLE")
# The user with this username will be considered the admin (default password 'adminpass')
ADMIN_USER = os.getenv("ADMIN_USER")

for k, v in {
    "reg_user": "",
    "reg_pass": "",
    "reg_name": "",
    "reg_email": "",
    "reg_message": ""
}.items():
    st.session_state.setdefault(k, v)

query_params = st.query_params

# --- Utility Functions for Hashing ---
def hash_password(password):
    """Hashes a password using SHA256."""
    # Using SHA256 for simplicity as it's a standard library.
    return hashlib.sha256(password.encode()).hexdigest()

def check_password(password, hashed_password):
    """Checks a cleartext password against a stored hash."""
    return hash_password(password) == hashed_password

# --- Database Functions ---

def init_db():
    """Initializes the SQLite database and creates the users and posts tables."""
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    # 1. Create the users table
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT,
            full_name TEXT,
            role TEXT DEFAULT 'user'
        )
    """)
    # 2. Create the posts table (NEW)
    c.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            post_id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS content_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT,
            researcher_goal TEXT,
            researcher_backstory TEXT,
            writer_goal TEXT,
            writer_backstory TEXT,
            editor_goal TEXT,
            editor_backstory TEXT,
            final_output TEXT,
            detection_result TEXT,
            user_id INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS micro_roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_type TEXT,
            source_value TEXT,
            role TEXT,
            tone TEXT,
            style TEXT,
            patterns TEXT,
            generated_json TEXT,
            created_at TEXT,
            is_active INTEGER DEFAULT 1,
            user_id INTEGER DEFAULT 0
        )
    """)

    c.execute("""
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

    c.execute("""
    CREATE TABLE IF NOT EXISTS contents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        topic TEXT,
        template_id INTEGER,
        generated_content TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS tones(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            details TEXT,
            user_id INTEGER DEFAULT 0,
            active INTEGER DEFAULT 1
        )
    """)
    # c.execute("""
    #     ALTER TABLE content_history
    #     ADD COLUMN user_id INTEGER DEFAULT 0
    # """)
    conn.commit()
    conn.close()

def get_user_id_by_username(username):
    """Retrieves the user ID based on the username."""
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def add_user(username, password, email, full_name, role=DEFAULT_USER_ROLE):
    """Adds a new user to the database."""
    hashed_password = hash_password(password)
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password_hash, email, full_name, role) VALUES (?, ?, ?, ?, ?)",
                  (username, hashed_password, email, full_name, role))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        # Username already exists
        return False
    except Exception as e:
        st.error(f"Database error during registration: {e}")
        return False

def verify_credentials(username, password):
    """Verifies user credentials and returns user info (including id) if successful."""
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    # Fetch ID as well, which is needed for post creation
    c.execute("SELECT id, password_hash, email, full_name, role FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()

    if result:
        user_id, password_hash, email, full_name, role = result
        if check_password(password, password_hash):
            return {"id": user_id, "username": username, "email": email, "full_name": full_name, "role": role}
    return None

def get_all_users():
    """Retrieves all users (excluding password hash) for admin page."""
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    c.execute("SELECT id, username, email, full_name, role FROM users")
    users = c.fetchall()
    conn.close()
    return [{"id": row[0], "username": row[1], "email": row[2], "full_name": row[3], "role": row[4]} for row in users]

def add_post(user_id, title, content):
    """Adds a new post associated with a user ID."""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()
        c.execute("INSERT INTO posts (user_id, title, content) VALUES (?, ?, ?)",
                  (user_id, title, content))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error adding post: {e}")
        return False

def get_posts_by_user(user_id):
    """Retrieves all posts created by a specific user."""
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    # Join posts with users to get the username for display
    c.execute("""
        SELECT p.post_id, p.title, p.content, p.created_at, u.username
        FROM posts p
        JOIN users u ON p.user_id = u.id
        WHERE p.user_id = ?
        ORDER BY p.created_at DESC
    """, (user_id,))
    posts = c.fetchall()
    conn.close()
    return [{"post_id": row[0], "title": row[1], "content": row[2], "created_at": row[3], "username": row[4]} for row in posts]


# --- Persistent Session State Functions ---
def get_tones_by_user(user_id):
    """Retrieves all tones created by a specific user."""
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    # Join tones with users to get the username for display

    c.execute("""
        SELECT p.*
        FROM micro_roles p
        JOIN users u ON p.user_id = u.id
        WHERE p.user_id = ?
        ORDER BY p.created_at DESC
    """, (user_id,))
    posts = c.fetchall()
    conn.close()
    return  posts


def save_session_state(user_info):
    """
    Saves user information to an encrypted cookie for persistent login.
    This replaces your file-based save logic.
    """
    try:
        # Convert the dictionary to a JSON string before saving it to the cookie
        user_info_json = json.dumps(user_info)

        # Set the value in the cookie manager
        cookies[USER_COOKIE_KEY] = user_info_json

        # Save the cookie to the user's browser with an expiration date
        # Note: The component handles setting the expiry based on the key persistence
        cookies.save(expires_in=time.time() + (COOKIE_EXPIRY_DAYS * 24 * 60 * 60))

        st.toast("✅ User session saved successfully to cookie!", icon='🍪')

    except Exception as e:
        # st.error is better than print in Streamlit for user feedback
        st.error(f"Error saving session state to cookie: {e}")


#     """Stores user info in Streamlit's per-user session state."""
#     # Use st.session_state to store data unique to the current user's session
# #     {"id": 2,
# # "username": "sudip",
# # "email": "sudip@gmail.com",
# # "full_name": "sudip",
# # "role": "user"}
#     #st.session_state['logged_in'] = True
#     st.session_state['id'] = user_info.get('id')
#     st.session_state['username'] = user_info.get('username')
#     st.session_state['email'] = user_info.get('email')
#     st.session_state['full_name'] = user_info.get('full_name')
#     st.session_state['role'] = user_info.get('role')
# def save_session_state(user_info):
#     """Saves user information to a file for persistent login."""
#     try:
#         # User info is now a dictionary, including 'id'
#         with open(SESSION_FILE, 'w') as f:
#             json.dump(user_info, f)
#     except Exception as e:
#         print(f"Error saving session state: {e}")
# def load_session_state():
#     """Retrieves user info from the current session state."""
#     if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
#         return {}
#     return {
#         'id': st.session_state.get('id', False),
#         'username': st.session_state.get('username', None),
#         'email': st.session_state.get('email', None),
#         'full_name': st.session_state.get('full_name', None),
#         'role': st.session_state.get('role', None),
#     }

def load_session_state():
    """Loads user information from the cookie."""
    try:
        user_info_json = cookies.get(USER_COOKIE_KEY)

        # Check if cookie exists and is not empty
        if user_info_json and user_info_json.strip():
            try:
                return json.loads(user_info_json)
            except json.JSONDecodeError:
                st.error("Error decoding user cookie data.")
                return None
    except:
        pass

    return None



def clear_session_state():
    """Clears the persistent session file."""
    try:
        # Check if cookie exists and delete it
        if USER_COOKIE_KEY in cookies:
            del cookies[USER_COOKIE_KEY]
            cookies.save()
    except Exception as e:
        st.error(f"Error clearing session state from cookie: {e}")

    # Clear all session state keys
    keys_to_delete = list(st.session_state.keys())
    for key in keys_to_delete:
        del st.session_state[key]

# def load_session_state():
#     """Loads user information from a file if it exists."""
#     if os.path.exists(SESSION_FILE):
#         try:
#             with open(SESSION_FILE, 'r') as f:
#                 return json.load(f)
#         except Exception as e:
#             # File might be corrupted or empty
#             print(f"Error loading session state: {e}")
#             os.remove(SESSION_FILE) # Clear corrupted file
#     return None


    #st.rerun()
    # if os.path.exists(SESSION_FILE):
    #     os.remove(SESSION_FILE)

# --- Session State Management and Initialization ---

def initialize_session_state():
    """Initializes necessary session state variables and checks for default admin and persistent session."""

    # 1. Check for persistent login file first
    persistent_info = load_session_state()

    # 2. Initialize Streamlit session state
    if 'logged_in' not in st.session_state:
        # If Streamlit session is fresh, use persistent info if available
        st.session_state['logged_in'] = bool(persistent_info)
    if 'user_info' not in st.session_state:
        st.session_state['user_info'] = persistent_info

    if 'page' not in st.session_state:
        # Default page is login if not logged in, otherwise dashboard
        st.session_state['page'] = 'login' if not st.session_state['logged_in'] else 'dashboard'
    #st.json( st.session_state)
    # 3. Check for demo admin user
    if not verify_credentials(ADMIN_USER, "adminpass"):
        if add_user(ADMIN_USER, "adminpass", "admin@example.com", "System Admin", "admin"):
            st.info(f"Demo admin user '{ADMIN_USER}' created. Password: 'adminpass'.")

# --- Authentication Logic ---

def login_user(username, password):
    """Handles the login process."""
    user_info = verify_credentials(username, password)
    if user_info:
        st.session_state['logged_in'] = True
        st.session_state['user_info'] = user_info
        st.session_state['page'] = 'dashboard'

        # Save state to file for persistence across browser refreshes
        save_session_state(user_info)

        st.success(f"Login successful! Welcome, {user_info['username']}.")
        time.sleep(1) # Wait slightly before rerun for message visibility
        st.rerun()
    else:
        st.error("Invalid username or password.")

def logout_user():
    """Handles the logout process."""
    # Clear the persistent session cookie
    if USER_COOKIE_KEY in cookies:
        cookies[USER_COOKIE_KEY] = ""
        cookies.save()
    # Clear all session state
    keys_to_delete = list(st.session_state.keys())
    for key in keys_to_delete:
        del st.session_state[key]
    # Set logged out state
    st.session_state['logged_in'] = False
    st.session_state['user_info'] = None
    st.session_state['page'] = 'login'
    st.toast("Logged out successfully!", icon="👋")
    time.sleep(0.5)  # Brief delay to show toast
    st.rerun()

# --- Page Rendering Functions ---

def show_login_page():
    """Renders the Login and Registration forms."""
    st.title("🔐 Secure Login Portal")
    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Sign In")
        with st.form("login_form"):
            login_username = st.text_input("Username", key="login_user")
            login_password = st.text_input("Password", type="password", key="login_pass")
            login_button = st.form_submit_button("Log In", type="primary")

            if login_button:
                login_user(login_username, login_password)

    with col2:
        st.subheader("New User Registration")
        with st.form("register_form"):
            reg_username = st.text_input("Choose Username*", key="reg_user")
            reg_password = st.text_input("Set Password*", type="password", key="reg_pass")
            reg_name = st.text_input("Full Name", key="reg_name")
            reg_email = st.text_input("Email", key="reg_email")
            register_button = st.form_submit_button("Register Account", type="secondary")

            if register_button:
                if reg_username and reg_password:
                    if add_user(reg_username, reg_password, reg_email, reg_name):
                        st.success("Registration successful! You can now log in.")
                        # Resetting form fields
                        if 'reg_user' not in st.session_state:
                            st.session_state.reg_user = ""
                        if 'reg_pass' not in st.session_state:
                            st.session_state.reg_pass = ""
                        if 'reg_name' not in st.session_state:
                            st.session_state.reg_name = ""
                        if 'reg_email' not in st.session_state:
                            st.session_state.reg_email = ""
                    else:
                        st.error("Registration failed. Username might already be taken.")
                else:
                    st.error("Username and Password are required.")


def show_dashboard():
    """Renders the main dashboard page."""
    user = st.session_state['user_info']

    st.title(f"🏠 Dashboard")
    st.header(f"Welcome back, {user['full_name'] or user['username']}!", divider='blue')

    st.markdown(f"""
        <div style="padding: 15px; border-radius: 10px; background-color: #e0f7fa; border-left: 5px solid #00bcd4;">
            <p style="font-size: 1.1em; margin: 0;">
                Your access role is: <strong>{user['role'].capitalize()}</strong>.
            </p>
            <p style="font-size: 0.9em; margin-top: 5px;">
                As a {user['role']}, you have access to specific modules in the sidebar.
            </p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Custom dashboard content
    # col1, col2, col3 = st.columns(3)
    # with col1:
    #     st.metric("Total Tasks", "12", "-2 overdue")
    # with col2:
    #     st.metric("Team Members", "4", "New")
    # with col3:
    #     # Use the stored user ID (user['id']) for reference
    #     st.metric("Your User ID", f"{user['id']}", "")

    # st.subheader("Recent Activity")
    # activity_data = {
    #     'Time': ['10:30 AM', '09:15 AM', 'Yesterday'],
    #     'Event': ['Updated project roadmap', 'Created new task: "Fix bug"', 'Logged out'],
    #     'Status': ['Completed', 'In Progress', 'System']
    # }
    # st.table(activity_data)


def show_profile():
    """Renders the user profile page."""
    user = st.session_state['user_info']
    st.title("👤 User Profile")
    #st.header(f"Details for {user['username'].capitalize()}", divider='green')

    st.markdown(f"""
        <div style="border: 1px solid #ddd; padding: 25px; border-radius: 12px; background-color: #f0fff4;">
            <p><strong>Database ID:</strong> <code>{user['id']}</code></p>
            <p><strong>Username:</strong> <code>{user['username']}</code></p>
            <p><strong>Full Name:</strong> {user['full_name'] or 'Not Provided'}</p>
            <p><strong>Email:</strong> {user['email'] or 'Not Provided'}</p>
            <p><strong>Access Role:</strong> <span style="font-weight: bold; color: {'#d9534f' if user['role'] == 'admin' else '#5cb85c'};">{user['role'].capitalize()}</span></p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.info("You can customize this page to allow users to update their profile information.")


def show_post_page():
    """Renders the Post creation and viewing page (NEW)."""
    user = st.session_state['user_info']
    user_id = user['id']
    username = user['username']

    st.title("✍️ My Posts")
    st.header(f"Create and View Your Content ({username})", divider='orange')

    # --- Post Creation Form ---
    with st.expander("➕ Create New Post", expanded=True):
        with st.form("new_post_form", clear_on_submit=True):
            post_title = st.text_input("Post Title (Required)", max_chars=100)
            post_content = st.text_area("Post Content (Required)", height=150)

            submit_button = st.form_submit_button("Publish Post", type="primary")

            if submit_button:
                if post_title and post_content:
                    if add_post(user_id, post_title, post_content):
                        st.success("Post published successfully!")
                        # Rerun to refresh the list of posts below
                        st.rerun()
                    else:
                        st.error("Could not publish post. Please try again.")
                else:
                    st.warning("Both title and content are required to publish a post.")

    st.markdown("---")

    # --- Post Viewing Section ---
    st.subheader("📝 Your Published Posts")

    user_posts = get_posts_by_user(user_id)

    if user_posts:
        for post in user_posts:
            st.markdown(f"""
                <div style="border: 1px solid #ffcc80; padding: 15px; margin-bottom: 15px; border-radius: 8px; background-color: #fff3e0;">
                    <h4 style="margin-top: 0; color: #e65100;">{post['title']}</h4>
                    <p style="font-size: 0.9em; color: #666; font-style: italic;">
                        Posted by {post['username']} on {post['created_at'].split('.')[0]}
                    </p>
                    <p>{post['content']}</p>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("You haven't published any posts yet. Use the form above to create your first one!")

def show_post_content():
    """Renders the Post creation and viewing page (NEW)."""
    user = st.session_state['user_info']
    user_id = user['id']
    username = user['username']


    #st.header(f"Create and View Your Content ({username})", divider='orange')
    left, right = st.columns([8, 2])
    with left:
        st.title("✍️ Generate Content with Tones")
    #left.header(f"View Your Tones ({username})")  # optional text
    with right:
        if st.button("List", type="primary"):
            st.session_state['spage'] = ''
            st.session_state['page'] = 'content'
            st.rerun()
            #common.navigate_to("content")

    if "detection_result" not in st.session_state:
        st.session_state.detection_result = None

    if "last_edit_time" not in st.session_state:
        st.session_state.last_edit_time = {}

    if "edit_cache" not in st.session_state:
        st.session_state.edit_cache = {}


    st.title("🧠 AI Content Agent v1.0.4")

    st.markdown(f"""
    <b>Enter your topic, then define each agent's role and backstory to get targeted, comprehensive output. The more specific you are, the better your content in terms of depth, angle, and completeness.</b>\n"""
    """
    This multi-agent system can be used anywhere content needs to be created, refined, and published regularly. Some examples include: SEO-friendly blogs and articles, generating social media posts, newsletters, campaign content , product descriptions, guides, promotional blogs, newsletters, announcements, reports.
    """, unsafe_allow_html=True)
    st.markdown("---")
    #st.markdown(generatecontent.__file__)
    # --- GENERATE BUTTON ---
    generatecontent.generate_content_page()
    # --- Post Creation Form ---

    st.markdown("---")





def show_post_tone():
    """Renders the Post creation and viewing page (NEW)."""
    user = st.session_state['user_info']
    user_id = user['id']
    username = user['username']

    st.title("✍️ Generate Content with Tones")
    st.header(f"Create and View Your Content ({username})", divider='orange')

    # --- Post Creation Form ---
    with st.expander("➕ Create New Post", expanded=True):
        with st.form("new_post_form", clear_on_submit=True):
            post_title = st.text_input("Post Title (Required)", max_chars=100)
            post_content = st.text_area("Post Content (Required)", height=150)

            submit_button = st.form_submit_button("Publish Post", type="primary")

            if submit_button:
                if post_title and post_content:
                    if add_post(user_id, post_title, post_content):
                        st.success("Post published successfully!")
                        # Rerun to refresh the list of posts below
                        st.rerun()
                    else:
                        st.error("Could not publish post. Please try again.")
                else:
                    st.warning("Both title and content are required to publish a post.")

    st.markdown("---")

    # --- Post Viewing Section ---
    st.subheader("📝 Your Published Posts")

    user_posts = get_posts_by_user(user_id)

    if user_posts:
        for post in user_posts:
            st.markdown(f"""
                <div style="border: 1px solid #ffcc80; padding: 15px; margin-bottom: 15px; border-radius: 8px; background-color: #fff3e0;">
                    <h4 style="margin-top: 0; color: #e65100;">{post['title']}</h4>
                    <p style="font-size: 0.9em; color: #666; font-style: italic;">
                        Posted by {post['username']} on {post['created_at'].split('.')[0]}
                    </p>
                    <p>{post['content']}</p>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Tones are not created yet!")


def show_admin_page():
    """Renders the admin page for user management."""
    user = st.session_state['user_info']

    if user['role'] != 'admin':
        st.error("🛑 ACCESS DENIED: You do not have administrator privileges.")
        st.warning("Only users with the 'admin' role can view this page.")
        return

    st.title("🛠️ Admin Panel")
    st.header("User Management", divider='red')
    st.info("A live list of all registered users in the database.")

    users_data = get_all_users()

    if users_data:
        # Convert list of dicts to a pandas DataFrame for a clean table display
        df = pd.DataFrame(users_data)
        df = df.set_index('id')

        # Display the users table
        st.dataframe(df, use_container_width=True)
    else:
        st.warning("No users found in the database.")

def update_tone_active(tone_id, is_active):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE micro_roles SET is_active = ? WHERE id = ?", (is_active, tone_id))
    conn.commit()
    conn.close()


def show_tone_page():
    """Renders the Post creation and viewing page (NEW)."""
    user = st.session_state['user_info']
    user_id = user['id']
    username = user['username']

    #left, right = st.columns([8, 2])
    left,middle, right = st.columns([6,2, 2])
    with left:
        st.title("✍️ My Tones")
    #left.header(f"View Your Tones ({username})")  # optional text
    with middle:
        if st.button("Tones", type="primary"):
            #common.navigate_to("addtone")
            st.session_state['spage'] = 'tonelist'
            st.rerun()
    with right:
        if st.button("Create Tone", type="primary"):
            #common.navigate_to("addtone")
            st.session_state['spage'] = 'addtone'
            st.rerun()
        #st.session_state['page'] = 'addtone'
        #st.rerun()
        #common.navigate_to("addtone")
        #st.session_state['page'] = 'addtone'
    # --- Post Creation Form ---
    # with st.expander("➕ Create New Post", expanded=True):
    #     with st.form("new_post_form", clear_on_submit=True):
    #         post_title = st.text_input("Post Title (Required)", max_chars=100)
    #         post_content = st.text_area("Post Content (Required)", height=150)

    #         submit_button = st.form_submit_button("Publish Post", type="primary")

    #         if submit_button:
    #             if post_title and post_content:
    #                 if add_post(user_id, post_title, post_content):
    #                     st.success("Post published successfully!")
    #                     # Rerun to refresh the list of posts below
    #                     st.rerun()
    #                 else:
    #                     st.error("Could not publish post. Please try again.")
    #             else:
    #                 st.warning("Both title and content are required to publish a post.")

    st.markdown("---")

    # --- Post Viewing Section ---
    st.subheader("📝 Tone List")

    user_tones = get_tones_by_user(user_id)
    #st.json(user_tones)

    # selected_tones = common.get_selected_tones_by_user(user_id)
    # st.json(selected_tones)
    #generated_json (7) created_at	is_active	user_id
    if user_tones:
        for tone in user_tones:
            tone_id = tone[0]
            is_active = tone[9] if len(tone) > 9 else 0
            with st.container():
                col1, col2 = st.columns([0.1, 0.9])
                active_checkbox = col1.checkbox(
                    "Active",
                    value=bool(is_active),
                    key=f"active_{tone_id}"
                )
                if active_checkbox != bool(is_active):
                    update_tone_active(tone_id, int(active_checkbox))
                    st.toast(f"Updated: {tone[1]}")  # Small popup notification
                    st.rerun()  # Refresh UI

                col2.markdown(f"""
                    <div style="border: 1px solid #ffcc80; padding: 15px; margin-bottom: 15px; border-radius: 8px; background-color: #fff3e0;">
                        <h4 style="margin-top: 0; color: #e65100;">{tone[1]}</h4>
                        <p style="font-size: 0.9em; color: #666; font-style: italic;">
                            Posted by {tone[10]} on {tone[8].split('.')[0]}
                        </p>
                        <p>{show_micro_humanizer_content(tone[7])}</p>
                    </div>
                """, unsafe_allow_html=True)
    else:
        st.info("You haven't published any posts yet. Use the form above to create your first one!")


def show_tone_list_page():
    """Renders the Post creation and viewing page (NEW)."""
    user = st.session_state['user_info']
    user_id = user['id']
    username = user['username']

    #left, right = st.columns([8, 2])
    left, right = st.columns([8, 2])
    with left:
        st.title("✍️ Tones")

    with right:
        if st.button("Tone List", type="primary"):

            st.session_state['spage'] = ''
            st.rerun()

    st.markdown("---")

    # --- Post Viewing Section ---
    #st.subheader("📝 Tone List")
    st.header("➕ Add New Tone")
    name = st.text_input("Name")
    #email = st.text_input("Email")
    email = ''
    if st.button("Insert Tone"):
        if name:
            common.insert_custom_tone(user_id, name, email)
            st.success("Tone inserted successfully!")
        else:
            st.error("Please fill all fields")

    # Show All Tones
    st.header("📋 All Tones")
    Tones = common.get_custom_tone(user_id)

    for row in Tones:
        tone_id, uname, uemail, active = row

        with st.expander(f"{uname} ({'Active' if active else 'Inactive'})"):
            new_name = st.text_input("Name", value=uname, key=f"name_{tone_id}")
            #new_email = st.text_input("Email", value=uemail, key=f"email_{tone_id}")

            col1, col2, col3 = st.columns(3)
            new_email = ''
            # Update Button
            if col1.button("Update", key=f"update_{tone_id}"):
                common.update_custom_tone(tone_id, new_name, new_email)
                st.success("Tone updated!")

            # Toggle Active Button
            if col2.button("Toggle Active", key=f"toggle_{tone_id}"):
                common.toggle_active_custom_tone(tone_id, active)
                st.info("Status updated!")

            # Delete Button
            if col3.button("Delete", key=f"delete_{tone_id}"):
                common.delete_custom_tone(tone_id)
                st.error("Tone deleted!")

    st.write("Refresh page to view updated records.")

    # user_tones = get_tones_by_user(user_id)
    # #st.json(user_tones)

    # if user_tones:
    #     for tone in user_tones:
    #         tone_id = tone[0]
    #         is_active = tone[9] if len(tone) > 9 else 0
    #         with st.container():
    #             col1, col2 = st.columns([0.1, 0.9])
    #             active_checkbox = col1.checkbox(
    #                 "Active",
    #                 value=bool(is_active),
    #                 key=f"active_{tone_id}"
    #             )
    #             if active_checkbox != bool(is_active):
    #                 update_tone_active(tone_id, int(active_checkbox))
    #                 st.toast(f"Updated: {tone[1]}")  # Small popup notification
    #                 st.rerun()  # Refresh UI

    #             col2.markdown(f"""
    #                 <div style="border: 1px solid #ffcc80; padding: 15px; margin-bottom: 15px; border-radius: 8px; background-color: #fff3e0;">
    #                     <h4 style="margin-top: 0; color: #e65100;">{tone[1]}</h4>
    #                     <p style="font-size: 0.9em; color: #666; font-style: italic;">
    #                         Posted by {tone[10]} on {tone[8].split('.')[0]}
    #                     </p>
    #                     <p>{show_micro_humanizer_content(tone[7])}</p>
    #                 </div>
    #             """, unsafe_allow_html=True)
    # else:
    #     st.info("You haven't published any posts yet. Use the form above to create your first one!")




def delete_content(content_id, user_id):
    """Deletes a content entry from the content_history table for a specific user."""
    try:
        conn = sqlite3.connect(DATABASE_FILE)
        c = conn.cursor()
        # Ensure the content belongs to the user to prevent unauthorized deletion
        c.execute("DELETE FROM content_history WHERE id = ? AND user_id = ?", (content_id, user_id))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error deleting content: {e}")
        return False
# --- Persistent Session State Functions ---


def list_gen_content():
    """Renders the Post creation and viewing page (NEW)."""
    user = st.session_state['user_info']
    user_id = user['id']
    username = user['username']

    #query_params = st.query_params
    #st.markdown(f"Mode: {query_params.get('mode')}")

    left, right = st.columns([8, 2])
    with left:
        st.title("✍️ My Generated Content List")
    #left.header(f"View Your Tones ({username})")  # optional text
    with right:
        if st.button("Generate Content", type="primary"):
            #common.navigate_to("gencontent")
            st.session_state['page'] = 'content'
            st.session_state['spage'] = 'gencontent'
            st.session_state.detection_result = ''
            st.session_state['content_id'] = ''
            st.rerun()
            #common.navigate_to("gencontent")


    st.markdown("---")

    # --- Post Viewing Section ---
    st.subheader("📝 Content List")

    user_content = common.get_content_by_user(user_id)
    #st.json(user_tones)

    # selected_tones = common.get_selected_tones_by_user(user_id)
    # st.json(selected_tones)
    #generated_json (7) created_at	is_active	user_id


    if user_content:
        for content_item in user_content:
            content_id = content_item[0]
            link_text = content_item[1]
            created_at = content_item[10]

            # Use st.columns to place the content title/link and the button side-by-side
            col_content, col_delete = st.columns([0.8, 0.2])

            with col_content:
                # Custom HTML/Markdown for the content card and edit link
                link_href = f"?id={content_id}&mode=edit&refresh=true"
                st.markdown(f"""
                    <div style="border: 1px solid #ffcc80; padding: 15px; margin-bottom: 15px; border-radius: 8px; background-color: #fff3e0;">
                        <h4 style="margin-top: 0; color: #e65100;">
                            <a href="/?refresh=true&page=content&id={content_id}&mode=edit" target="_self">{link_text}</a>
                        </h4>
                        <p style="font-size: 0.9em; color: #666; font-style: italic;">
                            Posted on {created_at}
                        </p>
                    </div>
                """, unsafe_allow_html=True)

            with col_delete:
                # Add the delete button with a unique key and the callback function
                # The button is placed slightly lower to align with the content card
                st.markdown("<div style='height: 25px;'></div>", unsafe_allow_html=True) # Spacer
                st.button(
                    "Delete 🗑️",
                    key=f"delete_btn_{content_id}",
                    on_click=handle_delete_content,
                    args=(content_id, user_id), # Pass content_id and user_id to the callback
                    type="secondary",
                    use_container_width=True
                )
    else:
        st.info("Content is not created yet!")

def handle_delete_content(content_id, user_id):
    """Callback function to handle content deletion."""
    if delete_content(content_id, user_id):
        st.toast(f"Content ID {content_id} deleted successfully!", icon="🗑️")
    else:
        st.error(f"Failed to delete Content ID {content_id}.")
    st.rerun()
# --- Main Application Layout and Routing ---
def show_micro_humanizer_content(role_json):
    #st.json(role_json)
    if isinstance(role_json, str):
        try:
            role_json = json.loads(role_json)
            suggested_agents = role_json.get("micro_agent_list") if isinstance(role_json, dict) else None
            if not suggested_agents:
                suggested_agents = ["ToneMatcher","SentenceVariabilityAdjuster","FlowEnhancer","HumanErrorInjector"]
            for a in suggested_agents:
                st.write(f"- **{a}** — role: {a}; goal: implement the micro-behavior described in role JSON; backstory: derived from blog fingerprint.")
            return ""
        except Exception as e:
            st.error(f"Error parsing role JSON: {e}")
            return ""



def main():
    """Main function to run the Streamlit app."""



    # st.json(st.session_state)
    # st.stop()
    if 'user_info' not in st.session_state:
        st.session_state['user_info'] = None
        st.session_state['logged_in'] = False
        st.rerun()


    st.set_page_config(
        page_title="Streamlit Auth Demo",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    upage = None
    #st.json(st.session_state)
    # 1. Database and State Initialization
    init_db()
    # Now includes checking for persistent session file
    initialize_session_state()
    #st.json(st.session_state)
    # 2. Sidebar/Navigation

    with st.sidebar:
        st.header("App Navigation")

        if st.session_state['logged_in']:



            user = st.session_state['user_info']
            user_id = user['id']
            st.success(f"Logged in as: {user['username']}")

            # --- Navigation buttons ---
            st.markdown("### User Pages")

            # Added 'Posts' to the list of pages
            #user_pages = ['Dashboard', 'Profile', 'Posts', 'Content', 'Tone']
            if user['role'] == 'admin':
                user_pages = ['Dashboard', 'Profile', 'Tone','Content' ,'Humanize','Template','Generate Content','Template Contents','DB']
            else:
                user_pages = ['Dashboard', 'Profile', 'Tone','Content']
            #,'DB'
            # Determine the correct index for the current page selection
            try:
                current_index = user_pages.index(st.session_state['page'].capitalize())
            except ValueError:
                current_index = 0 # Default to Dashboard if page is unknown
            upage = st.query_params.get("page", None)
            if 'refresh' in query_params and query_params['refresh'].lower() == 'true':
                current_index = 3
            # Use radio buttons for clear, responsive navigation selection
            #st.markdown(f"### Navigate to: {current_index}")
            current_selection = st.radio(
                "Go to:",
                user_pages,
                index=current_index,
                key='nav_radio_user'
            )

            # Update page state based on radio button



            if upage:
                st.session_state['page'] = upage
                if 'refresh' in query_params and query_params['refresh'].lower() == 'true' and 'id' in query_params:
                    st.session_state['spage'] = 'gencontent'
                    st.session_state['content_id'] = query_params['id']
                #common.navigate_to("clear")
            else:
                st.session_state['page'] = current_selection.lower()

            #st.markdown(f"Navigating to: **{st.session_state['page']}**")


            # pageSlug = current_selection.lower()
            # common.navigate_to(pageSlug)
            # --- Admin Section (Role-based content) ---
            if user['role'] == 'admin':
                st.markdown("### Admin Tools")
                if st.button("Admin Panel", use_container_width=True, type="secondary"):
                    st.session_state['page'] = 'admin'

            st.markdown("---")
            #st.markdown(f"### Account Actions {cookies}")
            st.button("Logout", on_click=logout_user, use_container_width=True, type="primary", key="logout_btn")

        else:
            st.info("Please sign in or register to access the application features.")
            if st.button("Go to Login/Register", use_container_width=True):
                 st.session_state['page'] = 'login'


    # 3. Content Routing
    if st.session_state['logged_in']:
        # Show the appropriate page based on the session state
        #upage = st.query_params.get("page", "dashboard")

        # if upage not in [None, ""]:
        #     common.navigate_to("clear")
        #     st.session_state['page'] = upage
            #st.rerun()
        page = st.session_state['page']
        # if upage not in [None, ""]:
        #     page = upage[0]

        st.markdown(f"## Navigating to: {page} - {upage}.", unsafe_allow_html=True)
        if page == 'dashboard':
            show_dashboard()
        elif page == 'profile':
            show_profile()
        elif page == 'posts':
            show_post_page()
        elif page == 'content':
            if 'spage' in st.session_state and st.session_state['spage'] == 'gencontent':
                show_post_content()
            else:
                list_gen_content()
                 # NEW Page Routing
        elif upage == 'gencontent':
            #st.markdown(f"## gencontent", unsafe_allow_html=True)
                 # NEW Page Routing
            show_post_content()
        elif upage == 'addtone':
            #st.markdown(f"## addtone", unsafe_allow_html=True)
            micro_humanizer_generator.default_view()
        elif page == 'tone':
            if 'spage' in st.session_state and st.session_state['spage'] == 'addtone':
                micro_humanizer_generator.default_view()
            elif 'spage' in st.session_state and st.session_state['spage'] == 'tonelist':
                show_tone_list_page()
            else:
                show_tone_page()     # NEW Page Routing
        elif page == 'db':

            sqlite.main()     # NEW Page Routing
        elif page == 'humanize':
            humanize_convert.show_post_content()
        elif page == 'template':
            temp_app.template_page(user_id)
        elif page == 'generate content':
            temp_app.generate_content_page(user_id)
        elif page == 'template contents':
            temp_app.content_page(user_id)         # NEW Page Routing
        elif page == 'admin':
            show_admin_page()
        else:
            # Fallback
            show_dashboard()

    else:
        # Show login page if not logged in
        show_login_page()

    #st.markdown(f"---{upage}")
    if upage:
        st.query_params.clear()



    st.markdown(
        """
        <style>
        .st-emotion-cache-1cypcdb { padding-top: 1rem; }
        </style>
        <hr/>
        <p style="font-size: 0.8em; color: #777; text-align: center;">
        ✅ **Persistent Login Fixed:** The app now uses a file (`app_session.json`) to store the login state, meaning you will stay logged in even after a full browser refresh (F5/Ctrl+R) until you click Logout.
        </p>
        """, unsafe_allow_html=True)

if __name__ == '__main__':
    main()
