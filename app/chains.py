import os
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException
from dotenv import load_dotenv

load_dotenv()


class Chain:
    def __init__(self):
        self.llm = ChatGroq(
            temperature=0,
            groq_api_key=os.getenv("GROQ_API_KEY"),
            model_name="meta-llama/llama-4-scout-17b-16e-instruct"
        )

    def extract_jobs(self, cleaned_text):
        prompt_extract = PromptTemplate.from_template("""
        You are a job info extractor.

        From the given job listing page text, extract ONE job listing and return it as a **valid JSON object** with the following fields:
        - role
        - experience
        - skills
        - responsibilities
        - qualifications

        Do NOT write explanations or commentary. Just return the raw JSON object exactly in this format:

        {{
            "role": "...",
            "experience": "...",
            "skills": "...",
            "responsibilities": "...",
            "qualifications": "..."
        }}

        ### TEXT TO PARSE:
        {page_data}
        """)

        chain_extract = prompt_extract | self.llm
        res = chain_extract.invoke(input={"page_data": cleaned_text})

        print("📄 RAW MODEL OUTPUT:\n", res.content)

        try:
            parser = JsonOutputParser()
            parsed = parser.parse(res.content)
        except OutputParserException:
            raise OutputParserException("Unable to parse jobs. The model may have returned bad JSON.")

        return [parsed] if isinstance(parsed, dict) else parsed

    def write_mail(self, job, name, qualification, experience, skills):
        prompt_email = PromptTemplate.from_template("""
        ### JOB DESCRIPTION:
        {job_description}

        ### CANDIDATE CONTEXT:
        - The candidate is named {name}
        - They recently completed their qualification: {qualification}
        - Their experience level is: {experience}
        - They have skills in: {skills}

        ### INSTRUCTIONS:
        Write a professional cold email applying for the above job.
        Integrate the candidate’s background naturally — do not list it as bullet points.
        Do not mention "My name is" or "I am writing this because...". Write as a confident candidate.
        Keep the tone warm, concise, and focused on why they’re a good fit.
        Avoid generic fluff and avoid repeating job description phrases.

        Start the email with a compelling subject line in this format:
        Subject: [Your Subject Line]

        Then write the body of the email, and end with:
        "Sincerely, {name}"

        ### EMAIL:
        """)

        chain_email = prompt_email | self.llm
        res = chain_email.invoke({
            "job_description": str(job),
            "name": name,
            "qualification": qualification,
            "experience": experience,
            "skills": skills
        })

        return res.content

    def extract_resume_fields(self, resume_text):
        prompt = PromptTemplate.from_template("""
        ### RESUME TEXT:
        {resume_text}

        ### TASK:
        Extract the following fields from the resume and return as JSON:
        - name
        - qualification
        - experience
        - skills (comma-separated)
        - email

        If any field is not found, return it as an empty string.

        ### OUTPUT FORMAT (JSON):
        {{
            "name": "...",
            "qualification": "...",
            "experience": "...",
            "skills": "...",
            "email": "..."
        }}
        """)

        chain = prompt | self.llm
        try:
            result = chain.invoke({"resume_text": resume_text})
            parser = JsonOutputParser()
            return parser.parse(result.content)
        except OutputParserException:
            raise OutputParserException("Could not parse resume fields.")
