import os
import re
import sqlite3
import urllib.parse
import streamlit as st
import fitz  # PyMuPDF
from langchain_community.document_loaders import WebBaseLoader
from chains import Chain
from utils import clean_text, extract_email


DB_FILE = "user_data.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            qualification TEXT,
            experience TEXT,
            skills TEXT,
            email TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS email_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_title TEXT,
            email_content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def save_user_info(name, qualification, experience, skills, email):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_info")
    cursor.execute(
        "INSERT INTO user_info (name, qualification, experience, skills, email) VALUES (?, ?, ?, ?, ?)",
        (name, qualification, experience, skills, email)
    )
    conn.commit()
    conn.close()


def get_user_info():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT name, qualification, experience, skills, email FROM user_info LIMIT 1")
    data = cursor.fetchone()
    conn.close()
    return data


def save_email_to_history(job_title, email_content):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO email_history (job_title, email_content) VALUES (?, ?)",
        (job_title, email_content)
    )
    conn.commit()
    conn.close()


def get_email_history():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT job_title, email_content, timestamp FROM email_history ORDER BY timestamp DESC")
    history = cursor.fetchall()
    conn.close()
    return history


def extract_info_from_pdf(uploaded_file, llm_chain):
    if uploaded_file is None:
        return {}
    text = ""
    with fitz.open(stream=uploaded_file.read(), filetype="pdf") as doc:
        for page in doc:
            text += page.get_text()
    cleaned = clean_text(text)
    try:
        return llm_chain.extract_resume_fields(cleaned)
    except Exception as e:
        st.error(f"AI Resume Parsing Failed: {e}")
        return {}


def front_page():
    st.title("📝 Just Fill And Chill")

    chain = Chain()
    uploaded_pdf = st.file_uploader("Upload your LinkedIn PDF Resume:", type="pdf")

    extracted_data = {}
    if uploaded_pdf:
        extracted_data = extract_info_from_pdf(uploaded_pdf, chain)
        st.session_state["show_form"] = True

    if st.button("Manually Fill Details"):
        st.session_state["show_form"] = True

    if st.session_state.get("show_form", False):
        name = st.text_input("Enter your name:", value=extracted_data.get("name", ""))
        qualification = st.text_input("Enter your qualification:", value=extracted_data.get("qualification", ""))
        experience = st.text_input("Enter your experience:", value=extracted_data.get("experience", ""))
        skills = st.text_input("Enter your skills (comma-separated):", value=extracted_data.get("skills", ""))

        if st.button("Submit"):
            if not name or not qualification or not experience:
                st.error("Please fill in all required fields.")
            else:
                email = extracted_data.get("email", "")
                save_user_info(name, qualification, experience, skills, email)
                st.session_state["page"] = "main_page"
                st.rerun()


def create_streamlit_app(llm, clean_text):
    st.title("📧 AI-Powered Job Email Assistant")

    user_info = get_user_info()
    if not user_info:
        st.error("No user data found. Please fill out your profile.")
        if st.button("Go to Front Page"):
            st.session_state["page"] = "front_page"
        return

    name, qualification, experience, skills, email = user_info

    # Menu Bar
    menu = st.columns(3)
    if menu[0].button("📂 View History"):
        st.session_state["viewing_history"] = True
    if menu[1].button("📝 Edit Profile"):
        st.session_state["page"] = "front_page"
        st.rerun()
    if menu[2].button("🔄 Logout"):
        os.remove(DB_FILE)  # Clear DB
        st.session_state.clear()
        st.rerun()

    if st.session_state.get("viewing_history", False):
        st.subheader("📂 Email History")
        history = get_email_history()
        if not history:
            st.info("No past emails found.")
        for job_title, email_content, timestamp in history:
            st.markdown(f"**{job_title}** — _{timestamp}_")
            st.code(email_content, language="markdown")
        if st.button("Back to Email Generator"):
            st.session_state["viewing_history"] = False
        return

    url_input = st.text_input("Paste a job listing URL:")
    if st.button("Generate Email"):
        if not url_input.startswith("http"):
            st.error("Please enter a valid URL.")
            return
        try:
            loader = WebBaseLoader([url_input])
            raw_content = loader.load()
            page_content = raw_content.pop().page_content
            data = clean_text(page_content)
            recipient_email = extract_email(data)
            jobs = llm.extract_jobs(data)
            if not jobs:
                st.warning("No job found on the page.")
                return
            job = jobs[0]
            email_text = llm.write_mail(job, name, qualification, experience, skills)

            subject_line = next((line for line in email_text.splitlines() if line.lower().startswith("subject:")), "Subject: Cold Email")
            subject = subject_line.replace("Subject:", "").strip()
            email_body = "\n".join([line for line in email_text.splitlines() if not line.lower().startswith("subject:")])

            body_encoded = urllib.parse.quote(email_body)
            subject_encoded = urllib.parse.quote(subject)

            mailto_url = f"mailto:{recipient_email}?subject={subject_encoded}&body={body_encoded}"
            gmail_url = f"https://mail.google.com/mail/?view=cm&fs=1&to={urllib.parse.quote(recipient_email or '')}&su={subject_encoded}&body={body_encoded}"

            save_email_to_history(job["role"], email_text)

            st.code(email_text, language="markdown")
            st.markdown(f"""
                <div style="display:flex;flex-direction:column;gap:10px;">
                    <a href="{gmail_url}" target="_blank">
                        <button style="padding:10px 20px;background-color:#4CAF50;color:white;border:none;border-radius:5px;">📧 Send via Gmail</button>
                    </a>
                    <a href="{mailto_url}" target="_blank">
                        <button style="padding:10px 20px;background-color:#2196F3;color:white;border:none;border-radius:5px;">📧 Send via Email App</button>
                    </a>
                </div>
            """, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Error: {e}")


if __name__ == "__main__":
    init_db()
    st.set_page_config(layout="centered", page_title="Job Email Generator", page_icon="📧")

    if "page" not in st.session_state:
        if get_user_info():
            st.session_state["page"] = "main_page"
        else:
            st.session_state["page"] = "front_page"

    if st.session_state["page"] == "front_page":
        front_page()
    elif st.session_state["page"] == "main_page":
        create_streamlit_app(Chain(), clean_text)
