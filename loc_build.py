# loc_build.py - Smart Content Generation & Enhancement Module
"""
This module intelligently processes locality and developer descriptions:
- If content exceeds 200 words: Pass through unchanged
- If content is less than 200 words: Generate SEO-optimized 300+ word content
- If content is missing: Return None for that field
"""

import re
import requests
import logging
from typing import Dict, Optional
from bs4 import BeautifulSoup

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============= CONFIGURATION =============
GROQ_API_KEY = "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"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

WORD_THRESHOLD = 200  # Minimum word count threshold
TARGET_WORD_COUNT = 300  # Target word count for generated content

# ============= UTILITY FUNCTIONS =============

def strip_html_tags(html_text: str) -> str:
    """Remove HTML tags and clean text"""
    if not html_text:
        return ""
    soup = BeautifulSoup(html_text, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def count_words(text: str) -> int:
    """Count words in text after cleaning HTML"""
    if not text:
        return 0
    clean_text = strip_html_tags(text)
    return len(clean_text.split())

def is_content_sufficient(text: str, threshold: int = WORD_THRESHOLD) -> bool:
    """Check if content meets word count threshold"""
    return count_words(text) >= threshold

# ============= GROQ CLIENT =============

class GroqContentGenerator:
    """Handles content generation via GROQ API"""
    
    def __init__(self, api_key: str, api_url: str):
        self.api_key = api_key
        self.api_url = api_url
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def generate_content(self, prompt: str, max_tokens: int = 2000) -> str:
        """Generate content using GROQ API"""
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.7
        }
        
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=payload,
                timeout=180
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"GROQ API error: {str(e)}")
            raise RuntimeError(f"Content generation failed: {str(e)}")

# Initialize GROQ client
groq_client = GroqContentGenerator(api_key=GROQ_API_KEY, api_url=GROQ_API_URL)

# ============= CONTENT PROCESSORS =============

def process_locality_field(
    field_content: Optional[str],
    field_name: str,
    property_name: str,
    city: str,
    locality: str,
    other_field_content: Optional[str] = None
) -> Optional[str]:
    """
    Process a single locality field
    Returns: Enhanced/original content or None
    """
    if not field_content:
        return None
    
    word_count = count_words(field_content)
    logger.info(f"📊 {field_name}: {word_count} words")
    
    # If sufficient, return cleaned version
    if is_content_sufficient(field_content):
        logger.info(f"✅ {field_name} is sufficient. Keeping original.")
        return strip_html_tags(field_content)
    
    # Generate enhanced content
    logger.info(f"🔄 Generating enhanced content for {field_name}")
    
    # Combine with other field if available for better context
    combined = strip_html_tags(field_content)
    if other_field_content:
        combined += " " + strip_html_tags(other_field_content)
    
    prompt = f"""You are an expert SEO content writer for real estate.

TASK: Expand and enhance the following locality description to 300-350 words.

PROPERTY INFO:
- Project: {property_name}
- Location: {locality}, {city}

EXISTING CONTENT (insufficient - needs expansion):
{combined[:1000]}

INSTRUCTIONS:
1. Expand to 300-350 words
2. Make it SEO-optimized and engaging
3. Focus on: connectivity, IT hubs, social infrastructure, growth potential, livability
4. Use ONLY provided information - NO fictional details
5. Plain text only - NO HTML tags
6. Structure with 3-4 paragraphs

Generate the enhanced locality description now:"""

    try:
        generated = groq_client.generate_content(prompt)
        generated = strip_html_tags(generated).strip()
        logger.info(f"✅ Generated {field_name}: {count_words(generated)} words")
        return generated
    except Exception as e:
        logger.error(f"❌ Failed to generate {field_name}: {str(e)}")
        return strip_html_tags(field_content)

def process_developer_field(
    field_content: Optional[str],
    field_name: str,
    builder_name: str,
    property_name: str,
    founded_year: Optional[str] = None,
    property_count: Optional[str] = None,
    other_field_content: Optional[str] = None
) -> Optional[str]:
    """
    Process a developer description field
    Returns: Enhanced/original content or None
    """
    if not field_content:
        return None
    
    word_count = count_words(field_content)
    logger.info(f"📊 Developer {field_name}: {word_count} words")
    
    # If sufficient, return cleaned version
    if is_content_sufficient(field_content):
        logger.info(f"✅ Developer {field_name} is sufficient. Keeping original.")
        return strip_html_tags(field_content)
    
    # Generate enhanced content
    logger.info(f"🔄 Generating enhanced developer content for {field_name}")
    
    # Combine with other field if available
    combined = strip_html_tags(field_content)
    if other_field_content:
        combined += " " + strip_html_tags(other_field_content)
    
    prompt = f"""You are an expert SEO content writer for real estate.

TASK: Expand and enhance the following developer description to 300-350 words.

DEVELOPER INFO:
- Builder Name: {builder_name}
- Founded Year: {founded_year or 'Not specified'}
- Total Projects: {property_count or 'Not specified'}
- Current Project: {property_name}

EXISTING CONTENT (insufficient - needs expansion):
{combined[:1000]}

INSTRUCTIONS:
1. Expand to 300-350 words
2. Make it SEO-optimized and professional
3. Focus on: company background, experience, achievements, quality standards, customer satisfaction
4. Use ONLY provided information - NO invented project names
5. Plain text only - NO HTML tags
6. Structure with 3-4 paragraphs

Generate the enhanced developer description now:"""

    try:
        generated = groq_client.generate_content(prompt)
        generated = strip_html_tags(generated).strip()
        logger.info(f"✅ Generated developer {field_name}: {count_words(generated)} words")
        return generated
    except Exception as e:
        logger.error(f"❌ Failed to generate developer {field_name}: {str(e)}")
        return strip_html_tags(field_content)

# ============= MAIN PROCESSING FUNCTION =============

def enhance_property_content(input_data: Dict) -> Dict:
    """
    Main function to process and enhance property content
    Returns ONLY the enhanced fields
    
    Args:
        input_data: Dictionary containing property data in company format
    
    Returns:
        Dictionary with ONLY enhanced fields:
        {
            "LocalityDiscription": "...",
            "Property_LocalityDiscription": "...",
            "builder_description": "...",
            "builder_data_discription": "..."
        }
    """
    try:
        # Extract property info
        prop_info_list = input_data.get("prop_info", [])
        if not prop_info_list:
            logger.warning("⚠️ No prop_info found in input")
            return {
                "LocalityDiscription": None,
                "Property_LocalityDiscription": None,
                "builder_description": None,
                "builder_data_discription": None
            }
        
        prop_info = prop_info_list[0]
        property_name = prop_info.get("propertyName", "Unknown")
        city = prop_info.get("city_name", "")
        locality = prop_info.get("locality_name", "")
        
        logger.info(f"🔍 Processing content for: {property_name}")
        
        # Initialize result with None values
        result = {
            "LocalityDiscription": None,
            "Property_LocalityDiscription": None,
            "builder_description": None,
            "builder_data_discription": None
        }
        
        # Process LocalityDiscription
        locality_disc = prop_info.get("LocalityDiscription")
        property_locality_disc = prop_info.get("Property_LocalityDiscription")
        
        if locality_disc:
            enhanced_locality = process_locality_field(
                field_content=locality_disc,
                field_name="LocalityDiscription",
                property_name=property_name,
                city=city,
                locality=locality,
                other_field_content=property_locality_disc
            )
            result["LocalityDiscription"] = enhanced_locality
        
        # Process Property_LocalityDiscription
        if property_locality_disc:
            enhanced_prop_locality = process_locality_field(
                field_content=property_locality_disc,
                field_name="Property_LocalityDiscription",
                property_name=property_name,
                city=city,
                locality=locality,
                other_field_content=locality_disc
            )
            result["Property_LocalityDiscription"] = enhanced_prop_locality
        
        # Process developer_info
        developer_info_list = input_data.get("developer_info", [])
        if developer_info_list:
            dev_info = developer_info_list[0]
            builder_name = dev_info.get("BuilderName", "")
            founded_year = dev_info.get("founded_year")
            property_count = dev_info.get("property_count")
            
            # Process builder_description
            builder_desc = dev_info.get("builder_description")
            builder_data_desc = dev_info.get("builder_data_discription")
            
            if builder_desc:
                enhanced_builder_desc = process_developer_field(
                    field_content=builder_desc,
                    field_name="builder_description",
                    builder_name=builder_name,
                    property_name=property_name,
                    founded_year=founded_year,
                    property_count=property_count,
                    other_field_content=builder_data_desc
                )
                result["builder_description"] = enhanced_builder_desc
            
            # Process builder_data_discription
            if builder_data_desc:
                enhanced_builder_data = process_developer_field(
                    field_content=builder_data_desc,
                    field_name="builder_data_discription",
                    builder_name=builder_name,
                    property_name=property_name,
                    founded_year=founded_year,
                    property_count=property_count,
                    other_field_content=builder_desc
                )
                result["builder_data_discription"] = enhanced_builder_data
        
        logger.info(f"✅ Content enhancement complete for {property_name}")
        logger.info(f"📊 Results:")
        logger.info(f"   - LocalityDiscription: {'Enhanced' if result['LocalityDiscription'] else 'None'}")
        logger.info(f"   - Property_LocalityDiscription: {'Enhanced' if result['Property_LocalityDiscription'] else 'None'}")
        logger.info(f"   - builder_description: {'Enhanced' if result['builder_description'] else 'None'}")
        logger.info(f"   - builder_data_discription: {'Enhanced' if result['builder_data_discription'] else 'None'}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Content enhancement failed: {str(e)}")
        return {
            "LocalityDiscription": None,
            "Property_LocalityDiscription": None,
            "builder_description": None,
            "builder_data_discription": None
        }

if __name__ == "__main__":
    # Test the module
    import json
    
    sample_input = {
        "prop_info": [
            {
                "propertyName": "Test Property",
                "city_name": "Bangalore",
                "locality_name": "Sarjapur Road",
                "LocalityDiscription": "Short locality description.",
                "Property_LocalityDiscription": None
            }
        ],
        "developer_info": [
            {
                "BuilderName": "Test Builder",
                "founded_year": "2010",
                "property_count": "5",
                "builder_description": "Short builder description.",
                "builder_data_discription": None
            }
        ]
    }
    
    print("🚀 Testing Content Enhancement Module...")
    print("=" * 80)
    
    result = enhance_property_content(sample_input)
    
    print("\n📤 RESULT:")
    print(json.dumps(result, indent=2))