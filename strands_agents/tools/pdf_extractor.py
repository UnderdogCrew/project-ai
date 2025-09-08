import csv
import json
import os
from pathlib import Path
from typing import Optional, List, Union, Any, Dict
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from strands_agents.tools.toolkit import Toolkit
from strands_agents.utils.log import logger
import pandas as pd
import re
from tqdm import tqdm
import boto3
from botocore.exceptions import ClientError
from datetime import datetime

try:
    from pyzerox import zerox
except ImportError:
    raise ImportError("`zerox` not installed. Please install using `pip install py-zerox`.")


# Custom system prompt for detecting multiple resumes
SPLIT_PROMPT = """
You are a document analyzer. Your task is to:
1. Determine if this document contains multiple resumes
2. If it does, identify where each resume starts and ends
3. Return the count of resumes found

Look for clear indicators like:
- New contact information sections
- Multiple different names
- Distinct education/experience sections
- Page breaks between resumes

Return your response as a JSON with:
- "multiple_resumes": boolean
- "resume_count": number
"""

# Custom prompt template for resume parsing
RESUME_PROMPT = """
You are a resume parser. Extract the following information from the resume in a structured format:
    - Full Name
    - Email
    - Nationality
    - Mobile/Phone Number
    - Work Experience(as a string, including years of experience, job titles, and company names.work expeirce ,career summary all included)
    - Skills (as a string, including but not limited to digital skills, key skills, skills and competencies, communication and interpersonal skills)
    - Education (as an string, including degree, field of study, institution name, and location,year of passing)
    - Passport Information
    - Home Language (or mother language)
    - Spoken Languages (as a string, including fields like "languages" or "languages known" or "other languages")
    - Date of Birth (DOB, include date of birth as in document)
    - Gender
    - Driving License Number
    - Current Residential Address
    - Home Address(as a string/include home address in contact details)
    - Marital Status   

Resume content:
{text}

Format the output as a JSON object with these fields. Ensure the output is valid JSON format.
Important:        
-Don't add ```json in the response, instead return the json array

"""



class PdfTools(Toolkit):
    def __init__(
        self,
        api_key: str,
        aws_access_key_id: str = None,  # Add AWS credentials
        aws_secret_access_key: str = None,
        aws_bucket_name: str = None,
        aws_url: str = None
    ):
        super().__init__()

        os.environ["OPENAI_API_KEY"] = api_key
        self.api_key = api_key
        # Initialize the ChatOpenAI model
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)  # Changed to gpt-4o-mini
        self.prompt = ChatPromptTemplate.from_template(RESUME_PROMPT)
        self.csvs: List[Path] = []
        self.aws_url = aws_url
        self.current_timestamp = int(datetime.now().timestamp())
        # Define directories
        # Get the current directory
        current_directory = os.getcwd()

        # Define the folder name
        folder_name = "resumes"
        output_folder = "output_results"

        # Create the full folder path
        folder_path = os.path.join(current_directory, folder_name)
        output_folder_path = os.path.join(current_directory, output_folder)
        
        # Check if the folder exists, if not, create it
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
        
        if not os.path.exists(output_folder_path):
            os.makedirs(output_folder_path)

        self.resume_directory = folder_path
        self.output_dir = output_folder_path
        self.register(self.query_csv_file, name="pdf_extractor")

        # Initialize S3 client
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key
        ) if aws_access_key_id and aws_secret_access_key else None
        self.bucket_name = aws_bucket_name

    def check_multiple_resumes(self, text: str) -> Dict:
        """Check if the document contains multiple resumes."""
        messages = [{"role": "user", "content": SPLIT_PROMPT + "\n\n" + text}]
        response = self.llm.invoke(messages)
        try:
            return json.loads(response.content)
        except json.JSONDecodeError:
            return {"multiple_resumes": False, "resume_count": 1}

    async def split_resumes(self, text: str) -> List[str]:
        """Split text into individual resumes using Zerox's capabilities."""
        try:
            # Use Zerox to identify document boundaries
            split_result = await zerox(
                text=text,
                model="gpt-4o-mini",  # Changed to gpt-4o-mini
                custom_system_prompt="Split this document into individual resumes. Return each resume as a separate section.",
                return_segments=True
            )
            return split_result if isinstance(split_result, list) else [text]
        except Exception as e:
            print(f"Error splitting resumes: {str(e)}")
            return [text]

    def process_single_resume(self, text: str) -> Dict:
        """Process a single resume text and extract information."""
        try:
            messages = self.prompt.format_messages(text=text)
            response = self.llm.invoke(messages)
            
            try:
                parsed_json = json.loads(response.content)
                # Ensure skills are formatted as a string
                if 'skills' in parsed_json:
                    skills = parsed_json['skills']
                    if isinstance(skills, list):
                        # Convert skills list to a string
                        parsed_json['skills'] = ', '.join(skills)  # Join if it's a list
                    elif isinstance(skills, str):
                        # Clean up the skills string if it contains bullet points
                        parsed_json['skills'] = skills.replace('•', '').replace('\n', ', ').strip()  # Remove bullet points and newlines
                return parsed_json
            except json.JSONDecodeError:
                print("Error parsing JSON response")
                return {}
                
        except Exception as e:
            print(f"Error processing resume: {str(e)}")
            return {}



    async def process_pdf_file(self, file_path: str) -> List[Dict]:
        """Process a PDF file that might contain multiple resumes."""
        try:
            # Extract text from PDF using Zerox
            extracted_output = await zerox(
                file_path=file_path,
                model="gpt-4o-mini",  # Changed to gpt-4o-mini
                max_tokens=4096,
                output_dir=self.output_dir,
            )
            extracted_text = "\n".join(page.content for page in extracted_output.pages)
        
            # Check if the document contains multiple resumes
            check_result = self.check_multiple_resumes(extracted_text)
            
            if check_result.get("multiple_resumes", False):
                # Split the document into individual resumes
                resume_texts = self.split_resumes(extracted_text)
            else:
                resume_texts = [extracted_text]
            
            # Process each resume
            results = []
            for idx, resume_text in enumerate(resume_texts, 1):
                result = self.process_single_resume(resume_text)
                result["resume_index"] = idx
                results.append(result)
            
            return results
                
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")
            return [{}]

    async def process_multiple_files(self) -> Dict[str, List[Dict]]:
        """Process multiple PDF files from a directory."""
        # Create output directory if it doesn't exist
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        
        # Get all PDF files in the directory
        pdf_files = [str(f) for f in Path(self.resume_directory).glob("*.pdf")]
        print("pdf_files", pdf_files)
        results = {}
        # Process files with progress bar
        for pdf_file in tqdm(pdf_files, desc="Processing PDF files"):
            file_results = await self.process_pdf_file(pdf_file)
            results[pdf_file] = file_results   
        return results

    def convert_md_to_json(self, file_path: str) -> None:
        """Convert MD file to JSON using Claude API and save as CSV."""
        def json_to_csv(self, json_content: str) -> None:
            """Convert JSON string content to CSV file with proper None handling."""
            
            def format_multiline(text: str, max_length: int) -> str:
                """Format text into multiple lines if it exceeds max_length."""
                if len(text) > max_length:
                    return '\n'.join([text[i:i + max_length] for i in range(0, len(text), max_length)])
                return text

            try:
                parsed_json = json.loads(json_content)
                csv_file = Path(self.output_dir) / f"{str(self.current_timestamp)}.csv"
                file_exists = csv_file.exists()
                
                with open(csv_file, 'a', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    
                    if not file_exists:
                        writer.writerow(['Name', 'Email','Nationality', 'Mobile', 'Work Experience','Skills', 
                                        'Education','Passport Info', 
                                        'Home Language', 'Spoken Languages',
                                        'Date Of Birth', 'Gender', 'Driving License Number', 
                                        'Current Residential Address', 'Home Address',
                                        'Marital Status'])
                    
                    for resume in parsed_json:
                        # Handle all other fields with consistent null handling
                        name = str(resume.get('name', "N/A") or '').strip() or "N/A"
                                            # try:
                        mobile = str(resume.get('mobile', "N/A") or '').strip() or "N/A"
                        email = str(resume.get('email', "N/A") or '').strip() or "N/A"
                        # Handle experience field
                        work_experience = resume.get('work_experience', "N/A")
                        work_experience = format_multiline(text=str(work_experience).replace('\n', ' ').strip(), max_length=50)  # Format experience for multiline
                        
                        skills = resume.get('skills', "N/A")
                        skills_str = format_multiline(text=str(skills).replace('\n', ' ').strip(), max_length=50) 
                    
                        education = resume.get('education', "N/A")
                        education_str = format_multiline(text=str(education).replace('\n', ' ').strip(), max_length=50)  
                        passport_info = str(resume.get('passport_info', "N/A") or '').strip() or "N/A" 
                        
                        # Handle address fields
                        current_residential_address1 = resume.get('current_residential_address', "N/A") 
                        current_residential_address = format_multiline(text=str(current_residential_address1).replace('\n', ' ').strip(), max_length=50) 

                        home_address1 = resume.get('home_address', "N/A") 
                        home_address = format_multiline(text=str(home_address1).replace('\n', ' ').strip(), max_length=50) 
                        home_language = str(resume.get('home_language', "N/A") or '').strip() or "N/A"
                        spoken_languages1 = resume.get('spoken_languages', "N/A")  # Get spoken_languages, default to "N/A"
                        spoken_languages_str = format_multiline(text=str(spoken_languages1).replace('\n', ' ').strip(), max_length=50) 
                        nationality = str(resume.get('nationality', "N/A") or '').strip() or "N/A"
                        date_of_birth = str(resume.get('date_of_birth', "N/A")).strip()  # Default to "N/A" if 'dob' is not found
                        gender = str(resume.get('gender', "N/A")).strip()  # Default to "N/A" if 'gender' is not found
                        driving_license_number = str(resume.get('driving_license_number', "N/A") or '').strip() or "N/A"
                        driving_license_number = format_multiline(text=driving_license_number, max_length=50)
                        marital_status = str(resume.get('marital_status', "N/A") or '').strip() or "N/A"                   
                        writer.writerow([
                            name,
                            email,
                            nationality,
                            mobile,
                            work_experience,
                            skills_str,
                            education_str,
                            passport_info,
                            home_language,
                            spoken_languages_str,
                            date_of_birth,
                            gender,
                            driving_license_number,
                            current_residential_address,
                            home_address,
                            marital_status
                        ])
                
                print(f"Successfully converted JSON to CSV at: {csv_file}")
            
            except Exception as e:
                print(f"Error converting JSON to CSV: {str(e)}")
        try:
            # Read the markdown file
            with open(file_path, 'r', encoding='utf-8') as f:
                md_content = f.read()
            cleaned_content1 = re.sub(r'[“”"‘’*#`]', ' ', md_content)
            cleaned_content = re.sub(r'```|markdown', ' ', cleaned_content1)
            # Define the extraction prompt
            extraction_prompt = f"""
            You are a resume parser. The markdown content contains multiple candidate resumes. For each candidate, extract:
            - Full Name
            - Email
            - Nationality
            - Mobile/Phone Number
            - Work Experience(as a string, including years of experience, job titles, and company names don't include career summary)
            - Skills 
            - Education (as a string ,add all education details in the md file)
            - Passport Information
            - Home Language (or mother language)
            - Spoken Languages (as a string, including fields like "languages" or "languages known" or "other languages")
            - Date of Birth 
            - Gender
            - Driving License Number
            - Current Residential Address
            - Home Address(as a string/include home address in contact details)
            - Marital Status

            If any of these fields do not contain a value, represent them as an empty string ("") in the JSON output.
            **Do not guess or add extra content for any field; include only the exact value found in the resume.**
            

            Format the output as a JSON array where each object represents a candidate with these fields:
            - "name": string
            - "email": string
            - "nationality": string
            - "mobile": string
            - "work_experience": string
            - "skills": string
            - "education": string
            - "passport_info": string
            - "home_language": string
            - "spoken_languages": string
            - "date_of_birth": string
            - "gender": string
            - "driving_license_number": string
            - "marital_status": string
            - "current_residential_address": string
            - "home_address": string

            Example format:
            [
                {{
                    "name": "John Doe",
                    "email": "john@email.com",
                    "nationality": "American",
                    "mobile": "+1-555-0123",
                    "work_experience": "5 years, 3 years, 2 years",
                    "skills": "Python, Data Analysis",
                    "education": "BSc in Computer Science, MSc in Data Science",
                    "passport_info": "123456789",
                    "home_language": "English",
                    "spoken_languages": "English, Spanish",
                    "date_of_birth": "1990-01-01",
                    "gender": "Male",
                    "driving_license_number": "D1234567",
                    "current_residential_address": "123 Main St, Anytown, USA",
                    "home_address": "456 Elm St, Anytown, USA",
                    "marital_status": "Single",
                }}
            ]
            Double check each string is terminated with a double quote and a comma.
            Remove single quotes from the output.
            Check if the output is valid JSON.
            Only after validation generate the json.
            **Only generate valid JSON**
            -Important: Invalid JSON will get pernality
            -Avoid adding backticks json
            -Don't add ```json in the response, instead return the json array
            Here's the Markdown content to parse:
            {cleaned_content}

            Return only the JSON array, ensure it's valid JSON format.
            """
            response = self.llm.invoke([{"role": "user", "content": extraction_prompt}]) 
            json_content = response.content.strip()
            try:
                parsed_json = json.loads(json_content)
                
                print("JSON is valid.")
            except json.JSONDecodeError as e:
                print(f"Invalid JSON: {str(e)}")
                return  # Exit the function if JSON is invalid
            
            # Convert parsed_json to a JSON string if it's a list
            print(f"parsed json============>>>>>>> {parsed_json}")
            json_string = json.dumps(parsed_json)  # Convert list to JSON string
            
            # Convert JSON to CSV right here
            json_to_csv(self=self, json_content=json_string)  # Pass the JSON string to the function
            
            
        except Exception as e:
            print(f"Error processing file: {str(e)}")

    def upload_to_s3(self, file_path: str, object_name: str = None) -> Optional[str]:
        """Upload a file to S3 bucket and return the URL"""
        if not self.s3_client or not self.bucket_name:
            logger.warning("S3 credentials not provided. Skipping upload.")
            return None

        # If object_name not provided, use the file name
        if object_name is None:
            object_name = os.path.basename(file_path)

        try:
            # Upload file with ACL header
            extra_args = {
                'ACL': 'public-read',  # Makes the file publicly readable
                'ContentType': 'text/csv'  # Sets the content type for CSV files
            }
            self.s3_client.upload_file(
                file_path, 
                self.bucket_name, 
                object_name,
                ExtraArgs=extra_args
            )
            # Generate the URL for the uploaded file
            url = f"{self.aws_url}/{object_name}"
            return url
        except ClientError as e:
            logger.error(f"Error uploading to S3: {str(e)}")
            return None

    def query_csv_file(self):
        # Use asyncio to run the async operations
        import asyncio
        
        try:
            # Create an event loop if one doesn't exist
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Run the async operations
            results = loop.run_until_complete(self.process_multiple_files())
            
            # Rest of your code remains the same
            print("results==========>>>>>>>>>>>>>>>>>", results)
            
            md_files = list(Path(self.output_dir).glob("*.md"))
            if not md_files:
                print("❌ No markdown files were generated. Processing may have failed.")
                return "❌ No markdown files were generated. Processing may have failed."
            
            for md_file in md_files:
                self.convert_md_to_json(str(md_file))
                if os.path.exists(md_file):
                    os.remove(md_file)
            
            total_resumes = sum(len(file_results) for file_results in results.values())
            print(f"Total resumes processed: {total_resumes}")
            
            csv_path = Path(self.output_dir) / f"{str(self.current_timestamp)}.csv"
            if csv_path.exists():
                print("📊 CSV generated successfully.")
                # Upload to S3 if credentials are provided
                s3_url = self.upload_to_s3(str(csv_path))
                if s3_url:
                    print(f"📤 File uploaded to S3: {s3_url}")
                    if os.path.exists(csv_path):
                        os.remove(csv_path)
                    return s3_url
                if os.path.exists(csv_path):
                    os.remove(csv_path)
                return "❌ No CSV file found."
            
            print("❌ No CSV file found.")
            return "❌ No CSV file found."
            
        except Exception as e:
            print(f"Error in query_csv_file: {str(e)}")
            return f"Error processing files: {str(e)}"
