# main.py - Enhanced API-Driven Property Content Generator (Part 1)
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator, ValidationError
from typing import List, Optional, Dict, Any
import os
from datetime import datetime
from pathlib import Path
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
from urllib.parse import quote_plus
from openai import OpenAI

# Import review generator
try:
    from app import generate_reviews_from_text
except ImportError:
    print("⚠️  app.py not found. Review generation will be skipped.")
    generate_reviews_from_text = None


# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Property Content Generator API - Enhanced",
    description="Smart content generation with word count validation and conditional generation",
    version="9.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============= WEB SCRAPER (Integrated from loc_build.py) =============

class SimpleGoogleScraper:
    """Handles simple Google scraping - fast and minimal"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def quick_google_search(self, query: str, max_results: int = 2) -> str:
        try:
            encoded_query = quote_plus(query)
            url = f"https://www.google.com/search?q={encoded_query}"
            
            response = self.session.get(url, timeout=5)
            
            if response.status_code != 200:
                logger.warning(f"⚠️ Google returned status {response.status_code}")
                return ""
            
            soup = BeautifulSoup(response.text, 'html.parser')
            snippets = []
            
            search_divs = soup.find_all('div', class_='g')[:max_results]
            
            for div in search_divs:
                try:
                    snippet_elem = div.find('span')
                    if snippet_elem:
                        snippet = snippet_elem.get_text(strip=True)
                        if snippet and len(snippet) > 20:
                            snippets.append(snippet)
                except:
                    continue
            
            result = " ".join(snippets[:2])
            logger.info(f"✅ Google search: {len(result)} chars")
            return result
            
        except Exception as e:
            logger.error(f"❌ Google search failed: {str(e)}")
            return ""
    
    def search_builder_info(self, builder_name: str, city: str = "") -> str:
        query = f"{builder_name} real estate developer"
        if city:
            query += f" {city}"
        
        logger.info(f"🔍 Quick Google search for: {query}")
        return self.quick_google_search(query, max_results=2)

# Initialize scraper globally
web_scraper = SimpleGoogleScraper()

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

GENERATED_DATA_FILE = "generated_content.json"

# ============= CONFIGURATION =============

# OpenAI Configuration
OPENAI_API_KEY = "Your-API-KEY"

# Company callback API
COMPANY_CALLBACK_API = "http://192.168.0.144/superadmin/AItasks_Controller/update_Contents"

# ============= UTILITY FUNCTIONS =============

def get_random_name() -> str:
    """Get a random name from the Indian names list"""
    return random.choice(INDIAN_FIRST_NAMES)

def get_unique_names(count: int) -> List[str]:
    """Get unique random names"""
    if count > len(INDIAN_FIRST_NAMES):
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

def remove_dashes_from_text(text: str) -> str:
    """
    Remove ALL dash symbols (–, -, —) from text including hyphens in words
    """
    if not text:
        return text

    # List of all dash-like characters to remove
    dash_characters = ['-', '–', '—']

    # Remove ALL dash characters everywhere
    for dash in dash_characters:
        text = text.replace(dash, '')

    # Remove any extra spaces created due to dash removal
    text = re.sub(r'\s{2,}', ' ', text)

    return text.strip()

def clean_generated_content(content: str) -> str:
    """
    Clean generated content - remove dashes, markdown, and format properly
    Use this on ALL content before returning to user
    """
    if not content:
        return content
    
    # Remove markdown code blocks
    content = content.strip()
    if content.startswith("```html"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    content = content.strip()
    
    # Remove section headers (### SECTION NAME)
    content = re.sub(r'###\s+[A-Z\s]+\n', '', content)
    
    # Remove dashes
    content = remove_dashes_from_text(content)
    
    # Remove [Skip] lines
    content = re.sub(r'<br>\s*<strong>[^<]+:</strong>\s*\[Skip\]', '', content)
    content = re.sub(r'\[Skip\].*?(?=<br>|</p>|$)', '', content)
    
    # Clean up extra whitespace
    content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
    
    return content.strip()

def save_generated_data(output_data: Dict[str, Any]) -> None:
    """Save generated data to file, replacing previous data if property exists"""
    try:
        file_path = Path(GENERATED_DATA_FILE)
        
        existing_data = {}
        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load existing data: {e}")
                existing_data = {}
        
        prop_id = output_data.get('propid', 'unknown')
        output_data['generated_at'] = datetime.now().isoformat()
        existing_data[prop_id] = output_data
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Saved generated data for property {prop_id} to {GENERATED_DATA_FILE}")
        logger.info(f"📊 Total properties in file: {len(existing_data)}")
        
    except Exception as e:
        logger.error(f"❌ Failed to save generated data: {e}")

def calculate_content_richness(text: str) -> int:
    """Calculate how rich/detailed the content is (word count)"""
    if not text:
        return 0
    clean_text = strip_html_tags(text)
    return len(clean_text.split())

def count_words(text: str) -> int:
    """Count words in text (alias for calculate_content_richness)"""
    return calculate_content_richness(text)

def is_content_sufficient(text: str, min_words: int = 250) -> bool:
    """Check if content is detailed enough"""
    word_count = calculate_content_richness(text)
    logger.info(f"📊 Content word count: {word_count} (minimum required: {min_words})")
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

def clean_html_paragraphs(html_text: str) -> str:
    """Clean HTML text and ensure proper paragraph formatting"""
    if not html_text:
        return ""
    
    # Remove dashes
    html_text = remove_dashes_from_text(html_text)
    
    # Parse HTML
    soup = BeautifulSoup(html_text, 'html.parser')
    
    # Get all text content
    text = soup.get_text(separator='\n\n', strip=True)
    
    # Split into paragraphs and wrap in <p> tags
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    
    # Create clean HTML
    clean_html = '\n'.join([f'<p>{p}</p>' for p in paragraphs])
    
    return clean_html

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
    property_description: Optional[str] = None
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
    builder_listing_desc: Optional[str] = None
    builder_details_desc: Optional[str] = None
    
    class Config:
        populate_by_name = True

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

# main.py - Part 2 (Lines 601-1200)
# Data Transformer with Smart Content Validation

# ============= DATA TRANSFORMER WITH CONTENT VALIDATION =============

class DataTransformer:
    """Converts company format to internal format with smart content validation"""
    
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
        
        # ============= SMART CONTENT VALIDATION =============
        
        # Check LocalityDiscription (250+ words)
        locality_desc = None
        locality_needs_generation = True
        
        if prop.LocalityDiscription:
            word_count = count_words(prop.LocalityDiscription)
            logger.info(f"📊 LocalityDiscription: {word_count} words")
            
            if is_content_sufficient(prop.LocalityDiscription, min_words=250):
                locality_desc = clean_html_paragraphs(prop.LocalityDiscription)
                locality_needs_generation = False
                logger.info(f"✅ Using existing LocalityDiscription ({word_count} words) - NO generation needed")
            else:
                logger.info(f"⚠️ LocalityDiscription insufficient ({word_count} words < 250) - WILL generate")
        else:
            logger.info("⚠️ LocalityDiscription not provided - WILL generate")
        
        # Check Property_LocalityDiscription (250+ words)
        prop_locality_desc = None
        prop_locality_needs_generation = True
        
        if prop.Property_LocalityDiscription:
            word_count = count_words(prop.Property_LocalityDiscription)
            logger.info(f"📊 Property_LocalityDiscription: {word_count} words")
            
            if is_content_sufficient(prop.Property_LocalityDiscription, min_words=250):
                prop_locality_desc = clean_html_paragraphs(prop.Property_LocalityDiscription)
                prop_locality_needs_generation = False
                logger.info(f"✅ Using existing Property_LocalityDiscription ({word_count} words) - NO generation needed")
            else:
                logger.info(f"⚠️ Property_LocalityDiscription insufficient ({word_count} words < 250) - WILL generate")
        else:
            logger.info("⚠️ Property_LocalityDiscription not provided - WILL generate")
        
        # Check property_description (250+ words)
        property_desc = None
        property_needs_generation = True
        
        if basic.property_description:
            word_count = count_words(basic.property_description)
            logger.info(f"📊 property_description: {word_count} words")
            
            if is_content_sufficient(basic.property_description, min_words=250):
                property_desc = clean_html_paragraphs(basic.property_description)
                property_needs_generation = False
                logger.info(f"✅ Using existing property_description ({word_count} words) - NO generation needed")
            else:
                logger.info(f"⚠️ property_description insufficient ({word_count} words < 250) - WILL generate")
        else:
            logger.info("⚠️ property_description not provided - WILL generate")
        
        # Check developer descriptions (250+ words each)
        developer_details_desc = None
        developer_details_needs_generation = True
        
        developer_listing_desc = None
        developer_listing_needs_generation = True
        
        if dev:
            # Check builder_details_desc
            if dev.builder_details_desc:
                word_count = count_words(dev.builder_details_desc)
                logger.info(f"📊 builder_details_desc: {word_count} words")
                
                if is_content_sufficient(dev.builder_details_desc, min_words=250):
                    developer_details_desc = clean_html_paragraphs(dev.builder_details_desc)
                    developer_details_needs_generation = False
                    logger.info(f"✅ Using existing builder_details_desc ({word_count} words) - NO generation needed")
                else:
                    logger.info(f"⚠️ builder_details_desc insufficient ({word_count} words < 250) - WILL generate")
            else:
                logger.info("⚠️ builder_details_desc not provided - WILL generate")
            
            # Check builder_listing_desc
            if dev.builder_listing_desc:
                word_count = count_words(dev.builder_listing_desc)
                logger.info(f"📊 builder_listing_desc: {word_count} words")
                
                if is_content_sufficient(dev.builder_listing_desc, min_words=250):
                    developer_listing_desc = clean_html_paragraphs(dev.builder_listing_desc)
                    developer_listing_needs_generation = False
                    logger.info(f"✅ Using existing builder_listing_desc ({word_count} words) - NO generation needed")
                else:
                    logger.info(f"⚠️ builder_listing_desc insufficient ({word_count} words < 250) - WILL generate")
            else:
                logger.info("⚠️ builder_listing_desc not provided - WILL generate")
        else:
            logger.info("⚠️ Developer info not provided - WILL generate")
        
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
            
            # Existing content (if sufficient)
            "locality_description": locality_desc,
            "locality_needs_generation": locality_needs_generation,
            
            "prop_locality_description": prop_locality_desc,
            "prop_locality_needs_generation": prop_locality_needs_generation,
            
            "property_description": property_desc,
            "property_needs_generation": property_needs_generation,
            
            "developer_details_description": developer_details_desc,
            "developer_details_needs_generation": developer_details_needs_generation,
            
            "developer_listing_description": developer_listing_desc,
            "developer_listing_needs_generation": developer_listing_needs_generation,
            
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
   - Possession (timeline, delays)
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
7. DO NOT use dash symbols (–, -, —) anywhere in questions or answers

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
            
            # CRITICAL: Remove dashes from question and answers
            question = remove_dashes_from_text(question)
            answers_text = [remove_dashes_from_text(ans) for ans in answers_text]
            
            names_needed = len(answers_text) + 1
            unique_names = get_unique_names(names_needed)
            
            question_asker = unique_names[0]
            answer_givers = unique_names[1:]
            
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


# ============= REVIEW GENERATOR =============

def generate_reviews(seo_content: str, count: int = 10) -> List[Dict[str, Any]]:
    """Generate reviews using app.py"""
    if generate_reviews_from_text is None:
        logger.warning("Review generator not available. Returning empty reviews.")
        return []
    
    try:
        # Remove dashes before generating reviews
        clean_content = remove_dashes_from_text(seo_content)
        json_str, reviews = generate_reviews_from_text(clean_content, count)
        
        # Remove dashes from generated reviews
        for review in reviews:
            if 'review' in review:
                review['review'] = remove_dashes_from_text(review['review'])
        
        return reviews
    except Exception as e:
        logger.error(f"Review generation failed: {str(e)}")
        return []
    
# main.py - Part 3 (Lines 1201-1800)
# Smart Prompt Builder with Conditional Generation

# ============= SMART PROMPT BUILDER =============

# Replace the create_optimized_prompt function in your main.py with this version

def create_optimized_prompt(data: Dict[str, Any]) -> str:
    """Create SEO-optimized prompt with strategic keyword repetition"""
    
    # Extract location components
    location = data.get('location', 'Area')
    location_parts = location.split(',') if location else ['Area']
    locality = location_parts[0].strip() if location_parts else 'locality'
    city = location_parts[-1].strip() if len(location_parts) > 1 else ''
    
    # Determine property type
    configurations = data.get('configurations', [])
    if configurations:
        bhk = configurations[0]
        property_type = f"{bhk} apartments" if bhk else "residential apartments"
    else:
        property_type = "residential apartments"
    
    # Create primary keywords
    primary_keyword = f"{property_type} in {locality}"
    secondary_keyword = f"{property_type} near {locality}"
    location_keyword = f"{locality}, {city}" if city else locality
    
    logger.info(f"🎯 Primary keyword: {primary_keyword}")
    logger.info(f"🎯 Secondary keyword: {secondary_keyword}")
    
    # Get web context for developer if needed
    web_context = ""
    if data.get('developer_details_needs_generation') or data.get('developer_listing_needs_generation'):
        try:
            web_context = web_scraper.search_builder_info(
                data.get('builder', 'Developer'),
                city
            )
            time.sleep(0.5)
        except:
            pass
    
    sections_to_generate = []
    prompt = f"""You are an expert SEO content writer for Homes247.in real estate portal.

**CRITICAL SEO INSTRUCTIONS:**
1. Generate 5 COMPLETELY DIFFERENT sections
2. Each section starts with: === SECTION_NAME ===
3. Use PRIMARY KEYWORD "{primary_keyword}" 3-4 times naturally across all sections
4. Use SECONDARY KEYWORD "{secondary_keyword}" 2-4 times naturally
5. Use LOCATION "{location_keyword}" frequently (4-6 times total)
6. NO dash symbols (–, -, —)
7. Use only <p>, <strong>, <br> tags
8. Write in clean HTML paragraphs
9. Keywords should appear naturally, not forced

**PROPERTY DATA:**
Project: {data['project_name']}
Builder: {data.get('builder', 'Developer')}
Location: {location}
Property Type: {property_type}
Configurations: {', '.join(configurations) if configurations else 'Various'}
Area: {data.get('area_range', 'Varies')}
Price: {data.get('price_range', 'Contact for pricing')}

"""
    
    # Section 1: LocalityDiscription (ONLY LOCATION - NO PROPERTY)
    if data['locality_needs_generation']:
        prompt += f"""
=== LOCATION DESCRIPTION ===

Write 250-300 words about {locality} area in {city} ONLY.
DO NOT mention "{data['project_name']}" property name.
DO NOT mention any builder name.

**KEYWORD USAGE (3-4 times in this section):**
- Use "{secondary_keyword}" 2 times
- Use "{location_keyword}" 2-3 times

**Structure:**
<p>Paragraph 1: {locality} is a prominent locality in {city} known for excellent connectivity. Mention "{secondary_keyword}" naturally. Discuss roads, highways, metro stations, and public transport in {locality}...</p>

<p>Paragraph 2: The infrastructure in {locality} makes it ideal for residential living. Mention nearby amenities like schools, hospitals, shopping malls, and IT hubs that make "{secondary_keyword}" highly desirable...</p>

<p>Paragraph 3: Growth potential of {locality} area with upcoming infrastructure projects, metro expansions, and real estate development in {city}...</p>

**REMEMBER:** Use "{secondary_keyword}" naturally 2 times in this section.

"""
        sections_to_generate.append("LOCATION DESCRIPTION")
    
    # Section 2: Property_LocalityDiscription (PROPERTY + LOCATION)
    if data['prop_locality_needs_generation']:
        prompt += f"""
=== PROPERTY LOCALITY DESCRIPTION ===

Write 250-300 words about {data['project_name']} in {locality}.
**CRITICAL:** Use "{primary_keyword}" 2-3 times naturally in this section.

**KEYWORD USAGE (4-5 times in this section):**
- Use "{primary_keyword}" 2-3 times
- Use "{location_keyword}" 3-4 times
- Mention property name 2-3 times

**Structure:**
<p>Paragraph 1: {data['project_name']} in {locality} offers {property_type} that redefine modern living in {city}. These "{primary_keyword}" provide excellent connectivity advantages with proximity to major highways, metro stations, and business districts...</p>

<p>Paragraph 2: Residents of {data['project_name']} benefit from {locality}'s strategic location. The "{primary_keyword}" are surrounded by quality schools, healthcare facilities, and shopping centers. Commuting from {location_keyword} to key areas is seamless...</p>

<p>Paragraph 3: Investing in {data['project_name']} means securing one of the finest "{primary_keyword}" available. The project combines modern amenities with the location benefits of {locality}, making it ideal for families and professionals in {city}...</p>

**REMEMBER:** Use "{primary_keyword}" naturally 2-3 times in this section.

"""
        sections_to_generate.append("PROPERTY LOCALITY DESCRIPTION")
    
    # Section 3: Property Description (FULL PROPERTY DETAILS)
    if data['property_needs_generation']:
        highlights_text = ""
        if data['highlights']:
            highlights_text = '<br>'.join([h for h in data['highlights'][:10]])
        else:
            highlights_text = "Create 8-10 bullet points about property features"
        
        prompt += f"""
=== PROPERTY DESCRIPTION ===

**KEYWORD USAGE (2-3 times in ABOUT section):**
- Use "{primary_keyword}" 1-2 times in ABOUT section
- Use property name 2-3 times throughout
- Use "{location_keyword}" 2-3 times

<p><strong>OVERVIEW</strong><br>
<strong>Project Name:</strong> {data['project_name']}<br>
<strong>Builder:</strong> {data['builder'] or 'Developer name'}<br>
<strong>Location:</strong> {location}<br>
<strong>Configurations:</strong> {', '.join(configurations) if configurations else 'Various'}<br>
<strong>Area Range:</strong> {data['area_range'] or 'Varies'}<br>
<strong>Price Range:</strong> {data['price_range'] or 'Contact for pricing'}<br>
<strong>Possession:</strong> {data['possession_date'] or data['status'] or 'Contact for details'}</p>

<p><strong>ABOUT</strong><br>
{data['project_name']} by {data['builder'] or 'the developer'} is a premium residential project offering {property_type}. Write 250-300 words naturally incorporating "{primary_keyword}" 1-2 times. These "{primary_keyword}" are designed for modern families seeking luxury and comfort in {location_keyword}. Describe the project's unique features, spacious configurations, lifestyle benefits, and what makes these "{primary_keyword}" stand out in the market. Highlight the living experience, community atmosphere, and quality construction standards that make {data['project_name']} exceptional among "{primary_keyword}".</p>

<p><strong>HIGHLIGHTS</strong><br>
{highlights_text}</p>

<p><strong>AMENITIES</strong><br>
Write 200 words about amenities: {', '.join(data['amenities'][:20]) if data['amenities'] else 'Modern amenities'}. Group by categories (fitness, leisure, convenience, security). Describe how these amenities enhance the lifestyle experience for residents of these "{primary_keyword}".</p>

<p><strong>SPECIFICATIONS</strong><br>
Write 100 words about unit specifications: area ranges {data['area_range'] or ''}, possession {data['possession_date'] or ''}, RERA {data['rera_id'] or 'Contact for details'}, total units, and other technical details.</p>

<p><strong>WHO SHOULD BUY THIS</strong></p>

<p><strong>Ideal for Families:</strong><br>
Write 3-4 sentences explaining why {data['project_name']} is perfect for families. Mention proximity to schools, safe environment, and spacious living.</p>

<p><strong>Perfect for Working Professionals:</strong><br>
Write 3-4 sentences about benefits for professionals. Mention connectivity to IT hubs, modern amenities, work-life balance.</p>

<p><strong>Smart Investment Opportunity:</strong><br>
Write 3-4 sentences about investment potential in {location_keyword}. Mention appreciation prospects, rental demand, and quality construction.</p>

"""
        sections_to_generate.append("PROPERTY DESCRIPTION")
    
    # Section 4: Developer Details (COMPANY BACKGROUND)
    if data['developer_details_needs_generation']:
        prompt += f"""
=== DEVELOPER DETAILS DESCRIPTION ===

Write 250-300 words ABOUT {data.get('builder', 'THE DEVELOPER')} COMPANY ONLY.
This is COMPANY INFORMATION - history, experience, completed projects.
DO NOT write about location or property.
DO NOT write about "why choose" or buyer benefits.
DO NOT use keywords about apartments or location here.

<p>Paragraph 1: {data.get('builder', 'The developer')} is a prominent real estate developer with a vision to create exceptional living spaces. Discuss company founding year, establishment story, initial projects, and how it started in the real estate business...</p>

<p>Paragraph 2: With extensive experience in construction, {data.get('builder', 'The developer')} has successfully delivered numerous residential and commercial projects. Mention years in business, types of projects completed, scale of developments, and expertise areas...</p>

<p>Paragraph 3: {data.get('builder', 'The developer')} maintains high quality standards through modern construction methods, premium materials, strict safety protocols, and industry certifications. Discuss building practices and quality assurance...</p>

<p>Paragraph 4: Customer satisfaction is central to {data.get('builder', 'The developer')}'s operations. The company ensures transparency, maintains strong client relationships, provides excellent service, and has built a solid market reputation...</p>

Web context: {web_context[:500] if web_context else 'Leading real estate developer with proven track record'}

"""
        sections_to_generate.append("DEVELOPER DETAILS DESCRIPTION")
    
    # Section 5: Developer Listing (WHY CHOOSE THIS BUILDER)
    if data['developer_listing_needs_generation']:
        prompt += f"""
=== DEVELOPER LISTING DESCRIPTION ===

Write 250-300 words about WHY HOMEBUYERS SHOULD CHOOSE {data.get('builder', 'THIS DEVELOPER')}.
This is BUYER BENEFITS section - not company history.
DO NOT repeat company background from previous section.
DO NOT write about location or specific property.
DO NOT use apartment/location keywords here.

<p>Paragraph 1: Choosing the right developer is crucial for homebuyers when investing in real estate. The developer's reputation directly impacts construction quality, timely delivery, and long-term property value. Explain why trust and reliability matter...</p>

<p>Paragraph 2: {data.get('builder', 'This developer')} demonstrates unwavering commitment to quality construction through use of premium materials, adherence to safety standards, and focus on durability. Homes built by {data.get('builder', 'this developer')} are designed to last, providing long-term value to buyers...</p>

<p>Paragraph 3: {data.get('builder', 'This developer')} has an excellent track record of timely project delivery, ensuring buyers can move into their homes as scheduled. This reliability provides peace of mind and demonstrates professionalism in project execution and timeline management...</p>

<p>Paragraph 4: {data.get('builder', 'This developer')} prioritizes customer service excellence, offering value for money, comprehensive after-sales support, warranty programs, and maintenance assistance. This customer-first approach ensures buyer satisfaction extends well beyond the purchase...</p>

"""
        sections_to_generate.append("DEVELOPER LISTING DESCRIPTION")
    
    if not sections_to_generate:
        return None
    
    prompt += f"""

**FINAL CRITICAL RULES:**
1. Start each section with: === SECTION_NAME ===
2. Make each section COMPLETELY DIFFERENT in content
3. USE PRIMARY KEYWORD "{primary_keyword}" 2-3 TIMES TOTAL (naturally distributed)
4. USE SECONDARY KEYWORD "{secondary_keyword}" 2-3 TIMES TOTAL
5. USE LOCATION "{location_keyword}" 6-7 TIMES TOTAL
6. Keywords must flow naturally in sentences
7. Location section = ONLY about locality (no property, no builder)
8. Property Locality = PROPERTY + LOCATION combination (use primary keyword 2-3 times)
9. Property Description = FULL property details (use primary keyword 1-2 times)
10. Developer sections = NO property/location keywords
11. NO ```html blocks
12. NO dash symbols anywhere
13. Clean HTML paragraphs only

**KEYWORD DISTRIBUTION SUMMARY:**
- Location Description: "{secondary_keyword}" × 2, "{location_keyword}" × 2-4
- Property Locality Description: "{primary_keyword}" × 2-3, "{location_keyword}" × 2-3
- Property Description: "{primary_keyword}" × 1-2 in ABOUT section
- Developer sections: NO apartment/location keywords

Generate ALL sections NOW with natural keyword usage:"""
    
    logger.info(f"📝 Will generate {len(sections_to_generate)} sections: {', '.join(sections_to_generate)}")
    logger.info(f"🎯 Target keyword occurrences: '{primary_keyword}' (3-4×), '{secondary_keyword}' (2-3×)")
    
    return prompt

# Update the generate_seo_content function to include keyword validation

# ============= CONTENT GENERATOR =============

async def generate_seo_content(data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate SEO content - SIMPLIFIED VERSION WITHOUT KEYWORD VALIDATION"""
    try:
        prompt = create_optimized_prompt(data)
        
        # If prompt is None, all content is sufficient
        if prompt is None:
            logger.info("✨ All content sufficient - returning existing content")
            return {
                "locality_description": data.get('locality_description'),
                "prop_locality_description": data.get('prop_locality_description'),
                "property_description": data.get('property_description'),
                "developer_details_description": data.get('developer_details_description'),
                "developer_listing_description": data.get('developer_listing_description'),
                "generation_skipped": True
            }
        
        logger.info(f"🔄 Generating content...")
        
        # Generate with higher temperature for more variety
        generated_text = generate_with_openai(prompt, max_tokens=16000, temperature=0.8)
        
        logger.info(f"📄 Generated text length: {len(generated_text)} chars")
        
        # Clean the generated text
        generated_text = clean_generated_content(generated_text)
        
        # Extract each section
        result = {}
        
        if data['locality_needs_generation']:
            content = extract_section(generated_text, 'LOCATION DESCRIPTION')
            result['locality_description'] = clean_generated_content(content) if content else None
        else:
            result['locality_description'] = data.get('locality_description')
        
        if data['prop_locality_needs_generation']:
            content = extract_section(generated_text, 'PROPERTY LOCALITY DESCRIPTION')
            result['prop_locality_description'] = clean_generated_content(content) if content else None
        else:
            result['prop_locality_description'] = data.get('prop_locality_description')
        
        if data['property_needs_generation']:
            content = extract_section(generated_text, 'PROPERTY DESCRIPTION')
            result['property_description'] = clean_generated_content(content) if content else None
        else:
            result['property_description'] = data.get('property_description')
        
        if data['developer_details_needs_generation']:
            content = extract_section(generated_text, 'DEVELOPER DETAILS DESCRIPTION')
            result['developer_details_description'] = clean_generated_content(content) if content else None
        else:
            result['developer_details_description'] = data.get('developer_details_description')
        
        if data['developer_listing_needs_generation']:
            content = extract_section(generated_text, 'DEVELOPER LISTING DESCRIPTION')
            result['developer_listing_description'] = clean_generated_content(content) if content else None
        else:
            result['developer_listing_description'] = data.get('developer_listing_description')
        
        result['generation_skipped'] = False
        
        return result
        
    except Exception as e:
        raise RuntimeError(f"Content generation failed: {str(e)}")
    

def extract_section(text: str, section_name: str) -> Optional[str]:
    """Extract sections with multiple fallback strategies - ULTRA ROBUST VERSION"""
    try:
        if not text or not text.strip():
            logger.error(f"❌ Empty text provided for extraction")
            return None
        
        text = text.strip()
        logger.info(f"🔍 Attempting to extract: {section_name}")
        logger.info(f"📄 Full text length: {len(text)} chars, {len(text.split())} words")
        
        # Strategy 1: Try === SECTION_NAME === markers
        section_patterns = {
            'LOCATION DESCRIPTION': [
                r'===\s*LOCATION DESCRIPTION\s*===',
                r'###\s*LOCATION DESCRIPTION',
                r'LOCATION DESCRIPTION'
            ],
            'PROPERTY LOCALITY DESCRIPTION': [
                r'===\s*PROPERTY LOCALITY DESCRIPTION\s*===',
                r'###\s*PROPERTY LOCALITY DESCRIPTION',
                r'PROPERTY LOCALITY DESCRIPTION'
            ],
            'PROPERTY DESCRIPTION': [
                r'===\s*PROPERTY DESCRIPTION\s*===',
                r'###\s*PROPERTY DESCRIPTION',
                r'PROPERTY DESCRIPTION',
                r'<p><strong>OVERVIEW'
            ],
            'DEVELOPER DETAILS DESCRIPTION': [
                r'===\s*DEVELOPER DETAILS DESCRIPTION\s*===',
                r'###\s*DEVELOPER DETAILS DESCRIPTION',
                r'DEVELOPER DETAILS DESCRIPTION'
            ],
            'DEVELOPER LISTING DESCRIPTION': [
                r'===\s*DEVELOPER LISTING DESCRIPTION\s*===',
                r'###\s*DEVELOPER LISTING DESCRIPTION',
                r'DEVELOPER LISTING DESCRIPTION'
            ]
        }
        
        patterns = section_patterns.get(section_name, [section_name])
        
        # Try each pattern
        for pattern in patterns:
            try:
                # Split by this pattern
                parts = re.split(pattern, text, flags=re.IGNORECASE)
                
                if len(parts) > 1:
                    logger.info(f"✅ Found section marker: {pattern}")
                    content = parts[1]
                    
                    # Find the end of this section (next === or ### or end)
                    next_section = re.search(r'(===|###)\s+', content)
                    if next_section:
                        content = content[:next_section.start()]
                    
                    # Extract all paragraphs
                    paragraphs = re.findall(r'<p>.*?</p>', content, re.DOTALL)
                    
                    if paragraphs:
                        result = '\n'.join(paragraphs).strip()
                        word_count = count_words(result)
                        
                        if word_count > 50:
                            logger.info(f"✅ Extracted {section_name}: {word_count} words via pattern '{pattern}'")
                            return result
                        else:
                            logger.warning(f"⚠️ Content too short ({word_count} words)")
                            
            except Exception as e:
                logger.warning(f"⚠️ Pattern '{pattern}' failed: {e}")
                continue
        
        # Strategy 2: PROPERTY DESCRIPTION - Look for OVERVIEW tag
        if section_name == 'PROPERTY DESCRIPTION':
            overview_match = re.search(
                r'(<p><strong>OVERVIEW.*?)(?:===|###|\Z)',
                text,
                re.DOTALL | re.IGNORECASE
            )
            if overview_match:
                content = overview_match.group(1).strip()
                word_count = count_words(content)
                if word_count > 100:
                    logger.info(f"✅ Extracted {section_name} via OVERVIEW: {word_count} words")
                    return content
        
        # Strategy 3: Split text into 5 equal chunks and assign by position
        logger.warning(f"⚠️ No markers found. Attempting smart paragraph distribution...")
        
        all_paragraphs = re.findall(r'<p>.*?</p>', text, re.DOTALL)
        total_paragraphs = len(all_paragraphs)
        
        logger.info(f"📊 Total paragraphs found: {total_paragraphs}")
        
        if total_paragraphs < 10:
            logger.error(f"❌ Insufficient paragraphs ({total_paragraphs}) to extract sections")
            return None
        
        # Intelligent chunk distribution
        chunk_size = max(3, total_paragraphs // 5)
        
        section_ranges = {
            'LOCATION DESCRIPTION': (0, chunk_size),
            'PROPERTY LOCALITY DESCRIPTION': (chunk_size, chunk_size * 2),
            'PROPERTY DESCRIPTION': (chunk_size * 2, chunk_size * 4),  # Larger chunk
            'DEVELOPER DETAILS DESCRIPTION': (chunk_size * 4, chunk_size * 4 + chunk_size // 2),
            'DEVELOPER LISTING DESCRIPTION': (chunk_size * 4 + chunk_size // 2, total_paragraphs)
        }
        
        if section_name in section_ranges:
            start, end = section_ranges[section_name]
            selected_paragraphs = all_paragraphs[start:end]
            
            if selected_paragraphs:
                result = '\n'.join(selected_paragraphs).strip()
                word_count = count_words(result)
                logger.info(f"✅ Extracted {section_name} via smart distribution: {word_count} words (paragraphs {start}-{end})")
                return result
        
        logger.error(f"❌ All extraction strategies failed for {section_name}")
        return None
        
    except Exception as e:
        logger.error(f"❌ Fatal error extracting {section_name}: {e}")
        return None

def validate_extracted_content(
    locality_desc: Optional[str],
    prop_locality_desc: Optional[str],
    property_desc: Optional[str],
    builder_details: Optional[str],
    builder_listing: Optional[str]
) -> Dict[str, Any]:
    """Validate that extracted content is actually different"""
    
    validation_result = {
        "all_valid": True,
        "issues": []
    }
    
    def get_first_50_words(text: str) -> str:
        if not text:
            return ""
        words = strip_html_tags(text).split()[:50]
        return ' '.join(words).lower()
    
    contents = {
        "locality_desc": get_first_50_words(locality_desc),
        "prop_locality_desc": get_first_50_words(prop_locality_desc),
        "property_desc": get_first_50_words(property_desc),
        "builder_details": get_first_50_words(builder_details),
        "builder_listing": get_first_50_words(builder_listing)
    }
    
    # Check for duplicates
    for key1, content1 in contents.items():
        if not content1:
            continue
        for key2, content2 in contents.items():
            if key1 >= key2 or not content2:
                continue
            
            # Calculate similarity (simple word overlap)
            words1 = set(content1.split())
            words2 = set(content2.split())
            
            if len(words1) > 0 and len(words2) > 0:
                overlap = len(words1.intersection(words2))
                similarity = overlap / min(len(words1), len(words2))
                
                if similarity > 0.7:  # 70% similar = duplicate
                    validation_result["all_valid"] = False
                    validation_result["issues"].append(
                        f"⚠️ {key1} and {key2} are {similarity*100:.0f}% similar (likely duplicates)"
                    )
                    logger.error(f"❌ DUPLICATE CONTENT: {key1} ≈ {key2} ({similarity*100:.0f}% similar)")
    
    if validation_result["all_valid"]:
        logger.info("✅ Content validation passed - all sections are unique")
    else:
        logger.error(f"❌ Content validation FAILED: {len(validation_result['issues'])} issues")
        for issue in validation_result["issues"]:
            logger.error(issue)
    
    return validation_result

    # ============= FORMAT OUTPUT =============

def format_output(
    transformed_data: Dict[str, Any],
    generated_content: Dict[str, Any],
    reviews: List[Dict[str, Any]],
    faqs: List[Dict[str, Any]],
    error_note: Optional[str] = None
) -> Dict[str, Any]:
    """Format output in the exact required format"""
    
    # Get the full property description (combines all sections)
    prop_desc = generated_content.get('property_description', '')
    
    # Get locality descriptions
    locality_desc = generated_content.get('locality_description')
    prop_locality_desc = generated_content.get('prop_locality_description')
    
    # Get developer descriptions
    builder_details_desc = generated_content.get('developer_details_description')
    builder_listing_desc = generated_content.get('developer_listing_description')
    
    # Log what we're using
    if generated_content.get('generation_skipped'):
        logger.info("✨ Using all existing content (no generation performed)")
    else:
        logger.info("📊 Content sources:")
        logger.info(f"   - locality_desc: {'GENERATED' if transformed_data['locality_needs_generation'] else 'EXISTING'}")
        logger.info(f"   - prop_locality_desc: {'GENERATED' if transformed_data['prop_locality_needs_generation'] else 'EXISTING'}")
        logger.info(f"   - prop_desc: {'GENERATED' if transformed_data['property_needs_generation'] else 'EXISTING'}")
        logger.info(f"   - builder_details: {'GENERATED' if transformed_data['developer_details_needs_generation'] else 'EXISTING'}")
        logger.info(f"   - builder_listing: {'GENERATED' if transformed_data['developer_listing_needs_generation'] else 'EXISTING'}")
    
    output = {
        "propid": transformed_data.get('propertyID'),
        "prop_name": transformed_data.get('project_name'),
        "prop_desc": prop_desc,
        "localityid": transformed_data.get('localityID'),
        "locality_desc": locality_desc,
        "prop_locality_desc": prop_locality_desc,
        "builderid": transformed_data.get('BuilderID'),
        "builder_desc_details": builder_details_desc,
        "builder_desc_listing": builder_listing_desc,
        "reviews": reviews,
        "FAQ": faqs,
        "error_note": error_note
    }
    
    # Log word counts
    logger.info("📊 Final content word counts:")
    if locality_desc:
        logger.info(f"   - locality_desc: {count_words(locality_desc)} words")
    if prop_locality_desc:
        logger.info(f"   - prop_locality_desc: {count_words(prop_locality_desc)} words")
    if prop_desc:
        logger.info(f"   - prop_desc: {count_words(prop_desc)} words")
    if builder_details_desc:
        logger.info(f"   - builder_details: {count_words(builder_details_desc)} words")
    if builder_listing_desc:
        logger.info(f"   - builder_listing: {count_words(builder_listing_desc)} words")
    
    return output

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
                
                logger.info("🔄 Generating content (conditional based on word counts)...")
                generated_content = None
                seo_generation_error = None
                try:
                    generated_content = await generate_seo_content(transformed_data)
                    logger.info("✅ Content generation completed")
                except Exception as e:
                    seo_generation_error = str(e)
                    logger.error(f"❌ Content generation failed: {seo_generation_error}")
                    # Use existing content as fallback
                    generated_content = {
                        "locality_description": transformed_data.get('locality_description'),
                        "prop_locality_description": transformed_data.get('prop_locality_description'),
                        "property_description": transformed_data.get('property_description'),
                        "developer_details_description": transformed_data.get('developer_details_description'),
                        "developer_listing_description": transformed_data.get('developer_listing_description'),
                        "generation_skipped": False
                    }
                
                # Combine property description with full SEO content if needed
                if generated_content.get('property_description'):
                    full_seo = generated_content['property_description']
                else:
                    full_seo = get_fallback_seo_text_from_payload(body_data)
                
                logger.info("🔄 Generating reviews...")
                reviews = []
                try:
                    reviews = generate_reviews(full_seo, count=10)
                    logger.info(f"✅ Generated {len(reviews)} reviews")
                except Exception as e:
                    logger.error(f"❌ Review generation failed: {e}")
                    reviews = []
                
                logger.info("🔄 Generating FAQs...")
                faqs = []
                try:
                    faqs = generate_faqs(transformed_data, full_seo)
                    logger.info(f"✅ Generated {len(faqs)} FAQs")
                except Exception as e:
                    logger.error(f"❌ FAQ generation failed: {e}")
                    faqs = []
                
                formatted_output = format_output(
                    transformed_data,
                    generated_content,
                    reviews,
                    faqs,
                    error_note=seo_generation_error
                )
                
                logger.info("✅ Output formatted successfully")
                
                save_generated_data(formatted_output)
                
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
        
        generated_content = await generate_seo_content(transformed_data)
        
        full_seo = generated_content.get('property_description') or get_fallback_seo_text_from_payload(body_data)
        
        reviews = generate_reviews(full_seo, count=10)
        faqs = generate_faqs(transformed_data, full_seo)
        
        formatted_output = format_output(
            transformed_data,
            generated_content,
            reviews,
            faqs,
            error_note=None
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
        "service": "Property Content Generator API - Smart Version",
        "version": "9.0.0",
        "ai_model": "OpenAI GPT-4o-mini",
        "status": "operational",
        "features": [
            "Smart content validation (250+ words)",
            "Conditional generation (only generates what's needed)",
            "No dash symbols in output",
            "Validates: LocalityDiscription, Property_LocalityDiscription, property_description, builder_details_desc, builder_listing_desc"
        ],
        "output_format": {
            "propid": "string",
            "prop_name": "string",
            "prop_desc": "Clean HTML",
            "localityid": "string",
            "locality_desc": "Clean HTML (existing or generated)",
            "prop_locality_desc": "Clean HTML (existing or generated)",
            "builderid": "string",
            "builder_desc_details": "Clean HTML (existing or generated)",
            "builder_desc_listing": "Clean HTML (existing or generated)",
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
        "faq_generator_ready": True,
        "smart_validation": True,
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

        generated_content = await generate_seo_content(transformed_data)
        
        full_seo = generated_content.get('property_description') or get_fallback_seo_text_from_payload(body_data)

        reviews = generate_reviews(full_seo, count=10)
        faqs = generate_faqs(transformed_data, full_seo)

        formatted_output = format_output(
            transformed_data,
            generated_content,
            reviews,
            faqs,
            error_note=None
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
            "generation_summary": {
                "locality": "GENERATED" if transformed_data['locality_needs_generation'] else "EXISTING",
                "prop_locality": "GENERATED" if transformed_data['prop_locality_needs_generation'] else "EXISTING",
                "property": "GENERATED" if transformed_data['property_needs_generation'] else "EXISTING",
                "dev_details": "GENERATED" if transformed_data['developer_details_needs_generation'] else "EXISTING",
                "dev_listing": "GENERATED" if transformed_data['developer_listing_needs_generation'] else "EXISTING"
            },
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
        
        generated_content = await generate_seo_content(transformed_data)
        
        full_seo = generated_content.get('property_description') or get_fallback_seo_text_from_payload(body_data)
        
        reviews = generate_reviews(full_seo, count=10)
        faqs = generate_faqs(transformed_data, full_seo)
        
        formatted_output = format_output(
            transformed_data,
            generated_content,
            reviews,
            faqs,
            error_note=None
        )
        
        return {
            "message": "This is what would be sent to the callback API",
            "ai_provider": "OpenAI",
            "ai_model": "gpt-4o-mini",
            "callback_api": COMPANY_CALLBACK_API,
            "payload": formatted_output,
            "payload_size_bytes": len(json.dumps(formatted_output)),
            "payload_keys": list(formatted_output.keys()),
            "generation_summary": {
                "locality": "GENERATED" if transformed_data['locality_needs_generation'] else "EXISTING (250+ words)",
                "prop_locality": "GENERATED" if transformed_data['prop_locality_needs_generation'] else "EXISTING (250+ words)",
                "property": "GENERATED" if transformed_data['property_needs_generation'] else "EXISTING (250+ words)",
                "dev_details": "GENERATED" if transformed_data['developer_details_needs_generation'] else "EXISTING (250+ words)",
                "dev_listing": "GENERATED" if transformed_data['developer_listing_needs_generation'] else "EXISTING (250+ words)"
            },
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
    print("🚀 Starting Property Content Generator API (Smart Version)...")
    print("🤖 AI Model: OpenAI GPT-4o-mini")
    print("📍 Server: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")
    print(f"📤 Callback API: {COMPANY_CALLBACK_API}")
    print("\n✨ SMART FEATURES:")
    print("   ✓ Content validation (250+ words threshold)")
    print("   ✓ Conditional generation (only generates what's needed)")
    print("   ✓ No dash symbols in output")
    print("   ✓ Clean HTML formatting")
    print("   ✓ Validates: LocalityDiscription, Property_LocalityDiscription")
    print("   ✓ Validates: property_description, builder_details_desc, builder_listing_desc")
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        timeout_keep_alive=180,
        limit_concurrency=10
    )
