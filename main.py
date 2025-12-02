# main.py - Enhanced API-Driven Property Content Generator
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

# New imports for retry/backoff and small helper
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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
    title="Property Content Generator API - Automated",
    description="Receives data via POST, generates SEO content + reviews, sends back automatically",
    version="6.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============= CONFIGURATION =============

GROQ_API_KEY = "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"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Company callback API - Direct URL (no environment variable)
COMPANY_CALLBACK_API = "http://192.168.0.144/superadmin/AItasks_Controller/update_Contents"

# ============= UTILITY FUNCTIONS =============

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
    
    # Split by double newlines to preserve paragraphs
    paragraphs = text.split('\n\n')
    wrapped = []
    
    for para in paragraphs:
        para = para.strip()
        if para:
            # Replace single newlines with spaces within paragraph
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
    """
    Try to extract a reasonable fallback description from the incoming payload.
    This is used when the external content generation fails.
    """
    try:
        prop = body_data.get('prop_info', [{}])[0]
        # prefer property description fields if present
        candidates = [
            prop.get('property_description') if isinstance(prop, dict) else None,
            prop.get('Property_LocalityDiscription') if isinstance(prop, dict) else None,
            prop.get('LocalityDiscription') if isinstance(prop, dict) else None,
            prop.get('LocalityDiscription') if isinstance(prop, dict) else None
        ]
        for c in candidates:
            if c:
                text = strip_html_tags(c)
                if text:
                    return text
    except Exception:
        pass
    # Last resort: short placeholder
    return "Brief property overview not available. Please check property data."

# ============= INPUT MODELS =============

class PropInfo(BaseModel):
    propertyid: Optional[str] = None
    propertyName: str
    city_name: Optional[str] = None
    locality_name: Optional[str] = None
    localityid: Optional[str] = None
    LocalityDiscription: Optional[str] = None
    Property_LocalityDiscription: Optional[str] = None
    BuilderName: Optional[str] = None
    BuilderId: Optional[str] = None
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
    BuilderId: Optional[str] = None
    property_count: Optional[str] = None
    founded_year: Optional[str] = None
    builder_description: Optional[str] = None
    builder_data_discription: Optional[str] = None

class IncomingPropertyData(BaseModel):
    status: Optional[str] = None
    result: Optional[str] = None
    prop_info: List[PropInfo]
    basic_details: List[BasicDetails]
    amenities: List[Amenity]
    highlights: Optional[List[Highlight]] = []
    developer_info: Optional[List[DeveloperInfo]] = []

# ============= GROQ CLIENT =============

class _MsgObj:
    def __init__(self, text: str):
        self.text = text

class _MessagesCreateResponse:
    def __init__(self, text: str):
        self.content = [_MsgObj(text)]

class GroqClient:
    def __init__(self, api_key: str, api_url: str):
        self.api_key = api_key
        self.api_url = api_url
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.messages = self.Messages(self)

    class Messages:
        def __init__(self, parent):
            self.parent = parent

        def create(self, model: str, max_tokens: int, temperature: float, messages: List[Dict[str, str]]):
            payload = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            # Retry logic with backoff for transient errors (429, 5xx)
            max_attempts = 5
            base_backoff = 1.0
            for attempt in range(1, max_attempts + 1):
                try:
                    session = requests.Session()
                    retries = Retry(
                        total=2,
                        backoff_factor=0.5,
                        status_forcelist=[429, 500, 502, 503, 504],
                        raise_on_status=False
                    )
                    session.mount("https://", HTTPAdapter(max_retries=retries))

                    resp = session.post(
                        self.parent.api_url,
                        headers=self.parent.headers,
                        json=payload,
                        timeout=180
                    )

                    # If status indicates rate limit or server error, raise to trigger backoff
                    if resp.status_code == 429 or 500 <= resp.status_code < 600:
                        logger.warning(f"GROQ returned status {resp.status_code} (attempt {attempt}). Retrying...")
                        # raise HTTPError with response to be handled below
                        http_err = requests.HTTPError(f"Status {resp.status_code}")
                        http_err.response = resp
                        raise http_err

                    resp.raise_for_status()
                    data = resp.json()
                    text = data["choices"][0]["message"]["content"]
                    return _MessagesCreateResponse(text=text)

                except requests.HTTPError as e:
                    status = getattr(e.response, "status_code", None) if hasattr(e, "response") else None
                    logger.warning(f"GROQ request failed (attempt {attempt}/{max_attempts}) status={status} error={e}")
                    if attempt == max_attempts:
                        raise RuntimeError(f"GROQ API error: {str(e)}")
                    # exponential backoff with small jitter
                    sleep_time = base_backoff * (2 ** (attempt - 1)) + (0.1 * attempt)
                    time.sleep(sleep_time)
                except Exception as e:
                    logger.warning(f"GROQ request exception (attempt {attempt}/{max_attempts}): {e}")
                    if attempt == max_attempts:
                        raise RuntimeError(f"GROQ API error: {str(e)}")
                    time.sleep(base_backoff * (2 ** (attempt - 1)))

client = GroqClient(api_key=GROQ_API_KEY, api_url=GROQ_API_URL)

# ============= ENHANCED DATA TRANSFORMER =============

class DataTransformer:
    """Converts company format to internal format with content richness analysis"""
    
    @staticmethod
    def transform(incoming: IncomingPropertyData) -> Dict[str, Any]:
        prop = incoming.prop_info[0] if incoming.prop_info else PropInfo(propertyName="Unknown")
        basic = incoming.basic_details[0] if incoming.basic_details else BasicDetails()
        dev = incoming.developer_info[0] if incoming.developer_info else None
        
        # Extract amenities (ignore if empty)
        amenity_names = []
        if incoming.amenities:
            amenity_names = [a.Name for a in incoming.amenities if a.Name]
        
        # Extract highlights (ignore if empty)
        highlight_points = []
        if incoming.highlights:
            highlight_points = [h.highlight_point for h in incoming.highlights if h.highlight_point]
        
        # Build price range
        price_range = None
        if prop.min_price and prop.max_price:
            try:
                min_p = float(prop.min_price) / 10000000
                max_p = float(prop.max_price) / 10000000
                price_range = f"₹ {min_p:.2f} Cr - {max_p:.2f} Cr"
            except:
                pass
        
        # Build area range
        area_range = None
        if basic.area_min and basic.area_max:
            area_range = f"{basic.area_min} - {basic.area_max} sq.ft"
        
        # ===== ANALYZE LOCALITY DESCRIPTION =====
        locality_desc = None
        locality_needs_generation = True
        
        # Check both possible locality description fields
        for field in [prop.Property_LocalityDiscription, prop.LocalityDiscription]:
            if field:
                clean_text = strip_html_tags(field)
                if is_content_sufficient(clean_text, min_words=150):
                    locality_desc = clean_text
                    locality_needs_generation = False
                    logger.info(f"✅ Sufficient locality description found ({calculate_content_richness(field)} words)")
                    break
        
        # ===== ANALYZE DEVELOPER INFO =====
        developer_desc = None
        developer_needs_generation = True
        
        if dev:
            # Check builder_data_discription first (more detailed)
            for field in [dev.builder_data_discription, dev.builder_description]:
                if field:
                    clean_text = strip_html_tags(field)
                    if is_content_sufficient(clean_text, min_words=100):
                        developer_desc = clean_text
                        developer_needs_generation = False
                        logger.info(f"✅ Sufficient developer description found ({calculate_content_richness(field)} words)")
                        break
        
        transformed = {
            "propertyid": prop.propertyid,
            "project_name": prop.propertyName,
            "builder": prop.BuilderName or (dev.BuilderName if dev else None),
            "builderid": prop.BuilderId or (dev.BuilderId if dev else None),
            "localityid": prop.localityid,
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
            
            # Content richness flags
            "locality_description": locality_desc,
            "locality_needs_generation": locality_needs_generation,
            "developer_description": developer_desc,
            "developer_needs_generation": developer_needs_generation,
            
            # Additional metadata
            "developer_founded": dev.founded_year if dev else None,
            "developer_project_count": dev.property_count if dev else None
        }
        
        return transformed

# ============= ENHANCED PROMPT BUILDER =============

def create_optimized_prompt(data: Dict[str, Any]) -> str:
    """Create SEO-optimized prompt based on content availability"""
    
    # Determine what needs to be generated vs restructured
    locality_instruction = ""
    if data['locality_needs_generation']:
        locality_instruction = """
=== LOCATION ===
Generate 180-220 words about the location:
- Focus on connectivity and nearby areas
- Mention growth potential and livability
- Highlight infrastructure and accessibility
- 2-3 paragraphs"""
    else:
        locality_instruction = f"""
=== LOCATION ===
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
=== ABOUT THE DEVELOPER ===
Generate 180-220 words about the developer:
- Company background and founding year
- Experience and expertise in real estate
- Key achievements and completed projects
- Quality standards and customer satisfaction
- Unique selling points
- 2-3 comprehensive paragraphs"""
    else:
        developer_instruction = f"""
=== ABOUT THE DEVELOPER ===
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

    # Build highlights section instruction
    highlights_instruction = ""
    if data['highlights']:
        highlights_instruction = f"""
=== HIGHLIGHTS ===
The following highlights are provided. Present them in engaging format (120-140 words):
{chr(10).join(['- ' + h for h in data['highlights'][:10]])}

Format as 8-10 concise bullet points with benefit-focused descriptions."""
    else:
        highlights_instruction = """
=== HIGHLIGHTS ===
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

=== OVERVIEW ===
Project Name: {data['project_name']}
Builder: {data['builder'] or '[Skip this line]'}
Location: {data['location'] or '[Skip this line]'}
Configurations: {', '.join(data['configurations']) if data['configurations'] else '[Skip this line]'}
Area Range: {data['area_range'] or '[Skip this line]'}
Price Range: {data['price_range'] or '[Skip this line]'}
Possession: {data['possession_date'] or data['status'] or '[Skip this line]'}
RERA ID: {data['rera_id'] or '[Skip this line]'}

(Remove any lines that say [Skip this line])

=== ABOUT ===
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

=== AMENITIES ===
{'Write 180-220 words about the following amenities:' if data['amenities'] else 'Write 180-220 words about typical modern amenities:'}
{', '.join(data['amenities'][:20]) if data['amenities'] else 'Not specified - use general modern amenities'}
- Group by category: fitness & sports, leisure & entertainment, convenience & services, security & safety
- Describe each category with 2-3 sentences explaining the benefits
- 3-4 paragraphs with rich descriptions
- Make it lifestyle-focused, not just a list

{locality_instruction}

{developer_instruction}

=== SPECIFICATIONS ===
Write 80-100 words about unit specifications:
- List area ranges for each configuration if available
- Mention total number of units and towers if specified
- Include possession date and RERA details
- Keep it organized and easy to read
- Format as short, clear sentences

=== WHO SHOULD BUY THIS ===
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
    """Generate SEO content using GROQ with intelligent restructuring"""
    try:
        prompt = create_optimized_prompt(data)
        
        logger.info(f"🔄 Content generation mode:")
        logger.info(f"   - Locality: {'RESTRUCTURE' if not data['locality_needs_generation'] else 'GENERATE'}")
        logger.info(f"   - Developer: {'RESTRUCTURE' if not data['developer_needs_generation'] else 'GENERATE'}")
        
        message = client.messages.create(
            model="llama-3.3-70b-versatile",
            max_tokens=16000,
            temperature=0.7,
            messages=[{"role": "user", "content": prompt}]
        )
        
        generated_text = message.content[0].text
        
        # Clean up
        generated_text = re.sub(r'\|\s*\|', '', generated_text)
        generated_text = re.sub(r'\|\s*---\s*\|', '', generated_text)
        generated_text = re.sub(r'\[Skip this line\].*?\n', '', generated_text)
        
        # Remove unwanted phrases
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

def format_output(
    transformed_data: Dict[str, Any],
    seo_content: str,
    reviews: List[Dict[str, Any]],
    enhanced_content: Optional[Dict[str, Any]],
    error_note: Optional[str] = None
) -> Dict[str, Any]:
    """Format output in the exact required format"""
    
    # Wrap SEO content in <p> tags
    seo_content_html = wrap_in_p_tags(seo_content)
    
    # Get enhanced content fields or use None
    locality_desc = None
    prop_locality_desc = None
    builder_desc_details = None
    builder_desc_listing = None
    
    if enhanced_content:
        locality_desc = enhanced_content.get('LocalityDiscription')
        prop_locality_desc = enhanced_content.get('Property_LocalityDiscription')
        builder_desc_details = enhanced_content.get('builder_data_discription')
        builder_desc_listing = enhanced_content.get('builder_description')
    
    output = {
        "propid": transformed_data.get('propertyid'),
        "prop_name": transformed_data.get('project_name'),
        "prop_desc": seo_content_html,
        "localityid": transformed_data.get('localityid'),
        "locality_desc": locality_desc,
        "prop_locality_desc": prop_locality_desc,
        "builderid": transformed_data.get('builderid'),
        "builder_desc_details": builder_desc_details,
        "builder_desc_listing": builder_desc_listing,
        "reviews": reviews,
        # surface any error that occurred during generation so downstream knows we used fallback
        "error_note": error_note
    }
    
    return output

# ============= CALLBACK SENDER =============

async def send_to_company_api(payload: Dict[str, Any]):
    """Send generated content back to company API"""
    try:
        # Log the payload being sent (first 1000 chars)
        payload_preview = json.dumps(payload, indent=2, ensure_ascii=False)[:1000]
        logger.info(f"📤 Sending payload to {COMPANY_CALLBACK_API}")
        logger.info(f"📦 Payload preview:\n{payload_preview}...")
        logger.info(f"📊 Payload keys: {list(payload.keys())}")
        logger.info(f"📏 Payload size: {len(json.dumps(payload))} bytes")
        
        response = requests.post(
            COMPANY_CALLBACK_API,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        logger.info(f"📨 Response status code: {response.status_code}")
        logger.info(f"📨 Response text: {response.text[:500]}")
        
        response.raise_for_status()
        logger.info(f"✅ Successfully sent results to company API: {COMPANY_CALLBACK_API}")
        return True
    except requests.exceptions.Timeout:
        logger.error(f"❌ Timeout sending to company API: {COMPANY_CALLBACK_API}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Request failed to company API: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"❌ Response status: {e.response.status_code}")
            logger.error(f"❌ Response body: {e.response.text[:500]}")
        return False
    except Exception as e:
        logger.error(f"❌ Failed to send to company API: {str(e)}")
        return False

# ============= BACKGROUND PROCESSOR =============

async def process_data_background(body_data: Any, raw_body: bytes):
    """Process data in background and handle errors"""
    try:
        if isinstance(body_data, dict):
            try:
                incoming_data = IncomingPropertyData(**body_data)
                logger.info("✅ Data validation successful")
                
                # STEP 1: Transform data
                transformed_data = DataTransformer.transform(incoming_data)
                logger.info("✅ Data transformed successfully")
                
                # STEP 2: Enhance content using loc_build.py
                logger.info("🔄 Enhancing locality and developer content...")
                enhanced_content = None
                if enhance_property_content:
                    enhanced_content = enhance_property_content(body_data)
                
                # STEP 3: Generate SEO content (resilient)
                logger.info("🔄 Generating SEO content...")
                seo_content = None
                seo_generation_error = None
                try:
                    seo_content = await generate_seo_content(transformed_data)
                    logger.info("✅ SEO content generated")
                except Exception as e:
                    seo_generation_error = str(e)
                    logger.error(f"❌ Content generation failed: {seo_generation_error}")
                    # Fallback: try to get text from incoming payload
                    try:
                        seo_content = get_fallback_seo_text_from_payload(body_data)
                        logger.info("⚠️ Using fallback SEO content (from provided descriptions).")
                    except Exception as e2:
                        logger.error(f"❌ Failed to build fallback SEO content: {e2}")
                        seo_content = f"{transformed_data.get('project_name')} - Brief description not available."
                
                # STEP 4: Generate reviews (graceful)
                logger.info("🔄 Generating reviews...")
                reviews = []
                try:
                    reviews = generate_reviews(seo_content, count=10)
                    logger.info(f"✅ Generated {len(reviews)} reviews")
                except Exception as e:
                    logger.error(f"❌ Review generation failed: {e}")
                    reviews = []
                
                # STEP 5: Format output (include error note)
                formatted_output = format_output(
                    transformed_data,
                    seo_content,
                    reviews,
                    enhanced_content,
                    error_note=seo_generation_error
                )
                
                logger.info("✅ Output formatted successfully")
                
                # Send to company API (always attempt)
                await send_to_company_api(formatted_output)
                
            except Exception as validation_error:
                logger.error(f"❌ Validation error: {str(validation_error)}")
                logger.error(f"📦 Data received: {json.dumps(body_data, indent=2)}")
                # Try to notify company API of validation failure with minimal payload
                minimal_payload = {
                    "propid": body_data.get('prop_info', [{}])[0].get('propertyid'),
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
        # try to notify company with minimal info if possible
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
    """
    MAIN ENDPOINT - Validates incoming data and processes in background
    """
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
    """
    Optional endpoint for manual testing - returns formatted output immediately
    """
    try:
        raw_body = await request.body()
        body_data = json.loads(raw_body)
        
        incoming_data = IncomingPropertyData(**body_data)
        
        # Transform data
        transformed_data = DataTransformer.transform(incoming_data)
        
        # Enhance content
        enhanced_content = None
        if enhance_property_content:
            enhanced_content = enhance_property_content(body_data)
        
        # Generate SEO content (try/catch and fallback)
        seo_content = None
        seo_generation_error = None
        try:
            seo_content = await generate_seo_content(transformed_data)
        except Exception as e:
            seo_generation_error = str(e)
            logger.error(f"❌ Manual SEO generation failed: {seo_generation_error}")
            seo_content = get_fallback_seo_text_from_payload(body_data)
            logger.info("⚠️ Using fallback SEO content for manual run.")
        
        # Generate reviews
        reviews = generate_reviews(seo_content, count=10)
        
        # Format output
        formatted_output = format_output(
            transformed_data,
            seo_content,
            reviews,
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
        "service": "Property Content Generator API - Enhanced",
        "version": "6.0.0",
        "status": "operational",
        "mode": "API-driven with formatted output",
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
            "reviews": "array"
        },
        "callback_api": COMPANY_CALLBACK_API
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "groq_ready": True,
        "review_generator_ready": generate_reviews_from_text is not None,
        "loc_build_ready": enhance_property_content is not None,
        "callback_api": COMPANY_CALLBACK_API
    }

@app.post("/test-callback")
async def test_callback(request: Request):
    """
    Test endpoint to verify what data would be sent to callback API
    Returns the formatted output without actually sending it
    """
    try:
        raw_body = await request.body()
        body_data = json.loads(raw_body)
        
        incoming_data = IncomingPropertyData(**body_data)
        
        # Transform data
        transformed_data = DataTransformer.transform(incoming_data)
        
        # Enhance content
        enhanced_content = None
        if enhance_property_content:
            enhanced_content = enhance_property_content(body_data)
        
        # Generate SEO content (try/catch and fallback)
        seo_content = None
        seo_generation_error = None
        try:
            seo_content = await generate_seo_content(transformed_data)
        except Exception as e:
            seo_generation_error = str(e)
            logger.error(f"❌ Test-callback SEO generation failed: {seo_generation_error}")
            seo_content = get_fallback_seo_text_from_payload(body_data)
            logger.info("⚠️ Using fallback SEO content for test-callback.")
        
        # Generate reviews
        reviews = generate_reviews(seo_content, count=10)
        
        # Format output
        formatted_output = format_output(
            transformed_data,
            seo_content,
            reviews,
            enhanced_content,
            error_note=seo_generation_error
        )
        
        # Return what would be sent
        return {
            "message": "This is what would be sent to the callback API",
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
    print("🚀 Starting Enhanced Property Content Generator...")
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
