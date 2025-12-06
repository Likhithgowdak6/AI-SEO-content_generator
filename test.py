"""
Enhanced Test Script for Property Content Generation API
Verifies output format matches company API requirements
Includes better debugging for content extraction issues
"""

import requests
import json
from datetime import datetime
from pathlib import Path
import re

# Configuration
API_BASE_URL = "http://localhost:8000"
TEST_ENDPOINT = f"{API_BASE_URL}/test-callback"
OUTPUT_FILE = "test_output_results.json"

# Expected output format
EXPECTED_KEYS = [
    'propid', 'prop_name', 'prop_desc', 'localityid', 'locality_desc', 
    'prop_locality_desc', 'builderid', 'builder_desc_details', 
    'builder_desc_listing', 'reviews', 'FAQ', 'error_note'
]

# Test input data
TEST_INPUT = {
    "status": "True",
    "result": "successful",
    "prop_info": [
        {
            "propertyID": "44599",
            "propertyName": "Shri Aasra Aditya Apartment",
            "city_name": "Ghaziabad",
            "locality_name": "Bahrampur",
            "localityID": "5984",
            "LocalityDiscription": None,
            "Property_LocalityDiscription": None,
            "BuilderName": "Shri Aasra Homes",
            "BuilderID": "18045",
            "Status": "Ready to Move",
            "bhk": "1 BHK",
            "min_price": "1603000",
            "max_price": "2900000"
        }
    ],
    "basic_details": [
        {
            "property_description": "<p>Shriaasra Aditya Apartment</p>\r\n",
            "dimension": "12.50   ",
            "total_apartments": "394",
            "area_min": "525",
            "area_max": "950  ",
            "PossessionDate": "2020-03-03",
            "propertyType": "Apartments",
            "RERA_ID": "",
            "RegionName": "West Ghaziabad"
        }
    ],
    "amenities": [
        {"Name": "Garden"},
        {"Name": "Maintenance Staff"},
        {"Name": "Power Backup"},
        {"Name": "Elevator"},
        {"Name": "Indoor Games"},
        {"Name": "Water Supply"},
        {"Name": "Car Parking"},
        {"Name": "CCTV"},
        {"Name": "Club House"},
        {"Name": "Gym"},
        {"Name": "Rainwater Harvesting"},
        {"Name": "Sewage Treatment"}
    ],
    "highlights": [],
    "developer_info": [
        {
            "BuilderName": "Shri Aasra Homes",
            "BuilderID": "18045",
            "property_count": None,
            "founded_year": None,
            "builder_details_desc": None,
            "builder_listing_desc": None
        }
    ]
}


def count_words(text):
    """Count words excluding HTML tags"""
    if not text:
        return 0
    clean = re.sub(r'<[^>]+>', '', str(text))
    return len(clean.split())


def validate_html_format(text, field_name):
    """Validate if text is in clean HTML format - IMPROVED VERSION"""
    if not text:
        return False, "Empty content"
    
    text_str = str(text)
    
    # Check for <p> tags
    has_p_tags = '<p>' in text_str and '</p>' in text_str
    
    # Check for unwanted markdown code blocks
    has_code_blocks = '```html' in text_str or '```json' in text_str or '```' in text_str
    
    # Check for section headers (these should NOT be in final output)
    has_section_headers = '###' in text_str
    
    # Check for problematic dash symbols (en-dash, em-dash)
    # Note: Regular hyphen (-) in compound words is OK
    # We're looking for: en-dash (–), em-dash (—), or dash-as-bullet (- at start of line)
    has_bad_dashes = False
    dash_examples = []
    
    # Check for en-dash (–) and em-dash (—)
    if '–' in text_str or '—' in text_str:
        has_bad_dashes = True
        if '–' in text_str:
            dash_examples.append("en-dash (–)")
        if '—' in text_str:
            dash_examples.append("em-dash (—)")
    
    # Check for dash used as bullet at start of lines (after <p> or <br>)
    if re.search(r'(<p>|<br>)\s*-\s+', text_str):
        has_bad_dashes = True
        dash_examples.append("dash as bullet (- at line start)")
    
    # Collect issues
    issues = []
    
    if has_code_blocks:
        issues.append("Contains markdown code blocks (```)")
    
    if has_section_headers:
        issues.append("Contains section headers (###)")
    
    if not has_p_tags:
        issues.append("Missing <p> tags")
    
    if has_bad_dashes:
        issues.append(f"Contains dash symbols: {', '.join(dash_examples)}")
    
    if issues:
        return False, "; ".join(issues)
    
    return True, "Valid HTML format"



def check_content_extraction(payload, result):
    """Check if content extraction from OpenAI worked properly"""
    print("\n" + "="*80)
    print("🔍 CONTENT EXTRACTION DEBUGGING")
    print("="*80)
    
    # Check if we have generation_summary in result
    gen_summary = result.get('generation_summary', {})
    
    if gen_summary:
        print("\n📊 Generation Summary from API:")
        for field, status in gen_summary.items():
            print(f"   {field}: {status}")
    
    # Check each content field
    content_fields = {
        'locality_desc': 'Locality Description',
        'prop_locality_desc': 'Property Locality Description',
        'prop_desc': 'Property Description',
        'builder_desc_details': 'Builder Details',
        'builder_desc_listing': 'Builder Listing'
    }
    
    print("\n🔬 Content Extraction Results:")
    
    all_extracted = True
    for field, label in content_fields.items():
        content = payload.get(field)
        
        if content and count_words(content) > 50:
            status = "✅ EXTRACTED"
            word_count = count_words(content)
        else:
            status = "❌ FAILED"
            all_extracted = False
            word_count = count_words(content) if content else 0
        
        print(f"\n   {status} {label}")
        print(f"      Field: {field}")
        print(f"      Word count: {word_count}")
        
        if not content or word_count < 50:
            print(f"      ⚠️ Content extraction failed - check main.py extract_section() function")
    
    if not all_extracted:
        print("\n" + "="*80)
        print("🔧 DEBUGGING TIPS:")
        print("="*80)
        print("\n1. Check OpenAI Response Format:")
        print("   - Make sure OpenAI is using ### section headers")
        print("   - Verify sections are properly separated")
        
        print("\n2. Update extract_section() Function:")
        print("   - Use the improved version with multiple fallback strategies")
        print("   - Check regex patterns match actual OpenAI output")
        
        print("\n3. Update Prompt:")
        print("   - Ensure prompt explicitly requires ### SECTION_NAME headers")
        print("   - Verify prompt asks for clean HTML output")
        
        print("\n4. Check Logs:")
        print("   - Look for 'Could not extract' warnings in server logs")
        print("   - Verify OpenAI generation was successful")
    
    print("\n" + "="*80)
    
    return all_extracted


def verify_output_format(payload):
    """Verify the output matches expected company API format"""
    print("\n" + "="*80)
    print("🔍 OUTPUT FORMAT VERIFICATION")
    print("="*80)
    
    # Check all keys are present
    missing_keys = [key for key in EXPECTED_KEYS if key not in payload]
    extra_keys = [key for key in payload.keys() if key not in EXPECTED_KEYS]
    
    print(f"\n✅ Expected Keys: {EXPECTED_KEYS}")
    print(f"\n📦 Actual Keys: {list(payload.keys())}")
    
    if missing_keys:
        print(f"\n❌ MISSING KEYS: {missing_keys}")
    else:
        print(f"\n✅ All expected keys present")
    
    if extra_keys:
        print(f"\n⚠️ Extra keys (not expected): {extra_keys}")
    
    # Verify format matches company API requirement
    if list(payload.keys()) == EXPECTED_KEYS:
        print(f"\n✅ ✅ ✅ FORMAT MATCHES COMPANY API REQUIREMENT!")
    else:
        print(f"\n⚠️ Format differs from company API requirement")
    
    print("\n" + "="*80)
    
    return len(missing_keys) == 0


def validate_html_content(payload):
    """Validate HTML formatting of content fields - IMPROVED VERSION"""
    print("\n" + "="*80)
    print("🌐 HTML FORMAT VALIDATION")
    print("="*80)
    
    html_fields = [
        'prop_desc',
        'locality_desc', 
        'prop_locality_desc',
        'builder_desc_details',
        'builder_desc_listing'
    ]
    
    all_valid = True
    issues_found = {}
    
    for field in html_fields:
        content = payload.get(field)
        is_valid, message = validate_html_format(content, field)
        
        status = "✅" if is_valid else "❌"
        print(f"\n{status} {field}:")
        print(f"   {message}")
        
        if content:
            word_count = count_words(content)
            print(f"   Word count: {word_count}")
            
            # Show HTML structure
            if '<p>' in str(content):
                p_count = str(content).count('<p>')
                print(f"   Paragraph tags: {p_count} <p> tags found")
            
            # Check for specific issues
            text_str = str(content)
            
            # Check for dashes more carefully
            has_endash = '–' in text_str
            has_emdash = '—' in text_str
            has_bullet_dash = bool(re.search(r'(<p>|<br>)\s*-\s+', text_str))
            
            if has_endash or has_emdash or has_bullet_dash:
                dash_types = []
                if has_endash:
                    dash_types.append(f"en-dash (–): {text_str.count('–')} occurrences")
                if has_emdash:
                    dash_types.append(f"em-dash (—): {text_str.count('—')} occurrences")
                if has_bullet_dash:
                    dash_types.append("bullet dashes (- at line start)")
                
                print(f"   ⚠️ Dash issues: {', '.join(dash_types)}")
                issues_found[field] = dash_types
            
            # Show clean preview
            clean_preview = re.sub(r'<[^>]+>', '', text_str)[:150]
            print(f"   Preview: {clean_preview}...")
        else:
            print(f"   Content: None/Empty")
            print(f"   ⚠️ This field was not generated or extracted")
        
        if not is_valid:
            all_valid = False
    
    if all_valid:
        print(f"\n✅ ✅ ✅ ALL CONTENT IN CLEAN HTML FORMAT!")
    else:
        print(f"\n⚠️ Some content has formatting issues")
        
        if issues_found:
            print(f"\n🔧 ISSUES FOUND:")
            for field, issues in issues_found.items():
                print(f"   {field}:")
                for issue in issues:
                    print(f"      - {issue}")
            
            print(f"\n💡 TO FIX:")
            print(f"   1. Update remove_dashes_from_text() in main.py")
            print(f"   2. Apply it to all generated content before returning")
            print(f"   3. Check that OpenAI prompt explicitly forbids dashes")
    
    print("\n" + "="*80)
    
    return all_valid



def check_locality_differentiation(payload):
    """Check if locality_desc and prop_locality_desc are properly differentiated"""
    print("\n" + "="*80)
    print("🔍 LOCALITY DESCRIPTION DIFFERENTIATION CHECK")
    print("="*80)
    
    locality_desc = payload.get('locality_desc', '')
    prop_locality_desc = payload.get('prop_locality_desc', '')
    prop_name = payload.get('prop_name', '')
    
    if not locality_desc or not prop_locality_desc:
        print("\n⚠️ One or both locality fields are empty")
        print("   This usually means content extraction failed")
        return False
    
    # Check property name mentions
    def count_mentions(text, keyword):
        if not text:
            return 0
        clean = re.sub(r'<[^>]+>', '', str(text))
        return len(re.findall(re.escape(keyword), clean, re.IGNORECASE))
    
    locality_mentions = count_mentions(locality_desc, prop_name)
    prop_locality_mentions = count_mentions(prop_locality_desc, prop_name)
    
    print(f"\n📍 locality_desc (pure location, NO property name):")
    print(f"   Property name mentions: {locality_mentions}")
    print(f"   Word count: {count_words(locality_desc)}")
    if locality_mentions == 0:
        print(f"   ✅ Correct: No property name mentioned (pure location)")
    else:
        print(f"   ❌ Error: Property name found {locality_mentions} times (should be 0)")
    
    print(f"\n🏘️ prop_locality_desc (property + location combined):")
    print(f"   Property name mentions: {prop_locality_mentions}")
    print(f"   Word count: {count_words(prop_locality_desc)}")
    if prop_locality_mentions >= 2:
        print(f"   ✅ Correct: Property name mentioned {prop_locality_mentions} times")
    else:
        print(f"   ⚠️ Warning: Property name only mentioned {prop_locality_mentions} times (expected 2-3)")
    
    # Check content similarity
    locality_words = set(re.sub(r'<[^>]+>', '', locality_desc).lower().split())
    prop_locality_words = set(re.sub(r'<[^>]+>', '', prop_locality_desc).lower().split())
    
    if locality_words and prop_locality_words:
        similarity = len(locality_words & prop_locality_words) / len(locality_words) if locality_words else 0
        print(f"\n📊 Content Overlap: {similarity*100:.1f}%")
        
        if similarity < 0.6:
            print(f"   ✅ Good differentiation between the two descriptions")
        else:
            print(f"   ⚠️ High similarity - descriptions may be too similar")
    
    success = (locality_mentions == 0 and prop_locality_mentions >= 2)
    
    if success:
        print(f"\n✅ ✅ ✅ LOCALITY DIFFERENTIATION CORRECT!")
    else:
        print(f"\n⚠️ Locality differentiation needs improvement")
    
    print("\n" + "="*80)
    
    return success


def display_company_api_payload(payload):
    """Display what will be sent to company API"""
    print("\n" + "="*80)
    print("📤 COMPANY API PAYLOAD PREVIEW")
    print("="*80)
    
    print(f"\n🆔 Property ID: {payload.get('propid')}")
    print(f"🏢 Property Name: {payload.get('prop_name')}")
    print(f"📍 Locality ID: {payload.get('localityid')}")
    print(f"🏗️ Builder ID: {payload.get('builderid')}")
    
    print(f"\n📝 CONTENT FIELDS:")
    
    content_fields = {
        'prop_desc': 'Property Description',
        'locality_desc': 'Locality Description (NO property name)',
        'prop_locality_desc': 'Property + Locality Description',
        'builder_desc_details': 'Builder Details Description',
        'builder_desc_listing': 'Builder Listing Description'
    }
    
    for field, label in content_fields.items():
        content = payload.get(field)
        if content:
            word_count = count_words(content)
            has_html = '<p>' in str(content)
            print(f"\n   {label}:")
            print(f"      Words: {word_count}")
            print(f"      Format: {'✅ HTML' if has_html else '❌ Not HTML'}")
            
            # Show clean preview
            clean_preview = re.sub(r'<[^>]+>', '', str(content))[:120]
            print(f"      Preview: {clean_preview}...")
        else:
            print(f"\n   {label}: ❌ EMPTY")
    
    # Reviews
    reviews = payload.get('reviews', [])
    print(f"\n⭐ REVIEWS: {len(reviews)} reviews")
    if reviews:
        print(f"   Sample: {reviews[0].get('first_name')} rated {reviews[0].get('rating_value')}/5")
    
    # FAQs
    faqs = payload.get('FAQ', [])
    print(f"\n❓ FAQs: {len(faqs)} FAQs")
    if faqs:
        categories = {}
        for faq in faqs:
            cat = faq.get('category', 'Other')
            categories[cat] = categories.get(cat, 0) + 1
        print(f"   Categories: {categories}")
    
    # Error note
    error = payload.get('error_note')
    if error:
        print(f"\n⚠️ ERROR NOTE: {error}")
    else:
        print(f"\n✅ No errors")
    
    print("\n" + "="*80)


def save_test_results(data: dict, filename: str = OUTPUT_FILE):
    """Save test results to JSON file"""
    try:
        test_results = {
            "test_timestamp": datetime.now().isoformat(),
            "test_property": "Shri Aasra Aditya Apartment",
            "test_property_id": "44599",
            "api_endpoint": TEST_ENDPOINT,
            "status": "success",
            "results": data
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(test_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Test results saved to: {Path(filename).absolute()}")
        return True
    except Exception as e:
        print(f"\n❌ Failed to save results: {str(e)}")
        return False


def run_comprehensive_test():
    """Run comprehensive test with all validations"""
    print("\n" + "🔬 COMPREHENSIVE API TEST" + "\n")
    print("="*80)
    print(f"📍 API Endpoint: {TEST_ENDPOINT}")
    print(f"🏢 Test Property: Shri Aasra Aditya Apartment")
    print(f"🆔 Property ID: 44599")
    print("="*80)
    
    # Check API health
    try:
        print("\n🔍 Checking API health...")
        health = requests.get(f"{API_BASE_URL}/health", timeout=5)
        if health.status_code == 200:
            health_data = health.json()
            print(f"✅ API is healthy")
            print(f"   AI Provider: {health_data.get('ai_provider')}")
            print(f"   AI Model: {health_data.get('ai_model')}")
            print(f"   Smart Validation: {health_data.get('smart_validation')}")
        else:
            print(f"⚠️ API returned status {health.status_code}")
    except Exception as e:
        print(f"❌ Cannot reach API: {str(e)}")
        print("\n💡 Make sure the API is running:")
        print("   python main.py")
        return False
    
    # Send test request
    try:
        print("\n📤 Sending test request...")
        print("⏳ Processing (this may take 3-5 minutes)...")
        print("   - Validating input word counts...")
        print("   - Generating SEO content with OpenAI...")
        print("   - Extracting content sections...")
        print("   - Creating reviews...")
        print("   - Generating FAQs...")
        print("\n⏰ Please wait...\n")
        
        response = requests.post(
            TEST_ENDPOINT,
            json=TEST_INPUT,
            headers={"Content-Type": "application/json"},
            timeout=300
        )
        
        print(f"📨 Response Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ API returned error: {response.text[:500]}")
            return False
        
        result = response.json()
        payload = result.get('payload', {})
        
        if not payload:
            print("❌ No payload in response")
            return False
        
        print("✅ Response received successfully\n")
        
        # Run all validations
        print("\n" + "🔍 RUNNING VALIDATIONS" + "\n")
        
        # New: Check content extraction first
        extraction_valid = check_content_extraction(payload, result)
        
        format_valid = verify_output_format(payload)
        html_valid = validate_html_content(payload)
        locality_valid = check_locality_differentiation(payload)
        
        # Display company API payload
        display_company_api_payload(payload)
        
        # Save results
        save_test_results(result)
        
        # Final summary
        print("\n" + "="*80)
        print("📊 VALIDATION SUMMARY")
        print("="*80)
        
        print(f"\n✅ Content Extraction: {'PASS' if extraction_valid else 'FAIL'}")
        print(f"✅ Output Format Match: {'PASS' if format_valid else 'FAIL'}")
        print(f"✅ HTML Formatting: {'PASS' if html_valid else 'FAIL'}")
        print(f"✅ Locality Differentiation: {'PASS' if locality_valid else 'FAIL'}")
        
        all_passed = extraction_valid and format_valid and html_valid and locality_valid
        
        if all_passed:
            print("\n" + "="*80)
            print("🎉 🎉 🎉 ALL VALIDATIONS PASSED! 🎉 🎉 🎉")
            print("="*80)
            print("\n✅ Your model is working correctly!")
            print("✅ Content extraction is working!")
            print("✅ Output format matches company API requirements!")
            print("✅ Content is in clean HTML format!")
            print("✅ Locality descriptions are properly differentiated!")
            print(f"\n📁 Full results saved to: {OUTPUT_FILE}")
            print("\n💡 Ready to use /process-property endpoint for production!")
        else:
            print("\n" + "="*80)
            print("⚠️ SOME VALIDATIONS FAILED")
            print("="*80)
            
            if not extraction_valid:
                print("\n🔧 FIX NEEDED: Content Extraction")
                print("   1. Update extract_section() in main.py")
                print("   2. Use the improved version with fallback strategies")
                print("   3. Update create_optimized_prompt() to add ### headers")
            
            if not html_valid or not locality_valid:
                print("\n🔧 FIX NEEDED: Content Generation")
                print("   1. Check OpenAI prompt formatting")
                print("   2. Verify HTML output requirements")
                print("   3. Check locality differentiation logic")
        
        return all_passed
        
    except requests.exceptions.Timeout:
        print("❌ Request timed out (>5 minutes)")
        print("💡 This usually means OpenAI is taking too long")
        return False
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "="*80)
    print("🔬 ENHANCED PROPERTY CONTENT GENERATION API TEST")
    print("="*80)
    print("\nThis test will verify:")
    print("  1. ✅ Content extraction from OpenAI response")
    print("  2. ✅ Output format matches company API requirements")
    print("  3. ✅ Content is in clean HTML format (<p> tags)")
    print("  4. ✅ Locality descriptions are properly differentiated")
    print("  5. ✅ All required fields are present and valid")
    print("\n" + "="*80 + "\n")
    
    success = run_comprehensive_test()
    
    print("\n" + "="*80)
    if success:
        print("✅ TEST COMPLETED SUCCESSFULLY - MODEL IS WORKING!")
    else:
        print("❌ TEST FAILED - CHECK ERRORS ABOVE")
    print("="*80 + "\n")
