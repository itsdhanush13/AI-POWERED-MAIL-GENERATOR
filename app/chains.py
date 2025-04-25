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
        prompt_extract = PromptTemplate.from_template(
            """
            ### SCRAPED TEXT FROM WEBSITE: 
            {page_data}
            ### INSTRUCTION: 
            Extract job listings and return them as JSON objects with:
            `role`, `experience`, `skills`, `responsibilities`, and `qualifications`. 
            Only return valid JSON.
            """
        )
        chain_extract = prompt_extract | self.llm
        res = chain_extract.invoke(input={"page_data": cleaned_text})
        try:
            parser = JsonOutputParser()
            parsed = parser.parse(res.content)
        except OutputParserException:
            raise OutputParserException("Unable to parse jobs. Check the content size or format.")
        return parsed if isinstance(parsed, list) else [parsed]

    def write_mail(self, job, name, qualification, experience, skills):
        skill_line = f" I also have experience with {skills}." if skills else ""

        prompt_email = PromptTemplate.from_template(
            """
            ### JOB DESCRIPTION:
            {job_description}

            ### INSTRUCTION:
            Write a cold email for the job based on the following user profile:
            Name: {name}
            Qualification: {qualification}
            Experience: {experience}
            Skills: {skills}

            Generate a compelling subject line that reflects the content of the email.
            Avoid mentioning the company name in the subject.
            Start the email with the subject line in the format: Subject: [Your Subject]
            Follow it with the body of the email.
            End the email with "Sincerely, {name}".
            Do not include any intro lines like "Here's a cold email..."

            ### EMAIL:
            """
        )

        chain_email = prompt_email | self.llm
        res = chain_email.invoke({
            "job_description": str(job),
            "name": name,
            "qualification": qualification,
            "experience": experience,
            "skills": skills
        })

        return res.content