import os
import streamlit as st
from langchain_community.document_loaders import WebBaseLoader
import urllib.parse
from chains import Chain
from utils import clean_text, extract_email

def front_page():
    st.set_page_config(layout="wide", page_title="Resume & LinkedIn Submission", page_icon="📝")
    st.title("📝 Upload Details & LinkedIn Profile")

    # User name input
    name = st.text_input("Enter your name:", placeholder="Your full name")

    # Qualification input
    qualification = st.text_input("Enter your qualification:", placeholder="e.g. BCA, MCA, B.Tech")

    # Experience input
    experience = st.text_input("Enter your experience:", placeholder="e.g. 1 year internship, 6 months project")

    # Optional Skills input
    skills = st.text_input("Enter your skills (comma-separated, optional):", placeholder="e.g. Python, Web Development, AI")

    # LinkedIn profile link
    linkedin_link = st.text_input("Enter your LinkedIn Profile Link:")

    # Resume Drive Link
    resume_drive_link = st.text_input("Paste your resume Drive link:")

    if 'submitted' not in st.session_state:
        st.session_state['submitted'] = False

    if st.button("Submit"):
        if not name:
            st.error("Please enter your name.")
        elif not qualification:
            st.error("Please enter your qualification.")
        elif not experience:
            st.error("Please enter your experience.")
        elif not linkedin_link:
            st.error("Please provide your LinkedIn profile link.")
        elif not resume_drive_link:
            st.error("Please paste your resume Drive link.")
        else:
            # Save inputs in session state
            st.session_state['name'] = name
            st.session_state['qualification'] = qualification
            st.session_state['experience'] = experience
            st.session_state['skills'] = skills
            st.session_state['linkedin_link'] = linkedin_link
            st.session_state['resume_drive_link'] = resume_drive_link

            st.session_state['submitted'] = True
            st.session_state['page'] = 'main_page'

def create_streamlit_app(llm, clean_text):
    st.set_page_config(layout="wide", page_title="Cold Email Generator", page_icon="📧")
    st.title("📧 AI-POWERED JOB EMAIL ASSISTANT")

    # Retrieve session state variables
    name = st.session_state.get('name', '')
    qualification = st.session_state.get('qualification', '')
    experience = st.session_state.get('experience', '')
    skills = st.session_state.get('skills', '')
    linkedin_link = st.session_state.get('linkedin_link', '')
    resume_drive_link = st.session_state.get('resume_drive_link', '')

    if not name or not qualification or not experience or not linkedin_link or not resume_drive_link:
        st.error("Please go to the front page and provide all your details.")
        if st.button("Go to Front Page"):
            st.session_state['page'] = 'front_page'
        return

    url_input = st.text_input("Enter a URL:", placeholder="Drop a job listing link to generate tailored emails...")
    submit_button = st.button("Submit")

    if submit_button:
        try:
            loader = WebBaseLoader([url_input])
            data = clean_text(loader.load().pop().page_content)
            recipient_email = extract_email(data)
            jobs = llm.extract_jobs(data)

            for job in jobs:
                email = llm.write_mail(
                    job=job,
                    name=name,
                    qualification=qualification,
                    experience=experience,
                    skills=skills
                )

                email_lines = email.splitlines()
                subject_line = next((line for line in email_lines if line.lower().startswith("subject:")),
                                    "Subject: Cold Email from AtliQ")
                subject = subject_line.replace("Subject:", "").strip()
                body_lines = [line for line in email_lines if not line.lower().startswith("subject:")]
                email_body_cleaned = "\n".join(body_lines).strip()

                gmail_body = (
                    f"{email_body_cleaned}\n\n"
                    "📎 Resume:\n"
                    f"{resume_drive_link}\n\n"
                    "🔗 LinkedIn:\n"
                    f"{linkedin_link}"
                )

                subject_encoded = urllib.parse.quote(subject)
                body_encoded = urllib.parse.quote(gmail_body)
                mailto_url = f"mailto:{urllib.parse.quote(recipient_email or '')}?subject={subject_encoded}&body={body_encoded}"

                st.code(email_body_cleaned, language='markdown')
                st.markdown(f"""
                    <a href="{mailto_url}">
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
