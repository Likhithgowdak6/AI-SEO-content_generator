# app.py - Review generation module (Gradio removed)
import json
import requests
import random
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

# -------------------- CONFIG --------------------
HF_API_KEY = "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"  # optional: replace with your key
API_URL = "https://api.groq.com/openai/v1/chat/completions"
HEADERS = {"Authorization": f"Bearer {HF_API_KEY}", "Content-Type": "application/json"}

# -------------------- TEXT PARSER --------------------
def parse_text_to_features(raw_text: str) -> dict:
    """
    Parse a multi-section plain-text project description into a features dict.
    Recognizes sections starting with === SECTION NAME ===
    """
    sections = {
        "overview": "",
        "about": "",
        "highlights": "",
        "amenities": "",
        "location": "",
        "specifications": "",
        "lifestyle_scores": "",
        "who": ""
    }
    current = None
    for line in raw_text.splitlines():
        l = line.strip()
        if not l:
            continue
        up = l.upper()
        if up.startswith("=== OVERVIEW"):
            current = "overview"; continue
        if up.startswith("=== ABOUT"):
            current = "about"; continue
        if up.startswith("=== HIGHLIGHTS"):
            current = "highlights"; continue
        if up.startswith("=== AMENITIES"):
            current = "amenities"; continue
        if up.startswith("=== LOCATION"):
            current = "location"; continue
        if up.startswith("=== SPECIFICATIONS"):
            current = "specifications"; continue
        if up.startswith("=== LIFESTYLE"):
            current = "lifestyle_scores"; continue
        if up.startswith("=== WHO"):
            current = "who"; continue
        # Append to current section (if none, accumulate in 'about')
        if current:
            sections[current] += l + " "
        else:
            sections["about"] += l + " "

    # Extract common fields from overview (best-effort)
    overview = sections["overview"]
    features = {
        "property_name": extract_field(overview, "Project Name:") or extract_field(overview, "Project:"),
        "project_name": extract_field(overview, "Project Name:") or extract_field(overview, "Project:"),
        "builder": extract_field(overview, "Builder:"),
        "location": extract_field(overview, "Location:") or sections["location"] or None,
        "city": extract_city(overview),
        "state": extract_state(overview),
        "address": extract_field(overview, "Location:") or None,
        "area": extract_field(overview, "Area Range:"),
        "launch_date": None,
        "possession_date": extract_field(overview, "Possession:"),
        "amenities": sections["amenities"] or sections["highlights"],
        "highlights": sections["highlights"],
        "project_type": "Residential",
        "raw_sections": sections
    }
    return features

def extract_field(text: str, key: str) -> Optional[str]:
    if not text or key not in text:
        return None
    try:
        # split by key then by next line or by " - " etc
        after = text.split(key, 1)[1].strip()
        # stop at double space or two newlines or separators if present
        for sep in ["\n", "  ", " - ", ";"]:
            if sep in after:
                after = after.split(sep, 1)[0].strip()
        return after
    except Exception:
        return None

def extract_city(text: str) -> Optional[str]:
    if not text:
        return None
    t = text.lower()
    if "bangalore" in t or "bengaluru" in t:
        return "Bangalore"
    if "chennai" in t:
        return "Chennai"
    if "hyderabad" in t:
        return "Hyderabad"
    if "mumbai" in t:
        return "Mumbai"
    return None

def extract_state(text: str) -> Optional[str]:
    if not text:
        return None
    t = text.lower()
    if "bangalore" in t or "karnataka" in t:
        return "Karnataka"
    if "chennai" in t or "tamil nadu" in t:
        return "Tamil Nadu"
    if "hyderabad" in t or "telangana" in t:
        return "Telangana"
    if "mumbai" in t or "maharashtra" in t:
        return "Maharashtra"
    return None

# -------------------- REQUIRED FIELD CLEANER --------------------
REQUIRED_FIELDS = {
    "property_name",
    "project_name",
    "location",
    "city",
    "state",
    "address",
    "area",
    "launch_date",
    "possession_date",
    "amenities",
    "highlights",
    "builder",
    "project_type"
}

def clean_input_json(raw: dict) -> dict:
    clean = {}
    for key in REQUIRED_FIELDS:
        clean[key] = raw.get(key)
    return clean

# -------------------- DATE HELPERS --------------------
def normalize_date(date_str: Optional[str]) -> Optional[str]:
    if not date_str:
        return None
    s = str(date_str).strip()
    if len(s) == 4 and s.isdigit():
        return s + "-01-01"
    if len(s) == 7 and s[4] == "-":
        return s + "-01"
    try:
        datetime.fromisoformat(s)
        return s
    except:
        pass
    for fmt in ("%B %Y", "%b %Y", "%d %B %Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(s, fmt)
            return parsed.strftime("%Y-%m-%d")
        except:
            pass
    return s

def parse_date(date_str: Optional[str]) -> Optional[datetime.date]:
    d = normalize_date(date_str)
    if not d:
        return None
    try:
        return datetime.fromisoformat(d).date()
    except:
        return None

# -------------------- REGION DETECTION --------------------
REGION_KEYWORDS = {
    "tamil": ["tamil nadu", "chennai", "coimbatore", "madurai", "trichy", "salem", "vellore"],
    "kannada": ["karnataka", "bengaluru", "bangalore", "mysore", "mangalore"],
    "telugu": ["telangana", "andhra", "hyderabad", "visakhapatnam", "vizag"],
    "hindi": ["delhi", "new delhi", "uttar pradesh", "up", "rajasthan", "madhya pradesh", "punjab", "haryana"],
    "marathi": ["maharashtra", "mumbai", "pune", "nagpur"],
    "bengali": ["west bengal", "kolkata", "howrah"],
    "kerala": ["kerala", "kochi", "kozhikode", "thiruvananthapuram", "trivandrum"],
    "gujarati": ["gujarat", "ahmedabad", "surat", "vadodara"]
}

def detect_region_from_features(features: dict) -> str:
    # features should be a dict — we flatten relevant fields into a string
    if not isinstance(features, dict):
        return "general"
    fields = []
    for k in ("location", "city", "state", "address", "area"):
        v = features.get(k)
        if v:
            fields.append(str(v).lower())
    text = " ".join(fields)
    for region, kws in REGION_KEYWORDS.items():
        for kw in kws:
            if kw in text:
                return region
    return "general"

# -------------------- NAME POOLS --------------------
# (full pools kept as in original - unchanged)
NAMES_BY_REGION = {
    "tamil": {
      "first": [
        "Arun","Karthik","Vijay","Siva","Hari","Prakash","Gowtham","Senthil","Saravanan","Madhan",
        "Raja","Ajith","Murugan","Kabilan","Mugilan","Yuvaraj","Tamil","Dinesh","Praveen","Suriya",
        "Manikandan","Balamurugan","Naveen","Sathish","Ashok","Lokesh","Janarthan","Kiran","Vignesh","Santhosh",
        "Sriram","Aravind","Deepak","Rajkumar","Sathya","Ganesh","Sampath","Ramesh","Anand","Jagan",
        "Nithish","Kalai","Mathesh","Vasudevan","Velmurugan","Marimuthu","Perumal","Sukumaran","Arunachalam","Mayavan",
        "Nirmal","Darshan","Bharath","Shyam","Eswaran","Vetrivel","Tharani","Parthiban","Ilango","Thamizharasan",
        "Pugazh","Abinash","Sathyan","Sathwik","Samuthirakani","Veeramani","Subash","Jeyam","Arivalagan","Harikrishnan",
        "Logesh","Sundar","Udhay","Arul","Aruldoss","Bhuvan","Dev","Ezhil","Vallavan","Nalan",
        "Agni","Kavin","Mithran","Rithik","Sudhakar","Sanjay","Sagunthala","Shankaran","Guhan","Tharun",
        "Monish","Aathish","Aathmika","Yalini","Preethi","Rithanya","Swathi","Kaviya","Nandini","Harini",
        "Divya","Mahalakshmi","Meenakshi","Kowsalya","Anushka","Keerthana","Ishwarya","Lakshmi","Dhivya","Vaishnavi",
        "Sangeetha","Yogeshwari","Sahana","Sujatha","Usha","Bhuvana","Jayanthi","Sowmiya","Ilakya","Abarna",
        "Priya","Nilofer","Mahima","Kritika","Kalyani","Madhumitha","Harshita","Abirami","Kasthuri","Anitha",
        "Revathi","Ramya","Sandhiya","Vishnu Priya","Sreeja","Shobana","Janani","Hemamalini","Poorani","Ilamathi",
        "Thamarai","Padmavathi","Gomathi","Manimegalai","Karpagam","Muthulakshmi","Devayani","Amudha","Selvi","Kalaivani"
      ],
      "last": [
        "Iyer","Raman","Natarajan","Subramanian","Krishnan","Reddy","Pillai","Ganesan","Parthasarathy","Sivakumar",
        "Venkatesan","Arumugam","Balasubramanian","Chandrasekar","Sundaram","Rajendran","Kandasamy","Muthuraman","Palanisamy","Veerappan",
        "Manickam","Somasundaram","Jayakumar","Sankar","Murugesan","Rathinam","Lakshmanan","Karthikeyan","Thangavel","Mayilvahanan",
        "Selvaraj","Periyasamy","Elangovan","Velusamy","Sivamani","Mahadevan","Karunanidhi","Kaveriappan","Ravichandran","Kuppuswamy",
        "Nellaiappan","Sethupathi","Rajarathinam","Chidambaram","Pillaiyar","Thirumurugan","Thirumalai","Palaniappan","Azhagappan","Rajasekaran",
        "Gopalakrishnan","Baskaran","Ayyappan","Kathiresan","Jayapal","Muthukaruppan","Anbazhagan","Pasupathy","Paari","Valluvan",
        "Nallathambi","Alagarsamy","Pazhani","Kumaran","Sakthivel","Mathivanan","Jagadeesan","Sethupathi","Nambi","Kariappan",
        "Muthukumar","Rengarajan","Manoharan","Kaliyaperumal","Vadivel","Ayyan","Muthayya","Balakrishnan","Marimuthu","Kothandapani",
        "Dhandapani","Palanisami","Sivaraman","Sivathanu","Aravindaraj","Pugazhendhi","Periyannan","Uthayakumar","Arunmozhi","Rajalingam",
        "Karthiravan","Vijayaraghavan","Thiyagarajan","Aathimoolam","Palpandian","Sankaralingam","Sivaprakash","Rajabalan","Sivagnanam","Sornam",
        "Somashekar","Muthukrishnan","Duraisamy","Manokaran","Kuttimani","Ramasamy","Natarajar","Kulanthai","Kaverisami","Aandavar",
        "Karuppasamy","Pandurangan","Thangaraj","Sakthivelan","Sampathkumar","Sivanesan","Arangannal","Gunasekaran","Ramanathan","Sundaralingam",
        "Palanivel","Singaram","Veluchamy","Sivapalan","Ilango","Mayilsamy","Azhagan","Sundaresan","Kottaisamy","Kathiravan",
        "Veerasamy","Rasappan","Ponnusamy","Chockalingam","Thillainathan","Sargunam","Vadamalai","Thenappan","Kaliyannan","Arulmani"
      ]
    },
    "kannada": {
      "first": [
        "Rakesh","Darshan","Manjunath","Prajwal","Harsha","Keerthi","Anitha","Bhavana","Rohith","Chandan",
        "Vijay","Sharath","Rakshit","Yogesh","Kiran","Nandan","Vishal","Pradeep","Lokesh","Raghavendra",
        "Narayan","Sudeep","Srinivas","Deekshith","Ganesh","Mahesh","Naveen","Ramesh","Sanjay","Sunil",
        "Venkatesh","Yatish","Chethan","Dinesh","Abhishek","Aravind","Ajay","Puneeth","Rajesh","Raghunath",
        "Basavaraj","Mallikarjun","Ravikiran","Uday","Girish","Ravi","Rajkumar","Prem","Sohail","Sharan",
        "Anil","Gowtham","Sathish","Madhu","Sharadha","Pooja","Nandini","Namratha","Chaithra","Aparna",
        "Latha","Sudha","Roopa","Deepa","Meghana","Harini","Kavya","Ranjitha","Aishwarya","Shruthi",
        "Sahana","Prarthana","Shwetha","Geetha","Pavitra","Sushma","Divya","Sreeja","Nayana","Suchitra",
        "Vidya","Revathi","Jeevitha","Rachana","Shruthi","Pramila","Bhagya","Anagha","Shilpa","Anusree",
        "Pallavi","Hemalatha","Savitha","Sangeetha","Ananya","Madhuri","Sandhya","Varsha","Keerthana","Bindu",
        "Shashank","Jayanth","Chiranjeevi","Vikas","Rakshith","Sudeepth","Prajna","Vaishnavi","Shree","Mahima",
        "Chaitanya","Arpita","Tejas","Anirudh","Samarth","Sourabh","Anoop","Abhinav","Varun","Sanath",
        "Kousthubh","Madhav","Tarun","Vinay","Rohin","Nitin","Suraj","Akarsh","Mohan","Yeshwanth",
        "Sujith","Akash","Sharanraj","Bharath","Arun","Rajath","Pranav","Yogendra","Chandana","Niranjan",
        "Jnanesh","Dhanush","Kruthika","Sharmila","Mridula","Supriya","Deepthi","Sahithi","Devika","Ishita"
      ],
      "last": [
        "Gowda","Shetty","Hegde","Urs","Desai","Poojary","Nayak","Rao","Pai","Kamat",
        "Acharya","Bhat","Hebbar","Kulkarni","Koppal","Hiremath","Banakar","Patil","Angadi","Javali",
        "Moger","Kamath","Shenoy","Shivanna","Gundappa","Byrappa","Swamy","Raikar","Gowdru","Malnad",
        "Devadiga","Apte","Malagi","Sajjan","Sunagar","Naik","Kori","Hallur","Doddamani","Jadhav",
        "Galagali","Yelur","Agalakote","Hiriyur","Rangappa","Sadashiva","Rameshappa","Eshwarappa","Hanumanthappa","Basappa",
        "Mallappa","Krishnappa","Channappa","Shankaranarayan","Nagaraj","Somanna","Veerappa","Mahadevappa","Gurumurthy","Devendrappa",
        "Kalyanappa","Kittur","Gajendragadkar","Bagalkot","Talwar","Hiremath","Hosamani","Savanur","Gadagkar","Honnappa",
        "Pattar","Gokak","Mudhol","Kudachi","Hubballi","Dharwadkar","Ilkal","Chitradurga","Bhadravati","Manvi",
        "Srinath","Kabbur","Bommai","Harogadde","Sullia","Siddappa","Halappa","Doddaiah","Gollar","Bhovi",
        "Dombar","Bendre","Shivapur","Sunkad","Sankannavar","Anegondi","Hosakote","Gundurao","Doreswamy","Jayanna",
        "Lakshmana","Chikkanna","Suryanarayana","Govindappa","Narasimha","Vadiraj","Chandrappa","Shivappa","Hanumappa","Vadde",
        "Kodgi","Malur","Kakkilaya","Ballal","Kotian","Surathkal","Maroli","Pandit","Bharadwaj","Sringeri",
        "Achar","Somayaji","Shankara","Kotekar","Padmanabha","Gopalakrishnan","Gundappa","Veerabhadra","Mallesh","Keshavmurthy",
        "Ranganath","LakshmiNarayan","Manjunath","SrinivasMurthy","Chikkegowda","Boja","Bogar","Honnali","Kannur","Navada"
      ]
    },
    "telugu": {
      "first": [
        "Aadhav","Aaditya","Aakash","Abhinav","Abhiram","Aditya","Ajay","Akash",
        "Akhil","Amarnath","Amogh","Anand","Ananya","Anisha","Anil","Anirudh",
        "Anitha","Anjana","Anju","Ankitha","Anudeep","Anusha","Anvesh","Aparna",
        "Aravind","Arjun","Arpita","Ashok","Aswini","Avinash","Balaji","Bharath",
        "Bhargav","Bhaskar","Bhuvana","Charan","Chaitanya","Chandana","Chandra",
        "Chandu","Chandrika","Daksh","Damini","Darshan","Deepak","Deepti","Deepshika",
        "Dev","Devika","Dhanush","Dharani","Dharma","Dheeraj","Divakar","Divya",
        "Durga","Ganesh","Gauri","Gayathri","Girish","Gopi","Govind","Gowtham",
        "Harika","Harini","Haripriya","Harsha","Harshita","Hemanth","Hima","Himaja",
        "Hitesh","Indira","Indu","Ishan","Jagadeesh","Jagannath","Jahnavi","Jeevan",
        "Jishnu","John","Joshua","Jyothi","Kalyan","Kamal","Kamesh","Karthik",
        "Keerthi","Kiran","Kishore","Kranti","Krishna","Krishnaveni","Kumar",
        "Lakshmi","Lalitha","Lavanya","Laya","Lohitha","Lokesh","Madhavi","Madhav",
        "Mahati","Mahesh","Manasa","Mani","Manisha","Manoj","Meena","Meenakshi",
        "Meghana","Mohan","Mounika","Murali","Nagamani","Nagarjuna","Naresh",
        "Navya","Nikhil","Nikitha","Nirmala","Nitin","Padma","Pallavi","Pandu",
        "Pavan","Phani","Pradeep","Pragathi","Prakash","Pranathi","Pranay","Prasanna",
        "Pratap","Preeti","Prem","Puja","Purushotham","Rahul","Raj","Raju","Ram",
        "Ramakrishna","Ramakrishnan","Ramesh","Ramya","Ranjith","Raviteja","Rekha",
        "Rishi","Roja","Sai","Saikiran","Sailaja","Sairam","Sandeep","Sandhya",
        "Sangitha","Sanjay","Sanketh","Sanket","Sankar","Saritha","Satish","Savitha",
        "Sekhar","Sesha","Sharanya","Shashi","Sheetal","Shilpa","Shiva","Shravani",
        "Shyam","Sindhu","Sirisha","Sita","Sneha","Srinivas","Srinidhi","Srujan",
        "Sruthi","Subhash","Sudheer","Suhas","Supriya","Suresh","Sushma","Swathi",
        "Tarun","Teja","Tejaswini","Tharun","Uma","Uday","Ujwala","Upendra",
        "Vaishnavi","Vamsi","Varalakshmi","Varma","Vasudha","Vasu","Venkatesh",
        "Venkat","Vennela","Vidya","Vijaya","Vijay","Vinay","Vinitha","Vishnu",
        "Vishnuvardhan","Yamini","Yashwanth","Yogesh"
      ],
      "last": [
        "Achu","Adabala","Adapala","Akula","Alavala","Aluri","Annadata","Are",
        "Arigela","Avvaru","Bairi","Balaga","Bandi","Banoth","Bathina","Billa",
        "Bingi","Boggarapu","Bommakanti","Bonthala","Boyapati","Buddiga","Bujji",
        "Chada","Chakilam","Challa","Chandaka","Chandupatla","Chappidi","Chavva",
        "Chebrolu","Chennuru","Cherukuri","Cheruvu","Chillakuru","Chimakurthy",
        "Chinthakindi","Chodavarapu","Chokkakula","Chowdary","Chunduru","Dalavai",
        "Darapu","Desabattuni","Devabhaktuni","Dharmana","Dhulipala","Dhulipudi",
        "Dhulipudi","Dindigala","Donepudi","Donthu","Duggineni","Duggirala",
        "Duvvuri","Edem","Ediga","Ediga","Eluri","Emmadi","Eppa","Eragam",
        "Errabolu","Erram","Eshwar","Gangula","Ganjam","Garlapati","Gattu","Geddam",
        "Gollapalli","Gona","Gonuguntla","Goparaju","Gopisetty","Gorrela","Gosala",
        "Gottapalli","Gowru","Gudapati","Gudipati","Gudur","Gumma","Gummadi",
        "Guntaka","Guntaka","Guntupalli","Gurram","Gurrapu","Indukuri","Inguva",
        "Jadala","Jakkula","Jampani","Jangala","Janjam","Jannu","Jasti","Javvaji",
        "Jeedigunta","Jinka","Jonnalagadda","Jonnala","Junnuri","Kacham","Kadiyala",
        "Kakumanu","Kalagara","Kalapala","Kalidindi","Kalluri","Kamakala","Kandala",
        "Kanjarla","Kankipati","Kanneganti","Kanumuri","Karri","Kasula","Katta",
        "Kattamuri","Katkam","Kattamanchu","Kavuri","Kesineni","Kesireddy","Kethireddy",
        "Kilaru","Kilpadi","Kommana","Kommu","Kondapuram","Konduri","Kopparapu",
        "Kotagiri","Kothapalli","Kothapeta","Koya","Kuncham","Kuravi","Kurapati",
        "Kurella","Kurra","Lagudu","Lanka","Lankapalli","Lavu","Lekkala","Lingam",
        "Macha","Macharla","Madala","Madhiri","Mahankali","Makineni","Manchala",
        "Mandadi","Manda","Mandava","Maram","Maramreddy","Medapati","Medishetti",
        "Meduri","Megeri","Mekala","Mekapothu","Mekapudi","Mekala","Menneni","Mikkili",
        "Mittapalli","Mitta","Mogulla","Mohiddin","Motupalli","Mudhiraj","Mulakala",
        "Muppalla","Mupparaju","Muppidi","Musunuri","Nadimpalli","Nadella","Nagaraju",
        "Nageshwara","Nagula","Naini","Nallapati","Nallamothu","Nallapu","Namala",
        "Namani","Nannapaneni","Naragam","Naraparaju","Narava","Naredla","Narreddy",
        "Narra","Navuluri","Nekkanti","Nemani","Netha","Nidamarthi","Nidudavolu",
        "Nimmagadda","Nimmakayala","Nippani","Nukala","Obulam","Oleti","Ollala",
        "Padamata","Padamata","Padmaraju","Pakala","Pala","Paladugu","Paleti",
        "Palivela","Pamarthi","Pamu","Panabaka","Panda","Pandiri","Pandranki",
        "Pappu","Paradesi","Parekh","Parimi","Parvathaneni","Parvathala","Pasala",
        "Pasupuleti","Pedaballi","Peddi","PeddiReddy","Peketi","Penmetsa","Peram",
        "Pidakala","Pillalamarri","Pinisetti","Pinnamaneni","Pinninti","Pinnamaraju",
        "Pola","Polavarapu","Polisetti","Ponnada","Ponnapu","Ponnuri","Poranki",
        "Posina","Potlapalli","Prathipati","Pudisetti","Pulipati","Pullagura",
        "Pusapati","Putta","Pydipalli","Pydi","Rachakonda","Racharla","Rajamouli",
        "Rajula","Ramakanth","Ramana","Ramineni","Ramireddy","Rangineni","Rao",
        "Rasala","Rashinkar","Ravipati","Ravuru","Rayala","Rayudu","Reddy","Rupala",
        "Sabbella","Sabbi","Saddala","Saggam","Saivardhan","Sajja","Saladi","Samala",
        "Sampath","Sanapala","Sangala","Sanivarapu","Sanke","Sankineni","Sannam",
        "Santara","Sareddy","Saripalli","Satla","Satti","Seepana","Sekhar","Seka",
        "Settipalli","Shaik","Shanigaram","Siddineni","Singaraju","Singu","Sirasanambati",
        "Siri","Siva","Sivaram","Soma","Somaraju","Sommala","Sontha","Sreeram",
        "Srirangam","Sunkara","Sureddi","Surpala","Suryadevara","Tadikonda","Talari",
        "Tapi","Tatha","Thallam","Thandra","Thati","Thokala","Thonangi","Thota",
        "Thummala","Togati","Tumuluri","Uppalapati","Uppala","Uppara","Uyyala",
        "Vadde","Vaddadi","Vaka","Vakada","Vakkalanka","Valaboju","Valiveti",
        "Vallabhaneni","Vanam","Vangala","Vangapalli","Vankayala","Vannemreddy",
        "Vantala","Varikuti","Vasanta","Vavilala","Vecha","Vedantham","Velagapudi",
        "Velamuri","Velpula","Vemana","VemanaReddy","Vemuri","Vennam","Vepuri",
        "Vijjuluri","Vinnakota","Viral","Virupaksha","Viswanadha","Vogeti","Yadla",
        "Yedla","Yellamraju","Yellapragada","Yerra","Yerramilli","Yerramsetti"
      ]
    },
    "hindi": {
      "first": [
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
        "Vishnu","Vishwam","Vivek","Yash","Yogesh"
      ],
      "last": [
        "Agarwal","Agnihotri","Ahluwalia","Ahuja","Awasthi","Bajaj","Bakshi",
        "Bali","Bansal","Baranwal","Basu","Batham","Bedi","Beg","Behra","Benipuri",
        "Bhagat","Bhardwaj","Bharti","Bhasin","Bhatia","Bhatnagar","Bhatt","Bhavsar",
        "Bisen","Bisht","Biyani","Bora","Bose","Chadha","Chakraborty","Chandrakar",
        "Chandravanshi","Chauhan","Chhabra","Chhillar","Chopra","Choudhary",
        "Chowdhury","Dabas","Dalal","Dalmia","Dandekar","Das","Dasgupta",
        "Dave","Dayal","Deb","Devgan","Devnath","Dewan","Dey","Dhaka","Dhami",
        "Dhamija","Dhand","Dhankar","Dhar","Dhawan","Dhingra","Dholakia",
        "Dhoot","Dixit","Dua","Dubey","Duggal","Dutt","Dutta","Gadia","Gahlot",
        "Gajjar","Gandhi","Garg","Gautam","Gehlot","Gera","Ghai","Ghosh","Girdhar",
        "Goel","Gogia","Gokhale","Goswami","Goyal","Grover","Gulati","Gupta",
        "Haldar","Handa","Handoo","Harjai","Hegde","Hooda","Hussain","Jadhav",
        "Jaggi","Jain","Jakhar","Jangid","Jha","Jhala","Jhaveri","Joshi","Juyal",
        "Kadakia","Kaila","Kaith","Kalra","Kamboj","Kapadia","Kapoor","Karwal",
        "Kasera","Kashyap","Kathuria","Kaul","Kedia","Kejriwal","Khalsa","Kharbanda",
        "Khatri","Khattar","Khandelwal","Khanna","Khoja","Kochhar","Kohli",
        "Kotia","Krishnan","Kukreja","Kumar","Lal","Lamba","Lohia","Luthra","Madan",
        "Maharaj","Maheshwari","Malhotra","Malviya","Manchanda","Mandar","Maniar",
        "Manral","Mathur","Meena","Mehta","Mehrotra","Mittal","Modi","Monga",
        "Moolchandani","Moorjani","Muley","Mundra","Nagpal","Nahar","Nair",
        "Nanda","Narayan","Narula","Nath","Nayak","Nigam","Ojha","Pachauri","Pahuja",
        "Paliwal","Panicker","Pandey","Pandit","Pansare","Parekh","Parikh",
        "Parmar","Parwal","Pasi","Pateriya","Pathak","Patil","Patwari","Phadke",
        "Pillai","Poddar","Pradhan","Prakash","Puri","Purohit","Raghav","Rai",
        "Rajput","Rana","Rathod","Rathore","Rawal","Raza","Reddy","Rishi","Rizvi",
        "Roshan","Roy","Sachan","Sachdeva","Sadhu","Sagar","Sah","Sahu","Saini",
        "Saksena","Salvi","Sangwan","Sankhla","Sansi","Sanya","Sarin","Sarkar",
        "Sarma","Sarraf","Saxena","Sehgal","Sen","Shah","Shahu","Shandilya","Shanbag",
        "Sharma","Shekhar","Shetty","Shinde","Shukla","Sikdar","Singh","Sinha",
        "Solanki","Somvanshi","Soni","Sood","Srinivas","Srivastava","Sundar",
        "Sur","Tandon","Tanwar","Tewari","Thakur","Thomas","Tiwari","Tomar",
        "Trivedi","Tyagi","Upadhyay","Vaish","Vashishtha","Vasudevan","Verma",
        "Vohra","Yadav","Yogi","Yohannan"
      ]
    },
    "kerala": {
      "first": [
        "Akhil","Vineeth","Anu","Deepa","Manu","Sreedevi","Arun","Ajith","Anjali","Athira",
        "Aparna","Amal","Anand","Anitha","Arya","Asha","Aswin","Abhijith","Abhirami","Abin",
        "Ajeesh","Akhila","Akhilesh","Albin","Aleena","Alfiya","Amala","Ameya","Amritha",
        "Anagha","Anandhu","Anikha","Anila","Anish","Anju","Ankitha","Anson","Anu Mol",
        "Anwar","Arathi","Arjun","Arsha","Arshad","Aryan","Asif","Aslam","Aswathy","Athul",
        "Avani","Basil","Bency","Beno","Blessy","Celine","Chandni","Chithra","Christy",
        "Ciby","Cyril","Darsana","Darshak","David","Devika","Devu","Dhanush","Dhwani",
        "Diya","Donna","Dona","Dony","Dulquer","Ebin","Eldho","Elizabeth","Emil","Enosh",
        "Esha","Faizal","Fahad","Farhan","Farzana","Feba","Femy","Fida","Firoz","Frincy",
        "Gayathri","Gautham","Geethu","Geena","Gijo","Gini","Gireesh","Gokul","Greeshma",
        "Haritha","Hari","Harish","Haseena","Hiba","Hisham","Hriday","Ibrahim","Indu",
        "Isaac","Isha","Jaison","Jaseena","Jasim","Jasmin","Jaya","Jayakrishnan","Jayalakshmi",
        "Jeeva","Jenifer","Jeril","Jerin","Jesna","Jibin","Jim","Jincy","Jino","Jishnu",
        "Jithin","Joel","Johan","Jomol","Jomon","Joseph","Joshwa","Joyal","Jyothi",
        "Kachappilly","Kamal","Kannan","Karthika","Karthik","Keerthana","Kevin","Kiran",
        "Kripa","Krishna","Kumari","Kunjumol","Lakshmi","Laya","Leo","Liya","Liyaqath",
        "Lincy","Lino","Liya","Liya Mariam","Madhav","Madhuri","Mahesh","Malavika",
        "Manoj","Manasa","Manoj","Maria","Marina","Mariya","Maya","Meera","Meenu",
        "Melvin","Merin","Midhun","Mishal","Mohan","Muhammad","Mujeeb","Mukesh","Muthu",
        "Mythili","Nabiha","Nadirsha","Naina","Nandana","Nandhu","Nasrin","Nazim","Neenu",
        "Neeraj","Nikhil","Nimisha","Nithin","Niya","Noel","Nora","Nourin","Noufal",
        "Pallavi","Paul","Pavithra","Pooja","Prabha","Pradeep","Pranav","Pranjal",
        "Prashanth","Preeti","Priya","Rahul","Raj","Rajan","Rakesh","Ram","Raman",
        "Remya","Reshma","Rehna","Rehan","Rhea","Rishi","Riya","Robin","Rona","Roshan",
        "Safa","Sagar","Saif","Salim","Salu","Sana","Sandhya","Sangeeth","Sanju","Sanjana",
        "Santhosh","Sanu","Saraswathi","Sarath","Sarika","Seema","Shabana","Shaheen",
        "Shaiju","Shalini","Shan","Shane","Shani","Shanavas","Shani","Sharon","Sheela",
        "Sherin","Shibin","Shifa","Shiji","Shilpa","Shine","Shiva","Shruthi","Shyam",
        "Sneha","Soumya","Stebin","Steffi","Subin","Suhail","Suhana","Sujith","Sukanya",
        "Sunil","Surya","Swapna","Thara","Thomas","Tintu","Tony","Tracy","Vani","Varun",
        "Vidya","Vijay","Vikram","Vineetha","Vishnu","Yadu","Yaseen","Zeba","Zerin"
      ],
      "last": [
        "Nair","Menon","Pillai","Varma","Kurup","Panicker","Warrier","Namboothiri","Sharma","Rao",
        "Kartha","Marar","Kaimal","Achari","Maliackal","Kochumann","Pulickal","Cherian","Muthalaly",
        "Ittycheria","Kizhakke","Palat","Kottarathil","Tharakan","Chirayath","Vadakkethil","Velayudhan",
        "Cheeran","Moothedan","Chandran","Balakrishnan","Gopalakrishnan","Narayanan","Sankar","Sasidharan",
        "Rajan","Sukumaran","Ramachandran","Haridas","Bhat","Gopinathan","Govind","Koshy","Kurian",
        "Pappachan","Mathew","Mathewkutty","Varghese","Johny","Varkey","Idicula","Cheruvally","Kochuparambil",
        "Pullampallil","Kolenchery","Iype","Akkara","Oommen","Chacko","Palathingal","Punnakuzhy","Thekkedath",
        "Perumpally","Vadakkan","Padiyath","Thachara","Kunnath","Thekkumthala","Kandoth","Nalankal","Kottayam",
        "Parayil","Moothedath","Nedungadi","Thampy","Thampi","Mavilayi","Kilimanoor","Cherakkal","Koodathil",
        "Cheruthazham","Kollam","Anjilimoottil","Kancheril","Olickal","Padiyil","Edathil","Elayidom","Paleri",
        "Kizhakkeyil","Manappally","Kadakkal","Kuruva","Kadalayi","Peringala","Kakkad","Kuzhivelil","Vattoli",
        "Aloor","Alunkal","Anchery","Arangath","Arackal","Arayampuram","Ayrookuzhi","Cherukara","Chettiar",
        "Chirayil","Edayil","Edappilly","Eliyath","Eruthickal","Ettukudukka","Kadappuram","Kadavil","Kallupurakkal",
        "Kanjirathinkal","Karukappadath","Karumathil","Kaveripadam","Kizhissery","Koipuram","Kolady","Konnackal",
        "Konthuruthy","Koonan","Koottummel","Kottalil","Koyipuram","Kudiyirickal","Kunjukrishnan","Kuruvilla",
        "Kuzhippallil","Madhavan","Madathil","Mavunkal","Meledam","Mukkam","Mundackal","Muringayil","Muttil",
        "Nedumangad","Pallithazhathu","Pallikkara","Pallivathukkal","Parameswaran","Pattathil","Payyanur","Perinchery",
        "Peringodan","Pillaveetil","Pulimoottil","Puthenpurackal","Rajappan","Raveendran","Sadananadan","Sankaran",
        "Sankaranarayanan","Sebastian","Sreenivasan","Sukumara","Thankappan","Thangaserry","Thattathil","Thayyil",
        "Thengumthara","Thirunilath","Thrikkovil","Tomy","Unnikrishnan","Vadakethil","Valiyaveetil","Varghese",
        "Vattakuzhy","Veluthur","Vengal","Vettikkuzhy","Vijayan","Vinod","Vishwanathan","Yoosuf"
      ]
    },
    "general": {
      "first": [
        "Aarav","Vivaan","Kabir","Arjun","Atharv","Ishaan","Reyansh","Advik","Vihaan","Krish",
        "Ritwik","Dev","Harsh","Naman","Laksh","Shaurya","Kunal","Yash","Varun","Samar",
        "Ayan","Tanmay","Parth","Abhinav","Pranav","Siddharth","Rohan","Tejas","Aadesh","Aakash",
        "Amit","Ansh","Arnav","Aryan","Daksh","Darsh","Gautam","Hrithik","Jatin","Kartik",
        "Manav","Neil","Nitin","Om","Rachit","Rajat","Rishabh","Rishi","Rudra","Sahil",
        "Sameer","Samarth","Sandeep","Sanjay","Saurabh","Tanish","Ujjwal","Ved","Yuvraj","Zayan",
        "Aisha","Anaya","Anika","Anjali","Avni","Charvi","Diya","Eesha","Ira","Isha",
        "Jhanvi","Kashish","Khushi","Kiara","Lavanya","Mahima","Meera","Mishka","Myra","Navya",
        "Nidhi","Nikita","Palak","Pragya","Prerna","Radhika","Rhea","Riddhi","Riya","Saanvi"
      ],
      "last": [
        "Sharma","Verma","Singh","Chauhan","Tiwari","Shukla","Mishra","Pandey","Srivastava","Saxena",
        "Kapoor","Khanna","Mehra","Bedi","Sethi","Malhotra","Arora","Anand","Sibal","Grover",
        "Patel","Shah","Mehta","Desai","Trivedi","Joshi","Gandhi","Bhatt","Pathak","Solanki",
        "Rao","Iyer","Iyengar","Menon","Pillai","Nair","Reddy","Naidu","Shetty","Gowda"
      ]
    }
}

def generate_unique_name(used_first: set, region: str) -> str:
    region_pool = NAMES_BY_REGION.get(region, NAMES_BY_REGION["general"])
    firsts = region_pool["first"]
    lasts = region_pool["last"]
    available = [f for f in firsts if f not in used_first]
    if not available:
        f = random.choice(firsts)
        l = random.choice(lasts)
        return f"{f}{random.randint(10,99)} {l}"
    f = random.choice(available)
    used_first.add(f)
    l = random.choice(lasts)
    return f"{f} {l}"

# -------------------- UNIQUE REVIEW DATE --------------------
def random_unique_review_date(launch_date: Optional[str], used_dates: set) -> str:
    launch = parse_date(launch_date)
    today = datetime.now().date()
    if not launch or launch > today:
        launch = today - timedelta(days=60)
    delta = (today - launch).days
    if delta < 1:
        return today.strftime("%Y-%m-%d")
    attempts = 0
    while attempts < 200:
        d = launch + timedelta(days=random.randint(0, delta))
        s = d.strftime("%Y-%m-%d")
        if s not in used_dates:
            used_dates.add(s)
            return s
        attempts += 1
    return today.strftime("%Y-%m-%d")

# -------------------- HF CALL (safe) --------------------
def call_hf(prompt: str, max_tokens: int = 140) -> Optional[str]:
    # If no HF key, gracefully return None and use fallback
    if not HF_API_KEY:
        return None
    try:
        payload = {
            "model":"llama-3.3-70b-versatile",
            "messages":[{"role":"user","content":prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.8
        }
        r = requests.post(API_URL, headers=HEADERS, json=payload, timeout=20)
        j = r.json()
        return j.get("choices", [{}])[0].get("message", {}).get("content")
    except Exception:
        return None

# -------------------- LANGUAGE PROMPTS --------------------
LANG_PROMPTS = {
    "tamil": "Write the review ONLY using English letters. Do NOT mix other languages. Keep 2-3 sentences.",
    "kannada": "Write the review ONLY using English letters. Do NOT mix languages. Keep 2-3 sentences.",
    "telugu": "Write the review ONLY using English letters. Do NOT mix languages. Keep 2-3 sentences.",
    "hindi": "Write the review ONLY using English letters. Do NOT mix other languages. Keep 2-3 sentences.",
    "marathi": "Write the review ONLY using English letters. Keep 2-3 sentences.",
    "bengali": "Write the review ONLY using English letters. Keep 2-3 sentences.",
    "kerala": "Write the review ONLY using English letters. Keep 2-3 sentences.",
    "gujarati": "Write the review ONLY using English letters. Keep 2-3 sentences.",
    "general": "Write the review in simple Indian English. Keep 2-3 sentences."
}

# -------------------- MODE DECISION --------------------
def decide_review_mode(launch_date_str: Optional[str], possession_date_str: Optional[str]) -> str:
    today = datetime.now().date()
    launch = parse_date(launch_date_str)
    possession = parse_date(possession_date_str)
    if launch and launch == today:
        return "locality"
    if possession and possession == today:
        return "hand_over"
    if possession and today > possession:
        return "amenities"
    if possession and today < possession:
        return "under_construction"
    return "general"

# -------------------- SENTIMENT -> RATING --------------------
POSITIVE_WORDS = {"good","great","excellent","love","nice","amazing","comfortable","super"}
NEGATIVE_WORDS = {"bad","poor","noisy","dirty","delay","slow","problem","issue","disappointed"}

def rating_from_text(review_text: str) -> (int,str):
    txt = (review_text or "").lower()
    pos = any(w in txt for w in POSITIVE_WORDS)
    neg = any(w in txt for w in NEGATIVE_WORDS)
    if pos and not neg:
        score = random.choice([4,5])
    elif neg and not pos:
        score = random.choice([1,2])
    else:
        score = random.choice([2,3,4])
    stars = "⭐"*score + "☆"*(5-score)
    return score, f"{stars} ({score}/5)"

# -------------------- PROMPT BUILDER --------------------
def build_prompt_for_mode(mode: str, lang: str, features: dict, sentiment: str) -> str:
    base_lang = LANG_PROMPTS.get(lang, LANG_PROMPTS["general"])
    if mode == "locality":
        mode_instr = "Focus on locality, neighbourhood and nearby conveniences."
    elif mode == "amenities":
        mode_instr = "Focus on amenities (gym, pool, clubhouse, parking, security)."
    elif mode == "hand_over":
        mode_instr = "Talk about possession and handover experience."
    elif mode == "under_construction":
        mode_instr = "Talk about construction status, expected completion and investment potential."
    else:
        mode_instr = "Give a general, human-like review about the property."
    sentiment_instr = "Tone: slightly critical, mention small issues." if sentiment == "negative" else "Tone: positive/neutral, not marketing."

    return f"""{base_lang}
{mode_instr}
{sentiment_instr}

Property details:
{json.dumps(features, indent=2, ensure_ascii=False)}


Write a short 2-3 sentence review in simple Indian English. Only output the review text.
"""

def generate_review_text(mode: str, lang: str, features: dict, sentiment: str) -> str:
    prompt = build_prompt_for_mode(mode, lang, features, sentiment)
    text = call_hf(prompt, max_tokens=140)
    if text and isinstance(text, str) and text.strip():
        return text.strip()
    # fallback simple English summary
    fallback = f"Good project by {features.get('builder') or 'the builder'}. Nice location and amenities. Worth considering."
    if lang != "general":
        # keep fallback short romanised hint (best-effort)
        return fallback
    return fallback

# -------------------- SINGLE REVIEW GENERATION --------------------
def generate_single_review(features: dict, used_first_names: set, used_dates: set, detected_region: str) -> dict:
    # choose language: 10% regional, 90% english
    lang = detected_region if (detected_region != "general" and random.random() < 0.10) else "general"

    # generate full name → "First Last"
    full_name = generate_unique_name(used_first_names, detected_region)

    # split into firstname + lastname
    try:
        first_name, last_name = full_name.split(" ", 1)
    except:
        first_name = full_name
        last_name = ""

    review_date = random_unique_review_date(features.get("launch_date"), used_dates)
    mode = decide_review_mode(features.get("launch_date"), features.get("possession_date"))
    sentiment = random.choices(["positive", "negative"], weights=[0.75, 0.25])[0]
    review_text = generate_review_text(mode, lang, features, sentiment)
    rating_val, rating_ui = rating_from_text(review_text)

    return {
        "first_name": first_name,
        "last_name": last_name,
        "date": review_date,
        "rating_value": rating_val,
        "review": review_text
    }


# -------------------- MULTI REVIEW GENERATOR (TEXT INPUT) --------------------
def generate_reviews_from_text(raw_text: str, count: int):
    """
    Returns:
      - json_str (stringified list)
      - reviews (list of dicts)
    This maintains backward compatibility with the original Gradio wrapper.
    """
    # parse -> features dict
    parsed = parse_text_to_features(raw_text)
    features = clean_input_json(parsed)

    # normalize dates if present
    if features.get("launch_date"):
        features["launch_date"] = normalize_date(features["launch_date"])
    if features.get("possession_date"):
        features["possession_date"] = normalize_date(features["possession_date"])

    # detect region once from features
    detected_region = detect_region_from_features(features)

    used_first = set()
    used_dates = set()
    reviews = []
    for _ in range(max(1, int(count))):
        reviews.append(generate_single_review(features, used_first, used_dates, detected_region))

    return json.dumps(reviews, indent=2, ensure_ascii=False), reviews

# Module ends here. This file is intended to be imported by main.py

