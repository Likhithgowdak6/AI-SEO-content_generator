# AI-SEO-content_generator

# 🏢 Property Content Generator API

An intelligent, AI-powered API system that automatically generates SEO-optimized property content, enhances locality and developer descriptions, and creates realistic customer reviews for real estate listings.

## ✨ Features

### 🧠 Smart Content Enhancement
- **Intelligent Content Analysis**: Automatically detects if existing content is sufficient (200+ words)
- **Smart Restructuring**: Cleans and optimizes existing rich content instead of regenerating
- **Auto-Generation**: Creates high-quality 300+ word content when input is insufficient
- **HTML Stripping**: Removes all HTML tags and formats content cleanly

### 📝 SEO Content Generation
- **Comprehensive Property Descriptions**: 1800+ word SEO-optimized content
- **Structured Sections**:
  - Overview with key details
  - About the Project
  - Highlights & Key Features
  - Amenities (categorized)
  - Location Benefits
  - Developer Information
  - Specifications
  - Target Audience Analysis

### ⭐ Review Generation
- **AI-Generated Reviews**: Creates 10 realistic customer reviews
- **Varied Perspectives**: Mix of ratings (4-5 stars) with authentic feedback
- **Contextual Content**: Reviews based on actual property features

### 🔄 Automated Processing
- **Background Processing**: Non-blocking async operations
- **Callback Integration**: Automatically sends results to your API endpoint
- **Error Handling**: Robust error management and logging

---

## 🏗️ Architecture

```
┌─────────────────┐
│   Company API   │ ──POST──> Input Data (JSON)
└─────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│              main.py (FastAPI Server)               │
│                                                     │
│  1. Validates incoming data                        │
│  2. Calls loc_build.py                      │
│  3. Generates SEO content                          │
│  4. Generates reviews (via app.py)                 │
│  5. Sends complete output to callback API          │
└─────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌──────────────────┐ ┌──────────────┐ ┌────────────────┐
│loc_build.py│ │   app.py     │ │  Callback API  │
│                  │ │              │ │                │
│ - Analyzes word  │ │ - Generates  │ │ - Receives     │
│   count          │ │   reviews    │ │   final output │
│ - Passes through │ │ - Uses GROQ  │ │                │
│   or generates   │ │   AI         │ │                │
│ - Returns 4      │ │              │ │                │
│   enhanced fields│ │              │ │                │
└──────────────────┘ └──────────────┘ └────────────────┘
```

---

## 📋 Prerequisites

- Python 3.8+
- FastAPI
- GROQ API Key
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
GROQ_API_KEY = "your_groq_api_key_here"
COMPANY_CALLBACK_API = "https://your-company-api.com/receive-seo-content"
```

Edit `loc_build.py` and update:
```python
GROQ_API_KEY = "your_groq_api_key_here"
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
      "propertyName": "Klassik Landmark",
      "city_name": "Bangalore",
      "locality_name": "Sarjapur Road",
      "LocalityDiscription": "HTML content here...",
      "Property_LocalityDiscription": "HTML content here...",
      "BuilderName": "Klassik Enterprises",
      "Status": "Ready to Move",
      "bhk": "3 BHK",
      "min_price": "14900000",
      "max_price": "47000000"
    }
  ],
  "basic_details": [...],
  "amenities": [...],
  "highlights": [...],
  "developer_info": [...]
}
```

**Response:**
```json
{
  "status": true,
  "accepted": true,
  "message": "Request received and data format is valid. Processing in background.",
  "timestamp": "2024-12-02T10:30:45",
  "request_id": "req_1733134245123"
}
```

### 2. **POST** `/generate-manual`
Manual endpoint for immediate results (for testing).

Returns complete output immediately without callback.

### 3. **GET** `/health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-12-02T10:30:45",
  "groq_ready": true,
  "review_generator_ready": true,
  "loc_build_ready": true,
  "callback_api": "https://your-api.com"
}
```

---

## 📤 Output Format

### Callback Payload Structure

```json
{
  "property_name": "Klassik Landmark",
  
  "enhanced_content": {
    "LocalityDiscription": "Enhanced/original locality content...",
    "Property_LocalityDiscription": "Enhanced/original property locality content...",
    "builder_description": "Enhanced/original builder description...",
    "builder_data_discription": "Enhanced/original detailed builder info..."
  },
  
  "seo_content": "=== OVERVIEW ===\n...\n=== ABOUT ===\n...",
  
  "reviews": [
    {
      "author": "Priya Sharma",
      "rating": 5,
      "review": "Excellent property with great amenities...",
      "date": "2024-11-15"
    }
  ],
  
  "metadata": {
    "builder": "Klassik Enterprises",
    "location": "Sarjapur Road, Bangalore",
    "configurations": ["3 BHK"],
    "word_count": 1850,
    "review_count": 10,
    "locality_generated": false,
    "developer_generated": false,
    "enhanced_content_available": true
  },
  
  "generated_at": "2024-12-02T10:30:45",
  "status": "success"
}
```
## 🔧 Configuration

### Content Enhancement Thresholds

In `loc_build.py`:
```python
WORD_THRESHOLD = 200  # Minimum words to consider content sufficient
TARGET_WORD_COUNT = 300  # Target words for generated content
```

### Models Used

- **Content Enhancement**: `llama-3.3-70b-versatile` (via GROQ)
- **SEO Content**: `llama-3.3-70b-versatile` (via GROQ)
- **Review Generation**: Configured in `app.py`

---

## 📁 Project Structure

```
property-content-generator/
│
├── main.py                      # Main FastAPI server
├── loc_build.py          # Smart content enhancement module
├── app.py                       # Review generation module
├── requirements.txt             # Python dependencies
├── README.md                    # This file
---

## 🎨 How It Works

### Content Enhancement Logic

```
Input Content
     │
     ▼
Count Words (after HTML removal)
     │
     ├─── ≥200 words? ──> PASS THROUGH (clean HTML, return original)
     │
     └─── <200 words? ──> GENERATE (create 300+ word enhanced content)
```

### Processing Flow

1. **Receive Data**: API receives property data via POST
2. **Validate**: Validates data against Pydantic models
3. **Enhance**: `loc_build.py` processes 4 fields:
   - LocalityDiscription
   - Property_LocalityDiscription
   - builder_description
   - builder_data_discription
4. **Generate SEO**: Creates comprehensive property content
5. **Generate Reviews**: Creates 10 realistic reviews
6. **Send Callback**: Posts complete output to your API

---

## 🔍 Key Features Explained

### 1. **Intelligent Content Detection**
- Analyzes word count after HTML stripping
- 200-word threshold for content sufficiency
- Separate analysis for each field

### 2. **Smart Restructuring**
- For sufficient content: Cleans HTML, removes redundancies
- Maintains original information
- Optimizes for SEO without regenerating

### 3. **Contextual Generation**
- For insufficient content: Expands to 300+ words
- Uses existing brief content as seed
- Maintains factual accuracy
- No hallucinations

### 4. **SEO Optimization**
- Keyword-rich content
- Structured with clear sections
- Natural language flow
- Buyer persona targeting

---

## ⚙️ Environment Variables

Optional environment variables:

```bash
# Set callback API URL
export COMPANY_CALLBACK_API="https://your-api.com/callback"

# Set port (default: 8000)
export PORT=8000
```

---

## 🐛 Troubleshooti
### Content enhancer not working
- Verify `loc_build.py` exists in the same directory
- Check GROQ API key is valid
- Review logs for specific errors

### Reviews not generating
- Verify `app.py` exists and has `generate_reviews_from_text` function
- Check review generator configuration

---

## 📊 Performance

- **Average Processing Time**: 15-30 seconds per property
- **Concurrent Requests**: Supports up to 10 simultaneous requests
- **Content Quality**: SEO-optimized, human-like text
- **Review Authenticity**: Varied, contextual, realistic

---

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 🙏 Acknowledgments

- **GROQ**: For providing the AI model API
- **FastAPI**: For the excellent web framework
- **BeautifulSoup**: For HTML parsing
