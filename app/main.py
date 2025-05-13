import os
import re
import urllib.parse
import streamlit as st
import fitz  # PyMuPDF
from langchain_community.document_loaders import WebBaseLoader
from chains import Chain
from utils import clean_text, extract_email


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
    st.set_page_config(layout="centered", page_title="Resume & PDF Autofill", page_icon="📝")
    st.title("📝 Just Fill And Chill")

    # Session flag to track form visibility
    if "show_form" not in st.session_state:
        st.session_state["show_form"] = False

    chain = Chain()
    uploaded_pdf = st.file_uploader("Upload your LinkedIn PDF Resume:", type="pdf")

    extracted_data = {}
    if uploaded_pdf:
        st.session_state['uploaded_pdf'] = uploaded_pdf
        extracted_data = extract_info_from_pdf(uploaded_pdf, chain)
        st.session_state["show_form"] = True  # Automatically show form if resume is uploaded

    if st.button("Manually Fill Details"):
        st.session_state["show_form"] = True

    if st.session_state["show_form"]:
        name = st.text_input("Enter your name:", value=extracted_data.get("name", ""), placeholder="Your full name")
        qualification = st.text_input("Enter your qualification:", value=extracted_data.get("qualification", ""), placeholder="e.g. BCA, MCA, B.Tech")
        experience = st.text_input("Enter your experience:", value=extracted_data.get("experience", ""), placeholder="e.g. 1 year internship, 6 months project")
        skills = st.text_input("Enter your skills (comma-separated, optional):", value=extracted_data.get("skills", ""), placeholder="e.g. Python, Web Development, AI")

        if st.button("Submit"):
            if not name:
                st.error("Please enter your name.")
            elif not qualification:
                st.error("Please enter your qualification.")
            elif not experience:
                st.error("Please enter your experience.")
            else:
                st.session_state['name'] = name
                st.session_state['qualification'] = qualification
                st.session_state['experience'] = experience
                st.session_state['skills'] = skills
                st.session_state['email'] = extracted_data.get("email")
                st.session_state['submitted'] = True
                st.session_state['page'] = 'main_page'
                st.rerun()


def create_streamlit_app(llm, clean_text):
    st.set_page_config(layout="centered", page_title="Cold Email Generator", page_icon="📧")
    st.title("📧 AI-POWERED JOB EMAIL ASSISTANT")

    name = st.session_state.get('name', '')
    qualification = st.session_state.get('qualification', '')
    experience = st.session_state.get('experience', '')
    skills = st.session_state.get('skills', '')

    if not name or not qualification or not experience:
        st.error("Please go to the front page and provide all your details.")
        if st.button("Go to Front Page"):
            st.session_state['page'] = 'front_page'
        return

    url_input = st.text_input("Paste a job listing URL:", placeholder="e.g. https://company.com/job/software-engineer")
    submit_button = st.button("Generate Email")

    if submit_button:
        if not url_input or not url_input.startswith("http"):
            st.error("Please enter a valid job listing URL.")
            return

        try:
            loader = WebBaseLoader([url_input])
            raw_content = loader.load()
            if not raw_content:
                st.warning("Could not load the job page. Please try another URL.")
                return

            page_content = raw_content.pop().page_content
            data = clean_text(page_content)

            recipient_email = extract_email(data)
            jobs = llm.extract_jobs(data)

            if not jobs:
                st.warning("No job details were extracted from this page.")
                return

            job = jobs[0]
            email = llm.write_mail(
                job=job,
                name=name,
                qualification=qualification,
                experience=experience,
                skills=skills
            )

            email_lines = email.splitlines()
            subject_line = next((line for line in email_lines if line.lower().startswith("subject:")), "Subject: Cold Email")
            subject = subject_line.replace("Subject:", "").strip()
            body_lines = [line for line in email_lines if not line.lower().startswith("subject:")]
            email_body_cleaned = "\n".join(body_lines).strip()

            gmail_body = f"{email_body_cleaned}\n\n"
            subject_encoded = urllib.parse.quote(subject)
            body_encoded = urllib.parse.quote(gmail_body)

            gmail_url = f"https://mail.google.com/mail/?view=cm&fs=1&to=test@example.com&su=Test%20Subject&body=This%20is%20a%20test%20email."

            st.code(gmail_body, language='markdown')
            st.markdown(f"""
                <a href="{gmail_url}" target="_blank">
                    <button style="padding:10px 20px;background-color:#4CAF50;
                                   color:white;border:none;border-radius:5px;
                                   cursor:pointer;font-size:16px;">
                        📧 Send Email
                    </button>
                </a>
            """, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"An Error Occurred: {e}")


if __name__ == "__main__":
    chain = Chain()

    if 'page' not in st.session_state:
        st.session_state['page'] = 'front_page'

    if st.session_state['page'] == 'front_page':
        front_page()
    elif st.session_state['page'] == 'main_page':
        create_streamlit_app(chain, clean_text)
