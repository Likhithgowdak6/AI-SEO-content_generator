# AI-SEO-Content Generator with FAQ Generation

# 🏢 Property Content Generator API

An intelligent, AI-powered API system that automatically generates SEO-optimized property content, enhances locality and developer descriptions, creates realistic customer reviews, and generates contextual FAQs for real estate listings.

## ✨ Features

### 🧠 Smart Content Enhancement
- **Intelligent Content Analysis**: Automatically detects if existing content is sufficient (150+ words for locality, 100+ for developer)
- **Smart Restructuring**: Cleans and optimizes existing rich content instead of regenerating
- **Auto-Generation**: Creates high-quality content when input is insufficient
- **HTML Stripping**: Removes all HTML tags and formats content cleanly
- **P-Tag Wrapping**: Automatically wraps all content fields in `<p>` tags for consistent formatting

### 📝 SEO Content Generation
- **Comprehensive Property Descriptions**: 1500+ word SEO-optimized content
- **Structured Sections**:
  - Overview with key details
  - About the Project (200-250 words)
  - Highlights & Key Features (120-140 words)
  - Amenities categorized by type (180-220 words)
  - Location Benefits (180-220 words)
  - Developer Information (180-220 words)
  - Specifications (80-100 words)
  - Target Audience Analysis (200-250 words)

### ⭐ Review Generation
- **AI-Generated Reviews**: Creates 10 realistic customer reviews
- **Varied Perspectives**: Mix of ratings (1-5 stars) with authentic feedback
- **Contextual Content**: Reviews based on actual property features
- **Random Names**: Uses curated list of 400+ Indian names

### ❓ FAQ Generation (NEW!)
- **Intelligent Q&A**: Generates 8-10 contextual FAQs
- **Category-Based**: Questions across Location, Configuration, Status, Possession, Price, Home Loans, and Other
- **Multiple Answers**: Some FAQs include 1-2 different perspectives
- **Real Names**: Uses authentic Indian names from curated list
- **Property-Specific**: Based on actual property data and SEO content

### 🔄 Automated Processing
- **Background Processing**: Non-blocking async operations
- **Callback Integration**: Automatically sends results to your API endpoint as form data
- **Error Handling**: Robust error management with fallback content
- **Retry Logic**: OpenAI API calls with exponential backoff

---

## 🏗️ Architecture
```
┌─────────────────┐
│   Company API   │ ──POST──> Input Data (JSON)
└─────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────┐
│              main.py (FastAPI Server)                    │
│                                                          │
│  1. Validates incoming data (Pydantic models)           │
│  2. Analyzes content richness (word count)              │
│  3. Calls loc_build.py for enhancement                  │
│  4. Generates SEO content (OpenAI GPT-4o-mini)          │
│  5. Generates reviews (via app.py)                      │
│  6. Generates FAQs with random names                    │
│  7. Wraps all content in <p> tags                       │
│  8. Sends complete output to callback API (form data)   │
└──────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌──────────────────┐ ┌──────────────┐ ┌────────────────┐
│  loc_build.py    │ │   app.py     │ │  Callback API  │
│                  │ │              │ │                │
│ - Analyzes word  │ │ - Generates  │ │ - Receives     │
│   count (150/100)│ │   reviews    │ │   form data    │
│ - Restructures   │ │ - Uses AI    │ │ - Processes    │
│   or generates   │ │   model      │ │   content      │
│ - Returns 4      │ │              │ │                │
│   enhanced fields│ │              │ │                │
└──────────────────┘ └──────────────┘ └────────────────┘
```

---

## 📋 Prerequisites

- Python 3.8+
- FastAPI
- OpenAI API Key (for GPT-4o-mini)
- Required Python packages (see `requirements.txt`)

---

## 🚀 Installation

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/property-content-generator.git
cd property-content-generator
```

### 2. Create virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure API Keys
Edit `main.py` and update:
```python
OPENAI_API_KEY = "your_openai_api_key_here"
COMPANY_CALLBACK_API = "http://your-company-api.com/callback-endpoint"
```

Edit `loc_build.py` (if needed) and update:
```python
# Add your API key if loc_build uses external APIs
```

---

## 🎯 Usage

### Start the Server
```bash
python main.py
```

Server will start at: `http://localhost:8000`

### API Documentation
Access interactive API docs at: `http://localhost:8000/docs`

---

## 📡 API Endpoints

### 1. **POST** `/process-property`
Main endpoint for processing property data in background.

**Request Body:**
```json
{
  "status": "True",
  "result": "successful",
  "prop_info": [
    {
      "propertyID": "47",
      "propertyName": "Klassik Landmark",
      "city_name": "Bangalore",
      "locality_name": "Sarjapur Road",
      "localityID": "5",
      "LocalityDiscription": "<p>HTML content here...</p>",
      "Property_LocalityDiscription": "<p>HTML content here...</p>",
      "BuilderName": "Klassik Enterprises",
      "BuilderID": "57",
      "Status": "Ready to Move",
      "bhk": "3 BHK",
      "min_price": "14900000",
      "max_price": "47000000"
    }
  ],
  "basic_details": [
    {
      "dimension": "11",
      "total_apartments": "590",
      "area_min": "1446",
      "area_max": "4561",
      "PossessionDate": "2016-03-03",
      "propertyType": "Apartments",
      "RERA_ID": "PRM/KA/RERA/1251/446/PR/171015/000760"
    }
  ],
  "amenities": [
    {"Name": "Swimming Pool"},
    {"Name": "Gym"},
    {"Name": "Club House"}
  ],
  "highlights": [
    {"highlight_point": "Grand Spacious Clubhouse"}
  ],
  "developer_info": [
    {
      "BuilderName": "Klassik Enterprises",
      "BuilderID": "57",
      "property_count": "4",
      "founded_year": "2000",
      "builder_details_desc": "<p>Builder details...</p>",
      "builder_listing_desc": "<p>Builder listing info...</p>"
    }
  ]
}
```

**Response:**
```json
{
  "status": true,
  "accepted": true,
  "message": "Request received and data format is valid. Processing in background.",
  "timestamp": "2025-12-04T10:30:45",
  "request_id": "req_1733310645123"
}
```

### 2. **POST** `/generate-manual`
Manual endpoint for immediate results (for testing).

Returns complete formatted output immediately without callback.

### 3. **POST** `/process-property-debug`
Debug endpoint that processes data and sends to callback API with detailed response.

**Response includes:**
- Processing status
- Callback result
- Complete payload
- Payload size
- Timestamp

### 4. **POST** `/test-callback`
Test endpoint to preview what would be sent to callback API without actually sending.

### 5. **GET** `/`
Root endpoint with service information.

**Response:**
```json
{
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
    "locality_desc": "string (wrapped in <p> tags)",
    "prop_locality_desc": "string (wrapped in <p> tags)",
    "builderid": "string",
    "builder_desc_details": "string (wrapped in <p> tags)",
    "builder_desc_listing": "string (wrapped in <p> tags)",
    "reviews": "array",
    "FAQ": "array"
  },
  "callback_api": "http://your-callback-api.com"
}
```

### 6. **GET** `/health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "ai_provider": "OpenAI",
  "ai_model": "gpt-4o-mini",
  "timestamp": "2025-12-04T10:30:45",
  "openai_ready": true,
  "review_generator_ready": true,
  "loc_build_ready": true,
  "faq_generator_ready": true,
  "callback_api": "http://your-callback-api.com"
}
```

---

## 📤 Output Format

### Callback Payload Structure (Sent as Form Data)
```json
{
  "propid": "47",
  "prop_name": "Klassik Landmark",
  
  "prop_desc": "<p>=== OVERVIEW ===</p>\n<p>Project Name: Klassik Landmark...</p>\n<p>=== ABOUT ===</p>\n<p>Klassik Landmark by Klassik Enterprises is...</p>",
  
  "localityid": "5",
  "locality_desc": "<p>Sarjapur Road is part of south-east Bangalore...</p>",
  "prop_locality_desc": "<p>Ever wondered why Sarjapur Road became...</p>",
  
  "builderid": "57",
  "builder_desc_details": "<p>Klassik Enterprises Private Limited is...</p>",
  "builder_desc_listing": "<p>Klassik Enterprises are renowned for...</p>",
  
  "reviews": "[{\"first_name\":\"Aarav\",\"last_name\":\"Singh\",\"date\":\"2025-11-27\",\"rating_value\":4,\"review\":\"The property is decent...\"}]",
  
  "FAQ": "[{\"question\":\"What is the location?\",\"answers\":[{\"first_name\":\"Bindu\",\"answer\":\"Located on Sarjapur Road...\"}],\"first_name\":\"Gowtham\",\"category\":\"Location\"}]",
  
  "error_note": null
}
```

### FAQ Structure
```json
{
  "FAQ": [
    {
      "question": "How is the connectivity to major IT hubs?",
      "answers": [
        {
          "first_name": "Rohit",
          "answer": "Connectivity is great, with multiple routes available."
        }
      ],
      "first_name": "Adarsh",
      "category": "Location"
    },
    {
      "question": "Is the 3BHK configuration spacious?",
      "answers": [
        {
          "first_name": "Sharath",
          "answer": "Yes, the rooms are well-sized."
        }
      ],
      "first_name": "Keerthana",
      "category": "Configuration"
    },
    {
      "question": "Are there any delays in possession?",
      "answers": [
        {
          "first_name": "Shalini",
          "answer": "No delays so far; construction is on schedule."
        },
        {
          "first_name": "Manoj",
          "answer": "Yes, but only minor delays due to monsoon."
        }
      ],
      "first_name": "Harish",
      "category": "Possession"
    }
  ]
}
```

### FAQ Categories
- **Location**: Connectivity, neighborhood, nearby facilities
- **Configuration**: BHK availability, spaciousness
- **Status**: Amenities, maintenance
- **Possession**: Timeline, delays
- **Price**: Starting price, payment plans
- **Home Loans**: Bank approvals, financing options
- **Other**: Security, investment potential

---

## 🔧 Configuration

### Content Enhancement Thresholds

In `main.py`:
```python
def is_content_sufficient(text: str, min_words: int = 150) -> bool:
    """Check if content is detailed enough"""
    # Locality: 150 words minimum
    # Developer: 100 words minimum
```

### Models Used

- **SEO Content Generation**: `gpt-4o-mini` (OpenAI)
- **FAQ Generation**: `gpt-4o-mini` (OpenAI)
- **Content Enhancement**: Configured in `loc_build.py`
- **Review Generation**: Configured in `app.py`

### Names Database

400+ curated Indian names including:
- Traditional names (Aarav, Priya, Rahul, Anjali)
- Regional names (Rakesh, Keerthi, Sudeep, Pavitra)
- Modern names (Vihan, Ishita, Samarth, Kruthika)

---

## 📁 Project Structure
```
property-content-generator/
│
├── main.py                      # Main FastAPI server (v7.0.0)
├── loc_build.py                 # Smart content enhancement module
├── app.py                       # Review generation module
├── requirements.txt             # Python dependencies
├── README.md                    # This file
│
└── [Generated Files]
    ├── *.log                    # Application logs
    └── *.json                   # Debug/test outputs
```

---

## 🎨 How It Works

### Content Enhancement Logic
```
Input Content (with HTML)
     │
     ▼
Strip HTML Tags → Count Words
     │
     ├─── Locality: ≥150 words? ──> RESTRUCTURE (optimize for SEO)
     │         └─── <150 words? ──> GENERATE (create 180-220 words)
     │
     ├─── Developer: ≥100 words? ──> RESTRUCTURE (optimize for SEO)
     │         └─── <100 words? ──> GENERATE (create 180-220 words)
     │
     ▼
Wrap in <p> tags → Return enhanced content
```

### Processing Flow

1. **Receive Data**: API receives property data via POST
2. **Validate**: Validates data against Pydantic models with field aliases
3. **Transform**: Converts company format to internal format
4. **Analyze Content**: 
   - Checks `LocalityDiscription` (150 word threshold)
   - Checks `Property_LocalityDiscription` (150 word threshold)
   - Checks `builder_details_desc` (100 word threshold via alias)
   - Checks `builder_listing_desc` (100 word threshold via alias)
5. **Enhance**: `loc_build.py` processes 4 fields:
   - Returns restructured content if sufficient
   - Generates new content if insufficient
6. **Generate SEO**: Creates comprehensive property description using OpenAI
7. **Generate Reviews**: Creates 10 realistic reviews with random names
8. **Generate FAQs**: Creates 8-10 contextual FAQs with categories
9. **Format Output**: Wraps all text fields in `<p>` tags
10. **Send Callback**: Posts complete output as form data to company API

---

## 🔍 Key Features Explained

### 1. **Intelligent Content Detection**
- Analyzes word count after HTML stripping
- Different thresholds for different content types:
  - Locality descriptions: 150 words
  - Developer descriptions: 100 words
- Separate analysis for each of the 4 fields

### 2. **Smart Restructuring**
- For sufficient content: 
  - Removes HTML tags
  - Removes redundant information
  - Optimizes for SEO keywords
  - Maintains original facts
  - Wraps in clean `<p>` tags

### 3. **Contextual Generation**
- For insufficient content:
  - Uses existing brief content as seed
  - Expands to target word count (180-220 words)
  - Maintains factual accuracy
  - No hallucinations or false information
  - Property-specific details only

### 4. **SEO Optimization**
- Keyword-rich content
- Structured with clear sections
- Natural language flow
- Buyer persona targeting
- Long-form content (1500+ words)

### 5. **FAQ Generation with Real Names**
- Uses curated list of 400+ Indian names
- Ensures unique names per FAQ (no duplicates in same question)
- Generates 8-10 questions across multiple categories
- 1-2 answers per question for varied perspectives
- Contextual answers based on actual property data

### 6. **Automatic P-Tag Wrapping**
All content fields are wrapped in paragraph tags:
- `prop_desc` → Full SEO content in `<p>` tags
- `locality_desc` → Enhanced locality content in `<p>` tags
- `prop_locality_desc` → Enhanced property locality in `<p>` tags
- `builder_desc_details` → Builder details in `<p>` tags
- `builder_desc_listing` → Builder listing info in `<p>` tags

---

## ⚙️ Environment Variables

Optional environment variables:
```bash
# Set callback API URL
export COMPANY_CALLBACK_API="http://192.168.0.144/superadmin/AItasks_Controller/update_Contents"

# Set OpenAI API Key
export OPENAI_API_KEY="sk-proj-your-api-key-here"

# Set port (default: 8000)
export PORT=8000
```

---

## 🐛 Troubleshooting

### Common Issues

#### 1. OpenAI API Errors
**Problem**: `OpenAI API rate limit exceeded` or `OpenAI API error`
**Solution**:
- Check your API key is valid and has credits
- The system has built-in retry logic with exponential backoff
- Wait for rate limits to reset (usually 60 seconds)
- Verify API key in `main.py`

#### 2. Content Enhancer Not Working
**Problem**: `locality_desc` and `prop_locality_desc` are `null`
**Solution**:
- Verify `loc_build.py` exists in the same directory
- Check that input data has `LocalityDiscription` and `Property_LocalityDiscription`
- Review logs for specific errors
- Ensure content has some text (even if brief)

#### 3. Builder Descriptions Are Null
**Problem**: `builder_desc_details` and `builder_desc_listing` are `null`
**Solution**:
- Check that input data has `builder_details_desc` and `builder_listing_desc` fields
- Verify the field aliases are working in Pydantic model
- Ensure `developer_info` array is not empty
- Check if builder descriptions exist in source database

#### 4. Reviews Not Generating
**Problem**: Empty reviews array
**Solution**:
- Verify `app.py` exists and has `generate_reviews_from_text` function
- Check that SEO content was generated successfully
- Review `app.py` logs for errors
- Ensure review generator has proper configuration

#### 5. FAQs Not Generating
**Problem**: Empty FAQ array
**Solution**:
- Check OpenAI API is responding
- Verify SEO content exists (FAQs use it as context)
- Review logs for JSON parsing errors
- Ensure FAQ prompt is receiving property data

#### 6. Callback API Not Receiving Data
**Problem**: Data not reaching company API
**Solution**:
- Verify `COMPANY_CALLBACK_API` URL is correct
- Check network connectivity to callback endpoint
- Review callback API logs for incoming requests
- Test with `/test-callback` endpoint first
- Ensure callback API accepts form data (not JSON)

#### 7. Pydantic Validation Errors
**Problem**: `Validation error: field required`
**Solution**:
- Check incoming JSON structure matches expected format
- Verify all required fields are present
- Review field aliases in `DeveloperInfo` model
- Use `/generate-manual` endpoint to see detailed error messages

---

## 📊 Performance

- **Average Processing Time**: 20-35 seconds per property
  - Content analysis: 1-2 seconds
  - SEO generation: 8-12 seconds
  - Review generation: 5-8 seconds
  - FAQ generation: 6-10 seconds
  - Callback transmission: 1-2 seconds
- **Concurrent Requests**: Supports up to 10 simultaneous requests
- **Content Quality**: SEO-optimized, human-like text
- **Review Authenticity**: Varied ratings (1-5 stars), contextual feedback
- **FAQ Relevance**: Property-specific questions with accurate answers
- **API Rate Limiting**: Built-in retry logic with exponential backoff

---

## 🔐 Security Considerations

### API Key Management
- Never commit API keys to version control
- Use environment variables for sensitive data
- Rotate API keys regularly
- Monitor API usage for anomalies

### Input Validation
- All inputs validated with Pydantic models
- HTML content sanitized before processing
- SQL injection protection (if database integration added)

### Output Sanitization
- HTML tags stripped from user content
- Only safe HTML (`<p>` tags) added by system
- No script injection possible

---

## 📈 Future Enhancements

### Planned Features
- [ ] Multi-language support (Hindi, Tamil, Telugu)
- [ ] Image caption generation for property photos
- [ ] Video script generation for property tours
- [ ] Social media post generation
- [ ] Email campaign content generation
- [ ] Comparison reports between properties
- [ ] Market analysis integration
- [ ] Price prediction based on features
- [ ] Chatbot integration for FAQs

### Potential Improvements
- [ ] Caching layer for faster repeated requests
- [ ] Database integration for content storage
- [ ] Admin dashboard for monitoring
- [ ] A/B testing for content variations
- [ ] User feedback collection
- [ ] Content performance analytics
- [ ] Batch processing endpoint
- [ ] Webhook support for real-time updates

---

## 🤝 Contributing

We welcome contributions! Here's how you can help:

### Development Setup
1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Install development dependencies (`pip install -r requirements-dev.txt`)
4. Make your changes
5. Run tests (`pytest tests/`)
6. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
7. Push to the branch (`git push origin feature/AmazingFeature`)
8. Open a Pull Request

### Code Style
- Follow PEP 8 guidelines
- Use type hints for function parameters
- Add docstrings for all functions
- Write unit tests for new features
- Update README.md for new features

### Areas for Contribution
- Bug fixes
- Performance optimizations
- New AI model integrations
- Documentation improvements
- Test coverage expansion
- Feature enhancements

## 🙏 Acknowledgments

- **OpenAI**: For providing the GPT-4o-mini model API
- **FastAPI**: For the excellent web framework
- **BeautifulSoup**: For HTML parsing capabilities
- **Pydantic**: For robust data validation
- **Uvicorn**: For ASGI server implementation


