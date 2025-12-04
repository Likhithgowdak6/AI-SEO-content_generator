# main.py - Enhanced API-Driven Property Content Generator with FAQ Generation (Part 1)
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
import os
from datetime import datetime
import json
import re
import requests
import logging
from bs4 import BeautifulSoup
import random

# New imports for retry/backoff and OpenAI
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from openai import OpenAI

# Import review generator
try:
    from app import generate_reviews_from_text
except ImportError:
    print("⚠️  app.py not found. Review generation will be skipped.")
    generate_reviews_from_text = None

# Import content enhancer
try:
    from loc_build import enhance_property_content
except ImportError:
    print("⚠️  loc_build.py not found. Content enhancement will be skipped.")
    enhance_property_content = None

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Property Content Generator API - Automated with FAQ",
    description="Receives data via POST, generates SEO content + reviews + FAQs, sends back automatically",
    version="7.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============= NAMES DATABASE =============

INDIAN_FIRST_NAMES = [
    "Aabha","Aadhya","Aakash","Aakriti","Aamir","Aanchal","Aaradhya","Aarav",
    "Aarti","Aaryan","Aayush","Abha","Abhay","Abhinav","Abhishek","Aditi",
    "Aditya","Aishwarya","Ajay","Akanksha","Akash","Akhilesh","Alka","Amar",
    "Amisha","Amit","Amitabh","Amrita","Amrish","Anamika","Anand","Ananya",
    "Anchal","Anil","Anita","Anjali","Anju","Ankita","Ankit","Anmol","Ansh",
    "Anshika","Anubhav","Anuj","Anup","Anupam","Anurag","Aparna","Aradhana",
    "Arjun","Arpita","Arti","Arvind","Aryan","Ashish","Ashok","Ashutosh",
    "Asmita","Atul","Avani","Ayesha","Ayush","Babita","Baldev","Balkrishna",
    "Bansi","Bhagwan","Bhanu","Bharat","Bharti","Bhavana","Bhavya","Bhola",
    "Bhuvan","Bijendra","Bimla","Bina","Bindu","Chetan","Chhavi","Daljeet",
    "Damini","Darshan","Deepti","Deepak","Deepali","Deepansh","Dev","Devansh",
    "Devika","Dhananjay","Dheeraj","Diksha","Dinesh","Divya","Durga","Ekta",
    "Faisal","Farhan","Gajendra","Ganga","Gauri","Geeta","Girish","Gopal",
    "Govind","Gunjan","Hansraj","Harish","Harjeet","Harsha","Harshita",
    "Hemant","Hena","Himanshu","Ila","Imran","Indira","Indu","Ishaan","Isha",
    "Jagdish","Jai","Jaya","Jeet","Jitendra","Juhi","Jyoti","Kabir","Kajal",
    "Kamal","Kamini","Kanchan","Kanha","Karan","Karisma","Kavita","Keshav",
    "Ketan","Khushi","Kirti","Kislay","Komal","Kripa","Krish","Krishna",
    "Kuldeep","Lakhan","Lakshman","Lakshmi","Lata","Latika","Lavanya",
    "Leela","Luv","Madhav","Madhavi","Madhuri","Mahak","Mahi","Mahima",
    "Mahinder","Manas","Maneesh","Mangal","Manish","Manisha","Manju",
    "Meena","Meenal","Meera","Megha","Mihir","Mini","Mohan","Monika",
    "Mukesh","Muskan","Naina","Namita","Nandita","Narendra","Naren","Naveen",
    "Navya","Neelam","Neeraj","Neeta","Neeti","Neha","Nidhi","Nikhil",
    "Nikita","Nilesh","Niranjan","Nirmal","Nitish","Om","Omkara","Pallavi",
    "Pankaj","Pankuri","Pankaja","Param","Pari","Parul","Pawan","Payal",
    "Pooja","Poonam","Prachi","Pradeep","Pragya","Prakash","Pranav",
    "Pranjal","Prashant","Pratibha","Prateek","Preeti","Prem","Priti",
    "Priya","Priyanka","Puja","Puneet","Pushpa","Rahul","Raj","Raja",
    "Rajat","Rajeev","Rajendra","Rajesh","Rajni","Ramakant","Ram",
    "Raman","Ramesh","Rani","Ranjan","Rashmi","Ravi","Ravindra","Reena",
    "Rekha","Renuka","Rhea","Richa","Riddhi","Rina","Rishi","Rita","Ritika",
    "Rohit","Ruchi","Sagar","Sahil","Sakshi","Salman","Sameer","Sandhya",
    "Sangeeta","Sanjay","Sanket","Sanya","Sapna","Sara","Sarita","Saroj",
    "Sarthak","Sarvesh","Satish","Savitri","Seema","Shaurya","Sheela",
    "Sheetal","Shikha","Shilpa","Shiva","Shivangi","Shivani","Shreya",
    "Shrishti","Shubham","Shweta","Simran","Sindhu","Smita","Sneha","Sonali",
    "Sonia","Soniya","Sourabh","Sudha","Suhana","Sujata","Suman","Sundar",
    "Sunil","Sunita","Suraj","Suresh","Swati","Tarun","Tanya","Teena",
    "Trisha","Tulsi","Uma","Umesh","Urvi","Vaibhav","Vaishali","Varsha",
    "Varun","Vasudha","Veda","Veena","Vicky","Vidhi","Vidya","Vihan",
    "Vijay","Vijeta","Vikas","Vimal","Vinay","Vinod","Vipin","Vishal",
    "Vishnu","Vishwam","Vivek","Yash","Yogesh",
    "Rakesh","Manjunath","Prajwal","Harsha","Keerthi","Anitha","Rohith","Chandan",
    "Sharath","Rakshit","Yogesh","Kiran","Nandan","Vishal","Lokesh","Raghavendra",
    "Narayan","Sudeep","Srinivas","Deekshith","Ganesh","Mahesh","Ramesh","Venkatesh",
    "Yatish","Chethan","Aravind","Puneeth","Basavaraj","Mallikarjun","Ravikiran",
    "Uday","Rajkumar","Sohail","Sharan","Gowtham","Sathish","Madhu","Sharadha",
    "Nandini","Namratha","Chaithra","Latha","Roopa","Deepa","Meghana","Harini",
    "Kavya","Ranjitha","Sahana","Prarthana","Geetha","Pavitra","Sushma",
    "Sreeja","Nayana","Suchitra","Revathi","Jeevitha","Rachana","Pramila",
    "Bhagya","Anagha","Anusree","Hemalatha","Savitha","Sangeetha","Madhuri",
    "Sandhya","Keerthana","Shashank","Jayanth","Chiranjeevi","Rakshith",
    "Sudeepth","Prajna","Vaishnavi","Shree","Chaitanya","Tejas","Anirudh",
    "Samarth","Anoop","Sanath","Kousthubh","Rohin","Nitin","Akarsh",
    "Yeshwanth","Sujith","Sharanraj","Bharath","Arun","Rajath","Yogendra",
    "Chandana","Niranjan","Jnanesh","Dhanush","Kruthika","Sharmila","Mridula",
    "Supriya","Deepthi","Sahithi","Ishita"
]

# ============= CONFIGURATION =============

# OpenAI Configuration
OPENAI_API_KEY = "YOUR_OPENAI_KEY"

# Company callback API
COMPANY_CALLBACK_API = "http://192.168.0.144/superadmin/AItasks_Controller/update_Contents"

# ============= UTILITY FUNCTIONS =============

def get_random_name() -> str:
    """Get a random name from the Indian names list"""
    return random.choice(INDIAN_FIRST_NAMES)

def get_unique_names(count: int) -> List[str]:
    """Get unique random names"""
    if count > len(INDIAN_FIRST_NAMES):
        # If we need more names than available, allow duplicates
        return [get_random_name() for _ in range(count)]
    return random.sample(INDIAN_FIRST_NAMES, count)

def strip_html_tags(html_text: str) -> str:
    """Remove HTML tags and clean text"""
    if not html_text:
        return ""
    soup = BeautifulSoup(html_text, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def wrap_in_p_tags(text: str) -> str:
    """Wrap text content in <p> tags, preserving paragraph breaks"""
    if not text:
        return ""
    
    paragraphs = text.split('\n\n')
    wrapped = []
    
    for para in paragraphs:
        para = para.strip()
        if para:
            para = para.replace('\n', ' ')
            wrapped.append(f"<p>{para}</p>")
    
    return '\n'.join(wrapped)

def calculate_content_richness(text: str) -> int:
    """Calculate how rich/detailed the content is (word count)"""
    if not text:
        return 0
    clean_text = strip_html_tags(text)
    return len(clean_text.split())

def is_content_sufficient(text: str, min_words: int = 150) -> bool:
    """Check if content is detailed enough"""
    word_count = calculate_content_richness(text)
    return word_count >= min_words

def get_fallback_seo_text_from_payload(body_data: Dict[str, Any]) -> str:
    """Extract fallback description from payload"""
    try:
        prop = body_data.get('prop_info', [{}])[0]
        candidates = [
            prop.get('property_description') if isinstance(prop, dict) else None,
            prop.get('Property_LocalityDiscription') if isinstance(prop, dict) else None,
            prop.get('LocalityDiscription') if isinstance(prop, dict) else None,
        ]
        for c in candidates:
            if c:
                text = strip_html_tags(c)
                if text:
                    return text
    except Exception:
        pass
    return "Brief property overview not available. Please check property data."

# ============= INPUT MODELS =============

class PropInfo(BaseModel):
    propertyID: Optional[str] = None
    propertyName: str
    city_name: Optional[str] = None
    locality_name: Optional[str] = None
    localityID: Optional[str] = None
    LocalityDiscription: Optional[str] = None
    Property_LocalityDiscription: Optional[str] = None
    BuilderName: Optional[str] = None
    BuilderID: Optional[str] = None
    Status: Optional[str] = None
    bhk: Optional[str] = None
    min_price: Optional[str] = None
    max_price: Optional[str] = None

class BasicDetails(BaseModel):
    dimension: Optional[str] = None
    total_apartments: Optional[str] = None
    area_min: Optional[str] = None
    area_max: Optional[str] = None
    PossessionDate: Optional[str] = None
    propertyType: Optional[str] = None
    RERA_ID: Optional[str] = None
    RegionName: Optional[str] = None

class Amenity(BaseModel):
    PropertyId: Optional[str] = None
    Name: str
    ImgPath: Optional[str] = None

class Highlight(BaseModel):
    highlight_point: Optional[str] = None

class DeveloperInfo(BaseModel):
    BuilderName: Optional[str] = None
    BuilderID: Optional[str] = None
    property_count: Optional[str] = None
    founded_year: Optional[str] = None
    builder_description: Optional[str] = Field(None, alias='builder_listing_desc')
    builder_data_discription: Optional[str] = Field(None, alias='builder_details_desc')
    
    class Config:
        populate_by_name = True  # Allows both the field name and alias to work
class IncomingPropertyData(BaseModel):
    status: Optional[str] = None
    result: Optional[str] = None
    prop_info: List[PropInfo]
    basic_details: List[BasicDetails]
    amenities: List[Amenity]
    highlights: Optional[List[Highlight]] = []
    developer_info: Optional[List[DeveloperInfo]] = []

# ============= OPENAI CLIENT =============

openai_client = OpenAI(api_key=OPENAI_API_KEY)

def generate_with_openai(prompt: str, max_tokens: int = 16000, temperature: float = 0.7) -> str:
    """Generate content using OpenAI GPT-4o-mini with retry logic"""
    max_attempts = 5
    base_backoff = 1.0
    
    for attempt in range(1, max_attempts + 1):
        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            generated_text = response.choices[0].message.content
            logger.info(f"✅ OpenAI generation successful (attempt {attempt})")
            return generated_text
            
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"OpenAI request failed (attempt {attempt}/{max_attempts}): {error_msg}")
            
            if "rate_limit" in error_msg.lower() or "429" in error_msg:
                if attempt == max_attempts:
                    raise RuntimeError(f"OpenAI API rate limit exceeded: {error_msg}")
                sleep_time = base_backoff * (2 ** (attempt - 1)) + (0.1 * attempt)
                logger.info(f"⏳ Rate limited. Waiting {sleep_time:.2f}s before retry...")
                time.sleep(sleep_time)
            else:
                if attempt == max_attempts:
                    raise RuntimeError(f"OpenAI API error: {error_msg}")
                time.sleep(base_backoff * (2 ** (attempt - 1)))
    
    raise RuntimeError("OpenAI generation failed after all retries")

# ============= DATA TRANSFORMER =============

class DataTransformer:
    """Converts company format to internal format with content richness analysis"""
    
    @staticmethod
    def transform(incoming: IncomingPropertyData) -> Dict[str, Any]:
        prop = incoming.prop_info[0] if incoming.prop_info else PropInfo(propertyName="Unknown")
        basic = incoming.basic_details[0] if incoming.basic_details else BasicDetails()
        dev = incoming.developer_info[0] if incoming.developer_info else None
        
        amenity_names = []
        if incoming.amenities:
            amenity_names = [a.Name for a in incoming.amenities if a.Name]
        
        highlight_points = []
        if incoming.highlights:
            highlight_points = [h.highlight_point for h in incoming.highlights if h.highlight_point]
        
        price_range = None
        if prop.min_price and prop.max_price:
            try:
                min_p = float(prop.min_price) / 10000000
                max_p = float(prop.max_price) / 10000000
                price_range = f"₹ {min_p:.2f} Cr - {max_p:.2f} Cr"
            except:
                pass
        
        area_range = None
        if basic.area_min and basic.area_max:
            area_range = f"{basic.area_min} - {basic.area_max} sq.ft"
        
        locality_desc = None
        locality_needs_generation = True
        
        for field in [prop.Property_LocalityDiscription, prop.LocalityDiscription]:
            if field:
                clean_text = strip_html_tags(field)
                if is_content_sufficient(clean_text, min_words=150):
                    locality_desc = clean_text
                    locality_needs_generation = False
                    logger.info(f"✅ Sufficient locality description found ({calculate_content_richness(field)} words)")
                    break
        
        developer_desc = None
        developer_needs_generation = True
        
        if dev:
            for field in [dev.builder_data_discription, dev.builder_description]:
                if field:
                    clean_text = strip_html_tags(field)
                    if is_content_sufficient(clean_text, min_words=100):
                        developer_desc = clean_text
                        developer_needs_generation = False
                        logger.info(f"✅ Sufficient developer description found ({calculate_content_richness(field)} words)")
                        break
        
        transformed = {
            "propertyID": prop.propertyID,
            "project_name": prop.propertyName,
            "builder": prop.BuilderName or (dev.BuilderName if dev else None),
            "BuilderID": prop.BuilderID or (dev.BuilderID if dev else None),
            "localityID": prop.localityID,
            "location": f"{prop.locality_name}, {prop.city_name}" if prop.locality_name and prop.city_name else prop.city_name,
            "configurations": [prop.bhk] if prop.bhk else [],
            "area_range": area_range,
            "price_range": price_range,
            "possession_date": basic.PossessionDate,
            "status": prop.Status,
            "rera_id": basic.RERA_ID,
            "total_units": basic.total_apartments,
            "amenities": amenity_names,
            "highlights": highlight_points,
            "features": [],
            "location_data": [],
            "locality_description": locality_desc,
            "locality_needs_generation": locality_needs_generation,
            "developer_description": developer_desc,
            "developer_needs_generation": developer_needs_generation,
            "developer_founded": dev.founded_year if dev else None,
            "developer_project_count": dev.property_count if dev else None
        }
        
        return transformed

# ============= FAQ GENERATION =============

def create_faq_prompt(data: Dict[str, Any], seo_content: str) -> str:
    """Create prompt for FAQ generation"""
    
    prompt = f"""You are an expert real estate FAQ generator for Homes247.in portal.

Based on the property information below, generate 8-10 realistic FAQs that potential buyers would ask.

PROPERTY DATA:
Project: {data['project_name']}
Builder: {data['builder'] or 'Not specified'}
Location: {data['location'] or 'Not specified'}
Configurations: {', '.join(data['configurations']) if data['configurations'] else 'Not specified'}
Area: {data['area_range'] or 'Not specified'}
Price: {data['price_range'] or 'Not specified'}
Possession: {data['possession_date'] or 'Not specified'}
Status: {data['status'] or 'Not specified'}
RERA: {data['rera_id'] or 'Not specified'}
Amenities: {', '.join(data['amenities'][:15]) if data['amenities'] else 'Not specified'}

SEO CONTENT SUMMARY:
{seo_content[:1000]}

INSTRUCTIONS:
1. Generate 8-10 FAQs covering these categories:
   - Location (connectivity, neighborhood, nearby facilities)
   - Configuration (BHK availability, spaciousness)
   - Status (specific amenity questions, staff, charges)
   - Possession (timeline, delays,)
   - Price (starting price, payment plans, home loans)
   - Other (security features, neighborhood safety)
   - Home Loans (appreciation potential, rental demand, contact homes247 for loan)

2. Each FAQ must have:
   - A clear, natural question
   - 1-2 realistic answers (some FAQs can have 2 answers with slightly different perspectives)
   - Category label

3. Make questions and answers natural and conversational
4. Base answers on the actual property data provided
5. DO NOT make up information not present in the data
6. If specific data is not available, give general but realistic answers

OUTPUT FORMAT (JSON only, no markdown):
[
  {{
    "question": "Your question here?",
    "answer_count": 1,
    "answers_text": ["First answer here"],
    "category": "Location"
  }},
  {{
    "question": "Another question?",
    "answer_count": 2,
    "answers_text": ["First perspective answer", "Second perspective answer"],
    "category": "Price"
  }}
]

Generate 8-10 FAQs now in JSON format only:"""

    return prompt

def generate_faqs(data: Dict[str, Any], seo_content: str) -> List[Dict[str, Any]]:
    """Generate FAQs using OpenAI and format with random names"""
    try:
        prompt = create_faq_prompt(data, seo_content)
        
        logger.info("🔄 Generating FAQs with OpenAI...")
        generated_text = generate_with_openai(prompt, max_tokens=3000, temperature=0.8)
        
        # Clean the response
        generated_text = generated_text.strip()
        if generated_text.startswith("```json"):
            generated_text = generated_text[7:]
        if generated_text.startswith("```"):
            generated_text = generated_text[3:]
        if generated_text.endswith("```"):
            generated_text = generated_text[:-3]
        generated_text = generated_text.strip()
        
        # Parse JSON
        faqs_raw = json.loads(generated_text)
        
        # Format FAQs with random names
        formatted_faqs = []
        
        for faq in faqs_raw:
            question = faq.get('question', '')
            answers_text = faq.get('answers_text', [])
            category = faq.get('category', 'General')
            
            if not question or not answers_text:
                continue
            
            # Get unique names for this FAQ
            names_needed = len(answers_text) + 1  # +1 for question asker
            unique_names = get_unique_names(names_needed)
            
            question_asker = unique_names[0]
            answer_givers = unique_names[1:]
            
            # Format answers
            formatted_answers = []
            for idx, answer_text in enumerate(answers_text):
                formatted_answers.append({
                    "first_name": answer_givers[idx],
                    "answer": answer_text
                })
            
            formatted_faq = {
                "question": question,
                "answers": formatted_answers,
                "first_name": question_asker,
                "category": category
            }
            
            formatted_faqs.append(formatted_faq)
        
        logger.info(f"✅ Generated {len(formatted_faqs)} FAQs")
        return formatted_faqs
        
    except Exception as e:
        logger.error(f"❌ FAQ generation failed: {str(e)}")
        return []

# ============= ENHANCED PROMPT BUILDER =============

def create_optimized_prompt(data: Dict[str, Any]) -> str:
    """Create SEO-optimized prompt based on content availability"""
    
    locality_instruction = ""
    if data['locality_needs_generation']:
        locality_instruction = """
 LOCATION 
Generate 180-220 words about the location:
- Focus on connectivity and nearby areas
- Mention growth potential and livability
- Highlight infrastructure and accessibility
- 2-3 paragraphs"""
    else:
        locality_instruction = f"""
 LOCATION 
The following locality information is provided. RESTRUCTURE it for SEO optimization (180-220 words):
- Make it engaging and informative
- Remove redundant information and HTML tags
- Focus on key benefits, connectivity, and growth
- Highlight nearby IT hubs, schools, hospitals if mentioned
- Keep it 2-3 well-structured paragraphs

PROVIDED LOCALITY INFO:
{data['locality_description'][:1500]}"""

    developer_instruction = ""
    if data['developer_needs_generation']:
        developer_instruction = """
 ABOUT THE DEVELOPER
Generate 180-220 words about the developer:
- Company background and founding year
- Experience and expertise in real estate
- Key achievements and completed projects
- Quality standards and customer satisfaction
- Unique selling points
- 2-3 comprehensive paragraphs"""
    else:
        developer_instruction = f"""
 ABOUT THE DEVELOPER 
The following developer information is provided. RESTRUCTURE it for SEO optimization (180-220 words):
- Create a comprehensive developer profile
- Remove HTML tags and redundant information
- Focus on: company history, experience, achievements, quality standards
- Include specific numbers and facts (project count, area developed, experience years)
- Highlight unique strengths and customer satisfaction
- Make it professional and engaging
- 2-3 well-structured paragraphs

PROVIDED DEVELOPER INFO:
{data['developer_description'][:1500]}

Additional Info:
- Founded: {data.get('developer_founded', 'Not specified')}
- Total Projects: {data.get('developer_project_count', 'Not specified')}"""

    highlights_instruction = ""
    if data['highlights']:
        highlights_instruction = f"""
 HIGHLIGHTS 
The following highlights are provided. Present them in engaging format (120-140 words):
{chr(10).join(['- ' + h for h in data['highlights'][:10]])}

Format as 8-10 concise bullet points with benefit-focused descriptions."""
    else:
        highlights_instruction = """
 HIGHLIGHTS 
Based on amenities and available data, create 8-10 compelling highlights (120-140 words):
- Focus on unique selling points
- Format: "Feature name for benefit"
- Keep concise and impactful"""

    prompt = f"""You are an expert SEO content writer for Homes247.in real estate portal.

Generate SEO-optimized property page content for: {data['project_name']}

AVAILABLE DATA:
Project: {data['project_name']}
Builder: {data['builder'] or 'Not specified'}
Location: {data['location'] or 'Not specified'}
Configurations: {', '.join(data['configurations']) if data['configurations'] else 'Not specified'}
Area: {data['area_range'] or 'Not specified'}
Price: {data['price_range'] or 'Not specified'}
Possession: {data['possession_date'] or 'Not specified'}
Status: {data['status'] or 'Not specified'}
RERA: {data['rera_id'] or 'Not specified'}
Units: {data['total_units'] or 'Not specified'}
Amenities: {', '.join(data['amenities'][:20]) if data['amenities'] else 'Not specified'}

CRITICAL RULES:
1. For sections with PROVIDED content - RESTRUCTURE for SEO, expand if needed, but keep it informative
2. For sections marked "Generate" - Create engaging original content
3. ONLY use data provided above - NO hallucinations
4. If data says "Not specified", SKIP that information entirely
5. Never write "coming soon", "will be updated", "not mentioned"
6. Write naturally - if information is missing, don't include that point
7. Each section must be comprehensive and well-detailed
8. Remove ALL HTML tags, keep only clean text

OUTPUT FORMAT:

 OVERVIEW 
Project Name: {data['project_name']}
Builder: {data['builder'] or '[Skip this line]'}
Location: {data['location'] or '[Skip this line]'}
Configurations: {', '.join(data['configurations']) if data['configurations'] else '[Skip this line]'}
Area Range: {data['area_range'] or '[Skip this line]'}
Price Range: {data['price_range'] or '[Skip this line]'}
Possession: {data['possession_date'] or data['status'] or '[Skip this line]'}
RERA ID: {data['rera_id'] or '[Skip this line]'}

(Remove any lines that say [Skip this line])

 ABOUT 
Write 200-250 words describing the PROJECT (not the developer):
- Start with: "{data['project_name']} by {data['builder'] or 'the developer'} is..."
- Focus on: what makes this project special, location advantages, lifestyle it offers
- Mention configurations and who it's ideal for
- Discuss the living experience and community feel
- Highlight key features like possession status, number of units
- Make it engaging and benefit-focused
- DO NOT include developer/builder information here - that goes in the DEVELOPER section
- 3-4 paragraphs about the PROJECT itself

{highlights_instruction}

 AMENITIES
{'Write 180-220 words about the following amenities:' if data['amenities'] else 'Write 180-220 words about typical modern amenities:'}
{', '.join(data['amenities'][:20]) if data['amenities'] else 'Not specified - use general modern amenities'}
- Group by category: fitness & sports, leisure & entertainment, convenience & services, security & safety
- Describe each category with 2-3 sentences explaining the benefits
- 3-4 paragraphs with rich descriptions
- Make it lifestyle-focused, not just a list

{locality_instruction}

{developer_instruction}

 SPECIFICATIONS 
Write 80-100 words about unit specifications:
- List area ranges for each configuration if available
- Mention total number of units and towers if specified
- Include possession date and RERA details
- Keep it organized and easy to read
- Format as short, clear sentences

 WHO SHOULD BUY THIS 
(Required - 200-250 words total)

**Ideal for Families:**
Write 3-4 sentences explaining why families should consider this property.
Focus on: space, amenities for children, safety, community, schools nearby.

**Perfect for Working Professionals:**
Write 3-4 sentences explaining the benefits for working professionals.
Focus on: location, connectivity to IT hubs, modern amenities, lifestyle.

**Smart Investment Opportunity:**
Write 3-4 sentences about investment potential.
Focus on: location growth, appreciation potential, rental demand, builder reputation.

IMPORTANT REMINDERS:
- ABOUT section = About the PROJECT only (200-250 words)
- ABOUT THE DEVELOPER section = Separate detailed section about builder (180-220 words)
- Remove ALL HTML tags from restructured content
- Make each section comprehensive and detailed
- No generic or vague statements

Generate the complete content now."""

    return prompt

# ============= CONTENT GENERATOR =============

async def generate_seo_content(data: Dict[str, Any]) -> str:
    """Generate SEO content using OpenAI GPT-4o-mini with intelligent restructuring"""
    try:
        prompt = create_optimized_prompt(data)
        
        logger.info(f"🔄 Content generation mode (OpenAI GPT-4o-mini):")
        logger.info(f"   - Locality: {'RESTRUCTURE' if not data['locality_needs_generation'] else 'GENERATE'}")
        logger.info(f"   - Developer: {'RESTRUCTURE' if not data['developer_needs_generation'] else 'GENERATE'}")
        
        generated_text = generate_with_openai(prompt, max_tokens=16000, temperature=0.7)
        
        generated_text = re.sub(r'\|\s*\|', '', generated_text)
        generated_text = re.sub(r'\|\s*---\s*\|', '', generated_text)
        generated_text = re.sub(r'\[Skip this line\].*?\n', '', generated_text)
        
        phrases_to_remove = [
            "coming soon", "will be updated soon", "to be updated",
            "details will be shared", "information not available"
        ]
        for phrase in phrases_to_remove:
            generated_text = re.sub(phrase, '', generated_text, flags=re.IGNORECASE)
        
        return generated_text
        
    except Exception as e:
        raise RuntimeError(f"Content generation failed: {str(e)}")

# ============= REVIEW GENERATOR =============

def generate_reviews(seo_content: str, count: int = 10) -> List[Dict[str, Any]]:
    """Generate reviews using app.py"""
    if generate_reviews_from_text is None:
        logger.warning("Review generator not available. Returning empty reviews.")
        return []
    
    try:
        json_str, reviews = generate_reviews_from_text(seo_content, count)
        return reviews
    except Exception as e:
        logger.error(f"Review generation failed: {str(e)}")
        return []

# ============= FORMAT OUTPUT =============

# ============= FORMAT OUTPUT =============

def format_output(
    transformed_data: Dict[str, Any],
    seo_content: str,
    reviews: List[Dict[str, Any]],
    faqs: List[Dict[str, Any]],
    enhanced_content: Optional[Dict[str, Any]],
    error_note: Optional[str] = None
) -> Dict[str, Any]:
    """Format output in the exact required format"""
    
    seo_content_html = wrap_in_p_tags(seo_content)
    
    locality_desc = None
    prop_locality_desc = None
    builder_desc_details = None
    builder_desc_listing = None
    
    if enhanced_content:
        # Wrap enhanced content fields in <p> tags
        locality_desc_raw = enhanced_content.get('LocalityDiscription')
        prop_locality_desc_raw = enhanced_content.get('Property_LocalityDiscription')
        builder_desc_details_raw = enhanced_content.get('builder_data_discription')
        builder_desc_listing_raw = enhanced_content.get('builder_description')
        
        # Apply wrap_in_p_tags to each field if it exists
        locality_desc = wrap_in_p_tags(locality_desc_raw) if locality_desc_raw else None
        prop_locality_desc = wrap_in_p_tags(prop_locality_desc_raw) if prop_locality_desc_raw else None
        builder_desc_details = wrap_in_p_tags(builder_desc_details_raw) if builder_desc_details_raw else None
        builder_desc_listing = wrap_in_p_tags(builder_desc_listing_raw) if builder_desc_listing_raw else None
    
    output = {
        "propid": transformed_data.get('propertyID'),
        "prop_name": transformed_data.get('project_name'),
        "prop_desc": seo_content_html,
        "localityid": transformed_data.get('localityID'),
        "locality_desc": locality_desc,
        "prop_locality_desc": prop_locality_desc,
        "builderid": transformed_data.get('BuilderID'),
        "builder_desc_details": builder_desc_details,
        "builder_desc_listing": builder_desc_listing,
        "reviews": reviews,
        "FAQ": faqs,
        "error_note": error_note
    }
    
    return output
# ============= CALLBACK SENDER =============

async def send_to_company_api(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Send generated content back to company API as form data"""
    result: Dict[str, Any] = {
        "ok": False,
        "status_code": None,
        "response_text": None,
        "error": None,
    }

    try:
        form_payload = payload.copy()
        if 'reviews' in form_payload and isinstance(form_payload['reviews'], list):
            form_payload['reviews'] = json.dumps(form_payload['reviews'])
        if 'FAQ' in form_payload and isinstance(form_payload['FAQ'], list):
            form_payload['FAQ'] = json.dumps(form_payload['FAQ'])
        
        for key, value in form_payload.items():
            if value is None:
                form_payload[key] = ''
        
        payload_preview = str(form_payload)[:1000]
        logger.info(f"📤 Sending form data to {COMPANY_CALLBACK_API}")
        logger.info(f"📦 Form data preview:\n{payload_preview}...")
        logger.info(f"📊 Form data keys: {list(form_payload.keys())}")
        logger.info(f"📏 Payload size: {len(str(form_payload))} bytes")

        response = requests.post(
            COMPANY_CALLBACK_API,
            data=form_payload,
            timeout=30
        )

        logger.info(f"📨 Response status code: {response.status_code}")
        logger.info(f"📨 Response text: {response.text[:500]}")

        result["status_code"] = response.status_code
        result["response_text"] = response.text

        if 200 <= response.status_code < 300:
            logger.info(f"✅ Successfully sent results to company API: {COMPANY_CALLBACK_API}")
            result["ok"] = True
        else:
            logger.error(f"❌ Non-2xx response from company API: {response.status_code}")
            result["error"] = f"Non-2xx status: {response.status_code}"

        return result

    except requests.exceptions.Timeout:
        logger.error(f"❌ Timeout sending to company API: {COMPANY_CALLBACK_API}")
        result["error"] = "timeout"
        return result
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Request failed to company API: {str(e)}")
        result["error"] = str(e)
        return result
    except Exception as e:
        logger.error(f"❌ Failed to send to company API: {str(e)}")
        result["error"] = str(e)
        return result

# ============= BACKGROUND PROCESSOR =============

async def process_data_background(body_data: Any, raw_body: bytes):
    """Process data in background and handle errors"""
    try:
        if isinstance(body_data, dict):
            try:
                incoming_data = IncomingPropertyData(**body_data)
                logger.info("✅ Data validation successful")
                
                transformed_data = DataTransformer.transform(incoming_data)
                logger.info("✅ Data transformed successfully")
                
                logger.info("🔄 Enhancing locality and developer content...")
                enhanced_content = None
                if enhance_property_content:
                    enhanced_content = enhance_property_content(body_data)
                
                logger.info("🔄 Generating SEO content with OpenAI...")
                seo_content = None
                seo_generation_error = None
                try:
                    seo_content = await generate_seo_content(transformed_data)
                    logger.info("✅ SEO content generated")
                except Exception as e:
                    seo_generation_error = str(e)
                    logger.error(f"❌ Content generation failed: {seo_generation_error}")
                    try:
                        seo_content = get_fallback_seo_text_from_payload(body_data)
                        logger.info("⚠️ Using fallback SEO content (from provided descriptions).")
                    except Exception as e2:
                        logger.error(f"❌ Failed to build fallback SEO content: {e2}")
                        seo_content = f"{transformed_data.get('project_name')} - Brief description not available."
                
                logger.info("🔄 Generating reviews...")
                reviews = []
                try:
                    reviews = generate_reviews(seo_content, count=10)
                    logger.info(f"✅ Generated {len(reviews)} reviews")
                except Exception as e:
                    logger.error(f"❌ Review generation failed: {e}")
                    reviews = []
                
                logger.info("🔄 Generating FAQs...")
                faqs = []
                try:
                    faqs = generate_faqs(transformed_data, seo_content)
                    logger.info(f"✅ Generated {len(faqs)} FAQs")
                except Exception as e:
                    logger.error(f"❌ FAQ generation failed: {e}")
                    faqs = []
                
                formatted_output = format_output(
                    transformed_data,
                    seo_content,
                    reviews,
                    faqs,
                    enhanced_content,
                    error_note=seo_generation_error
                )
                
                logger.info("✅ Output formatted successfully")
                
                callback_result = await send_to_company_api(formatted_output)
                logger.info(f"📡 Callback result: {callback_result}")
                
            except Exception as validation_error:
                logger.error(f"❌ Validation error: {str(validation_error)}")
                logger.error(f"📦 Data received: {json.dumps(body_data, indent=2)}")
                minimal_payload = {
                    "propid": body_data.get('prop_info', [{}])[0].get('propertyID'),
                    "prop_name": body_data.get('prop_info', [{}])[0].get('propertyName'),
                    "error_note": f"Validation error: {str(validation_error)}"
                }
                try:
                    await send_to_company_api(minimal_payload)
                except Exception as e:
                    logger.error(f"❌ Failed to send minimal payload after validation error: {e}")
                
        else:
            logger.error(f"❌ Invalid data format. Expected JSON object, got: {type(body_data)}")
            logger.error(f"📦 Raw data: {str(raw_body.decode('utf-8'))[:500]}")
            
    except Exception as e:
        logger.error(f"❌ Background processing failed: {str(e)}")
        try:
            minimal_payload = {
                "error_note": f"Background processing failed: {str(e)}",
                "prop_name": body_data.get('prop_info', [{}])[0].get('propertyName') if isinstance(body_data, dict) else None
            }
            await send_to_company_api(minimal_payload)
        except Exception as send_err:
            logger.error(f"❌ Failed to send failure notification: {send_err}")

# ============= MAIN API ENDPOINT =============

from pydantic import ValidationError

@app.post("/process-property", status_code=200)
async def process_property_data(request: Request, background_tasks: BackgroundTasks):
    """MAIN ENDPOINT - Validates incoming data and processes in background"""
    try:
        raw_body = await request.body()

        try:
            body_data = json.loads(raw_body) if raw_body else {}
            logger.info(f"📥 Received data for: {body_data.get('prop_info', [{}])[0].get('propertyName', 'Unknown')}")
        except Exception as e:
            body_str = raw_body.decode('utf-8') if raw_body else ""
            logger.warning(f"⚠️ Could not parse JSON. Raw data: {body_str[:500]}")
            return {
                "status": True,
                "accepted": False,
                "message": "Invalid JSON payload",
                "errors": str(e),
                "timestamp": datetime.now().isoformat()
            }

        request_id = f"req_{int(datetime.now().timestamp() * 1000)}"

        try:
            incoming_data = IncomingPropertyData(**body_data)
            logger.info("✅ Schema validation successful")

            response = {
                "status": True,
                "accepted": True,
                "message": "Request received and data format is valid. Processing in background.",
                "timestamp": datetime.now().isoformat(),
                "request_id": request_id
            }

            background_tasks.add_task(process_data_background, body_data, raw_body)

            return response

        except ValidationError as ve:
            logger.warning(f"❌ Schema validation failed: {ve}")
            return {
                "status": True,
                "accepted": False,
                "message": "Payload did not match required format.",
                "errors": ve.errors(),
                "timestamp": datetime.now().isoformat(),
                "request_id": request_id
            }

    except Exception as e:
        logger.error(f"❌ Unexpected error receiving request: {str(e)}")
        return {
            "status": False,
            "accepted": False,
            "message": "Server error while receiving request.",
            "errors": str(e),
            "timestamp": datetime.now().isoformat(),
            "request_id": f"req_{int(datetime.now().timestamp() * 1000)}"
        }

# ============= MANUAL TRIGGER =============

@app.post("/generate-manual")
async def generate_manual(request: Request):
    """Optional endpoint for manual testing - returns formatted output immediately"""
    try:
        raw_body = await request.body()
        body_data = json.loads(raw_body)
        
        incoming_data = IncomingPropertyData(**body_data)
        transformed_data = DataTransformer.transform(incoming_data)
        
        enhanced_content = None
        if enhance_property_content:
            enhanced_content = enhance_property_content(body_data)
        
        seo_content = None
        seo_generation_error = None
        try:
            seo_content = await generate_seo_content(transformed_data)
        except Exception as e:
            seo_generation_error = str(e)
            logger.error(f"❌ Manual SEO generation failed: {seo_generation_error}")
            seo_content = get_fallback_seo_text_from_payload(body_data)
            logger.info("⚠️ Using fallback SEO content for manual run.")
        
        reviews = generate_reviews(seo_content, count=10)
        faqs = generate_faqs(transformed_data, seo_content)
        
        formatted_output = format_output(
            transformed_data,
            seo_content,
            reviews,
            faqs,
            enhanced_content,
            error_note=seo_generation_error
        )
        
        return formatted_output
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": "Manual processing failed. Check data format."
        }

# ============= HEALTH CHECK =============

@app.get("/")
async def root():
    return {
        "service": "Property Content Generator API - Enhanced with FAQ (OpenAI)",
        "version": "7.0.0",
        "ai_model": "OpenAI GPT-4o-mini",
        "status": "operational",
        "mode": "API-driven with formatted output + FAQs",
        "output_format": {
            "propid": "string",
            "prop_name": "string",
            "prop_desc": "<p>SEO content in paragraph tags</p>",
            "localityid": "string",
            "locality_desc": "string",
            "prop_locality_desc": "string",
            "builderid": "string",
            "builder_desc_details": "string",
            "builder_desc_listing": "string",
            "reviews": "array",
            "FAQ": "array"
        },
        "callback_api": COMPANY_CALLBACK_API
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "ai_provider": "OpenAI",
        "ai_model": "gpt-4o-mini",
        "timestamp": datetime.now().isoformat(),
        "openai_ready": True,
        "review_generator_ready": generate_reviews_from_text is not None,
        "loc_build_ready": enhance_property_content is not None,
        "faq_generator_ready": True,
        "callback_api": COMPANY_CALLBACK_API
    }

@app.post("/process-property-debug")
async def process_property_debug(request: Request):
    """Debug endpoint: runs the full pipeline, sends to callback API"""
    try:
        raw_body = await request.body()
        body_data = json.loads(raw_body)

        incoming_data = IncomingPropertyData(**body_data)
        logger.info("✅ Debug: Schema validation successful")

        transformed_data = DataTransformer.transform(incoming_data)

        enhanced_content = None
        if enhance_property_content:
            enhanced_content = enhance_property_content(body_data)

        seo_content = None
        seo_generation_error = None
        try:
            seo_content = await generate_seo_content(transformed_data)
        except Exception as e:
            seo_generation_error = str(e)
            logger.error(f"❌ Debug SEO generation failed: {seo_generation_error}")
            seo_content = get_fallback_seo_text_from_payload(body_data)
            logger.info("⚠️ Debug: Using fallback SEO content.")

        reviews = generate_reviews(seo_content, count=10)
        faqs = generate_faqs(transformed_data, seo_content)

        formatted_output = format_output(
            transformed_data,
            seo_content,
            reviews,
            faqs,
            enhanced_content,
            error_note=seo_generation_error
        )

        callback_result = await send_to_company_api(formatted_output)

        return {
            "status": True,
            "message": "Debug run completed. See callback_result and payload below.",
            "ai_provider": "OpenAI",
            "ai_model": "gpt-4o-mini",
            "callback_api": COMPANY_CALLBACK_API,
            "callback_result": callback_result,
            "payload": formatted_output,
            "payload_size_bytes": len(json.dumps(formatted_output)),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Debug processing failed: {e}")
        return {
            "status": False,
            "error": str(e),
            "message": "Debug processing failed. Check data format and logs."
        }

@app.post("/test-callback")
async def test_callback(request: Request):
    """Test endpoint to verify what data would be sent to callback API"""
    try:
        raw_body = await request.body()
        body_data = json.loads(raw_body)
        
        incoming_data = IncomingPropertyData(**body_data)
        transformed_data = DataTransformer.transform(incoming_data)
        
        enhanced_content = None
        if enhance_property_content:
            enhanced_content = enhance_property_content(body_data)
        
        seo_content = None
        seo_generation_error = None
        try:
            seo_content = await generate_seo_content(transformed_data)
        except Exception as e:
            seo_generation_error = str(e)
            logger.error(f"❌ Test-callback SEO generation failed: {seo_generation_error}")
            seo_content = get_fallback_seo_text_from_payload(body_data)
            logger.info("⚠️ Using fallback SEO content for test-callback.")
        
        reviews = generate_reviews(seo_content, count=10)
        
        formatted_output = format_output(
            transformed_data,
            seo_content,
            reviews,
            enhanced_content,
            error_note=seo_generation_error
        )
        
        return {
            "message": "This is what would be sent to the callback API",
            "ai_provider": "OpenAI",
            "ai_model": "gpt-4o-mini",
            "callback_api": COMPANY_CALLBACK_API,
            "payload": formatted_output,
            "payload_size_bytes": len(json.dumps(formatted_output)),
            "payload_keys": list(formatted_output.keys()),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "message": "Test callback failed. Check data format."
        }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Enhanced Property Content Generator (OpenAI)...")
    print("🤖 AI Model: OpenAI GPT-4o-mini")
    print("📍 Server: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")
    print(f"📤 Callback API: {COMPANY_CALLBACK_API}")
    print("\n✨ OUTPUT FORMAT:")
    print("   - propid, prop_name, prop_desc (in <p> tags)")
    print("   - localityid, locality_desc, prop_locality_desc")
    print("   - builderid, builder_desc_details, builder_desc_listing")
    print("   - reviews (array)")
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        timeout_keep_alive=180,
        limit_concurrency=10
    )
