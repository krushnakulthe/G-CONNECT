import streamlit as st
import json
import os
import re
from pathlib import Path
import base64
import plotly.express as px
import pandas as pd
import PyPDF2

# File paths
USER_FILE = "users.json"
VIDEO_FILE = "videos.json"
PDF_DIR = "pdfs"
PDF_META_FILE = "pdf_metadata.json"
PROGRESS_FILE = "progress.json"

# Admin user(s)
ADMIN_USERS = ["admin"]

# Ensure files and folders exist
Path(USER_FILE).touch(exist_ok=True)
Path(VIDEO_FILE).touch(exist_ok=True)
Path(PROGRESS_FILE).touch(exist_ok=True)
Path(PDF_META_FILE).touch(exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)

# Load/save functions
def load_users():
    try:
        with open(USER_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def save_users(users):
    with open(USER_FILE, "w") as f:
        json.dump(users, f, indent=2)

def load_videos():
    try:
        with open(VIDEO_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def save_videos(videos):
    with open(VIDEO_FILE, "w") as f:
        json.dump(videos, f, indent=2)

def load_progress():
    try:
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def save_progress(progress):
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2)

def load_pdf_metadata():
    try:
        with open(PDF_META_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def save_pdf_metadata(meta):
    with open(PDF_META_FILE, "w") as f:
        json.dump(meta, f, indent=2)

# Authentication and validation
def validate_user(username, password):
    users = load_users()
    if username in users:
        if users[username].get("disabled", False):
            return False
        if users[username].get("password") == password:
            users[username]["last_login"] = pd.Timestamp.now().isoformat()
            save_users(users)
            return True
    return False

def is_admin(username):
    return username in ADMIN_USERS

def is_valid_username(username):
    return re.match("^[A-Za-z0-9_]{3,20}$", username) is not None

def is_strong_password(password):
    return len(password) >= 6 and any(c.isdigit() for c in password) and any(c.isalpha() for c in password)

def patch_old_users():
    users = load_users()
    for u in users:
        users[u].setdefault("branch", "CSE")
        users[u].setdefault("year", "FE")
        users[u].setdefault("semester", "Sem 1")
    save_users(users)

def show_pdf(pdf_path):
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        pdf_text = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                sanitized = text.encode("utf-16", "surrogatepass").decode("utf-16", "ignore")
                pdf_text += sanitized
        st.text_area("PDF Content", pdf_text, height=400)

def login_signup_page():
    st.title("\U0001F4DA G-CONNECT")
    menu = st.sidebar.selectbox("Menu", ["Login", "Sign Up"])

    if "login_attempts" not in st.session_state:
        st.session_state.login_attempts = 0

    if menu == "Login":
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if st.session_state.login_attempts >= 3:
                st.error("\u274C Too many failed attempts. Try again later.")
            elif validate_user(username, password):
                if load_users()[username].get("disabled", False):
                    st.error("\u26D4 Your account is currently disabled. Contact admin.")
                    return
                st.session_state.logged_in = True
                st.session_state.user = username
                st.session_state.login_attempts = 0
                st.success("\u2705 Logged in successfully!")
                st.rerun()
            else:
                st.session_state.login_attempts += 1
                st.error(f"\u274C Invalid credentials ({st.session_state.login_attempts}/3)")

    elif menu == "Sign Up":
        name = st.text_input("Enter your Name")
        username = st.text_input("Create Username")
        password = st.text_input("Create Password", type="password")
        branch = st.selectbox("Branch", ["CSE", "ECE", "MECH", "CIVIL", "EEE"], key="signup_branch")
        year = st.selectbox("Year", ["1st", "2nd", "3rd", "4th"], key="signup_year")
        semester = st.selectbox("Semester", ["Sem 1", "Sem 2", "Sem 3", "Sem 4", "Sem 5", "Sem 6", "Sem 7", "Sem 8"], key="signup_semester")
        if st.button("Sign Up"):
            users = load_users()
            if username in users:
                st.error("\u274C Username already exists")
            elif not is_valid_username(username):
                st.error("\u274C Invalid username format")
            elif not is_strong_password(password):
                st.error("\u274C Weak password")
            else:
                users[username] = {
                    "password": password,
                    "branch": branch,
                    "year": year,
                    "semester": semester,
                    "name": name,
                    "disabled": False
                }
                save_users(users)
                st.success("\u2705 Account created! Please log in.")

def video_pdf_portal():
    st.title("\U0001F3AC Videos and \U0001F4C4 PDFs")
    videos = load_videos()
    user = st.session_state.user
    users = load_users()
    progress = load_progress()
    pdf_meta = load_pdf_metadata()

    if is_admin(user):
        tab1, tab2, tab3, tab4 = st.tabs(["Watch Videos", "View PDFs", "Edit Profile", "Admin Panel"])
    else:
        tab1, tab2, tab3 = st.tabs(["Watch Videos", "View PDFs", "Edit Profile"])

    user_data = users.get(user, {})
    user_branch = user_data.get("branch", "")
    user_year = user_data.get("year", "")
    user_semester = user_data.get("semester", "")

    with tab1:
        category = st.selectbox("Select Video Category", ["General", "Lecture", "Tutorial"])
        if videos:
            for i, video in enumerate(videos):
                if video.get("category") == category and video.get("branch") == user_branch and video.get("year") == user_year and video.get("semester") == user_semester:
                    st.subheader(video["title"])
                    st.video(video["url"])
        else:
            st.info("No videos available.")

    with tab2:
        pdf_files = [f for f in os.listdir(PDF_DIR) if pdf_meta.get(f, {}).get("branch") == user_branch and pdf_meta.get(f, {}).get("year") == user_year and pdf_meta.get(f, {}).get("semester") == user_semester]
        for pdf in pdf_files:
            st.markdown(f"**{pdf_meta[pdf]['title']}**")
            if st.button(f"\U0001F4D6 View {pdf}", key=f"view_{pdf}"):
                show_pdf(os.path.join(PDF_DIR, pdf))
                if user not in progress:
                    progress[user] = []
                if pdf not in progress[user]:
                    progress[user].append(pdf)
                    save_progress(progress)

    with tab3:
        st.subheader("\u270F\uFE0F Edit Profile")
        name = st.text_input("Full Name", value=user_data.get("name", ""))
        password = st.text_input("New Password", type="password")
        branch = st.selectbox("Branch", ["CSE", "ECE", "MECH", "CIVIL", "EEE"], index=["CSE", "ECE", "MECH", "CIVIL", "EEE"].index(user_branch))
        year = st.selectbox("Year", ["1ST", "2ND", "3RD", "4TH"], index=["FE", "SE", "TE", "BE"].index(user_year))
        semester = st.selectbox("Semester", ["Sem 1", "Sem 2", "Sem 3", "Sem 4", "Sem 5", "Sem 6", "Sem 7", "Sem 8"], index=["Sem 1", "Sem 2", "Sem 3", "Sem 4", "Sem 5", "Sem 6", "Sem 7", "Sem 8"].index(user_semester))
        if st.button("Update Profile"):
            if password and not is_strong_password(password):
                st.error("\u274C Weak password")
            else:
                users[user].update({"name": name, "branch": branch, "year": year, "semester": semester})
                if password:
                    users[user]["password"] = password
                save_users(users)
                st.success("\u2705 Profile updated")

    if is_admin(user):
        with tab4:
            st.title("\U0001F6E0 Admin Panel")
            user_df = pd.DataFrame.from_dict(users, orient="index")
            student_df = user_df[~user_df.index.isin(ADMIN_USERS)]

            total_students = len(student_df)
            active_students = student_df["last_login"].dropna().apply(pd.to_datetime)
            active_this_week = active_students[active_students > pd.Timestamp.now() - pd.Timedelta(days=7)]

            col1, col2 = st.columns(2)
            col1.metric("Total Students", total_students)
            col2.metric("Active This Week", len(active_this_week))

            if not active_students.empty:
                fig = px.histogram(active_students, nbins=7, title="Student Logins (Past Week)")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No login data available yet.")

            st.subheader("\U0001F465 Manage Users")
            selected_user = st.selectbox("Select user", student_df.index.tolist())
            if selected_user:
                with st.expander(f"Details of {selected_user}"):
                    st.json(users[selected_user])
                is_disabled = users[selected_user].get("disabled", False)
                if st.button("\u2705 Enable User" if is_disabled else "\u26D4 Disable User"):
                    users[selected_user]["disabled"] = not is_disabled
                    save_users(users)
                    st.success(f"User '{selected_user}' is now {'enabled' if not is_disabled else 'disabled'}.")

            with st.expander("\U0001F4C4 Upload PDF"):
                pdf_file = st.file_uploader("Choose a PDF file", type=["pdf"])
                pdf_title = st.text_input("PDF Title")
                pdf_branch = st.selectbox("Branch", ["CSE", "ECE", "MECH", "CIVIL", "EEE"], key="pdf_branch")
                pdf_year = st.selectbox("Year", ["FE", "SE", "TE", "BE"], key="pdf_year")
                pdf_semester = st.selectbox("Semester", ["Sem 1", "Sem 2", "Sem 3", "Sem 4", "Sem 5", "Sem 6", "Sem 7", "Sem 8"], key="pdf_semester")
                if st.button("Upload PDF") and pdf_file:
                    pdf_path = os.path.join(PDF_DIR, pdf_file.name)
                    with open(pdf_path, "wb") as f:
                        f.write(pdf_file.read())
                    meta = load_pdf_metadata()
                    meta[pdf_file.name] = {"title": pdf_title, "branch": pdf_branch, "year": pdf_year, "semester": pdf_semester}
                    save_pdf_metadata(meta)
                    st.success(f"\u2705 PDF '{pdf_title}' uploaded!")

            st.subheader("📤 Delete PDFs")
            pdf_meta = load_pdf_metadata()
            for filename in list(pdf_meta.keys()):
                if st.button(f"🗑️ Delete {filename}", key=f"delete_pdf_{filename}"):
                    try:
                        os.remove(os.path.join(PDF_DIR, filename))
                    except FileNotFoundError:
                        pass
                    del pdf_meta[filename]
                    save_pdf_metadata(pdf_meta)
                    st.success(f"PDF '{filename}' deleted")

            with st.expander("\U0001F39E Add Video"):
                video_title = st.text_input("Video Title")
                video_url = st.text_input("YouTube Embed URL")
                video_category = st.selectbox("Category", ["General", "Lecture", "Tutorial"])
                video_branch = st.selectbox("Video Branch", ["CSE", "ECE", "MECH", "CIVIL", "EEE"], key="video_branch")
                video_year = st.selectbox("Video Year", ["FE", "SE", "TE", "BE"], key="video_year")
                video_semester = st.selectbox("Video Semester", ["Sem 1", "Sem 2", "Sem 3", "Sem 4", "Sem 5", "Sem 6", "Sem 7", "Sem 8"], key="video_semester")
                if st.button("Add Video"):
                    videos = load_videos()
                    videos.append({"title": video_title, "url": video_url, "category": video_category, "branch": video_branch, "year": video_year, "semester": video_semester})
                    save_videos(videos)
                    st.success(f"\u2705 Video '{video_title}' added!")

            st.subheader("🗑️ Delete Videos")
            videos = load_videos()
            for i, video in enumerate(videos):
                if st.button(f"Delete Video: {video['title']}", key=f"delete_video_{i}"):
                    del videos[i]
                    save_videos(videos)
                    st.success(f"Deleted video: {video['title']}")
                    st.experimental_rerun()  # refresh UI after deletion

    st.sidebar.markdown("---")
    if st.sidebar.button("\U0001F6AA Logout"):
        st.session_state.logged_in = False
        st.session_state.user = ""
        st.rerun()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
patch_old_users()
if st.session_state.logged_in:
    video_pdf_portal()
else:
    login_signup_page()