# model_pipeline_test.py
"""
Test the full model pipeline:
- Send sample input to FastAPI
- Generate SEO content + reviews
- Send result to company callback API
- Show callback status + response
- SAVE the payload that is sent to the company API into a JSON file
"""

import requests
import json
from datetime import datetime

# 🔧 CHANGE THIS IF NEEDED:
# If you're testing locally:
FASTAPI_URL = "http://127.0.0.1:8000/process-property-debug"
# If your colleague hits via ngrok, you can also test that URL here:
# FASTAPI_URL = "https://your-ngrok-id.ngrok-free.app/process-property-debug"

# ============= SAMPLE TEST PAYLOAD =============
# This MUST match your Pydantic schema: IncomingPropertyData
# 🔴 IMPORTANT: put your existing big test_payload dict here.
test_payload = {
    "status": "True",
    "result": "successful",
    "prop_info": [
        {
            "propertyID": "47",
            "propertyName": "Klassik Landmark",
            "city_name": "Bangalore",
            "locality_name": "Sarjapur Road",
            "localityID": "5",
            "LocalityDiscription": "<p style=\"text-align: justify;\"><span style=\"font-size: 12pt;\"><strong>Sarjapur Road</strong> is part of south-east Bangalore. It is one of the fastest-growing locality in Bangalore. It is the prominent connectivity for some of the vibrant locations like Koramangala , HSR Layout , Hosa Road , Harlur Road , <a title=\"Properties For Sale in Electronic City, Bangalore - Homes247.in\" href=\"https://www.homes247.in/bangalore/property-sale-in-electronic-city-10\" target=\"_blank\" rel=\"bookmark noopener\">Electronic city</a> , Sarjapur. Properties for sale in Sarjapur Road are the most favored in the present days. They range from first-line projects for the new home buyers and to sophisticated investors.</span></p>\r\n<p dir=\"ltr\"><span style=\"font-size: 12pt;\">The neighbourhoods surrounding <a href=\"https://www.homes247.in/blogs/rise-of-sarjapur-road-1273\" target=\"_blank\" rel=\"noopener\">Sarjapur Road</a> are increasingly being used for residential development. For both home seekers and builders, it's like paradise. With a variety of housing options to meet everyone's needs, including luxurious villas, affordable apartments, and even land for construction, Sarjapur Road is currently popular with residents of the city. the industry, including Infosys, Wipro, TCS, and Tech Mahindra.</p>\r\n<h2 style=\"text-align: justify;\"><span style=\"font-size: 12pt;\"><strong>Why wait when you can enjoy property shopping with a plethora of properties for sale in Sarjapur Road?</strong></span></h2>\r\n<p style=\"text-align: justify;\"><span style=\"font-size: 12pt;\">Sarjapur Road is a rapidly growing residential area in Bangalore. Several of the properties in Sarjapur Road are in high demand. The key factor that makes Sarjapur Road more demanding is its placement between two of the famous technology parks. Both residential, as well as commercial development have helped Sarjapur Road gain significance over a period of time.</span></p>\r\n<p style=\"text-align: justify;\"><span style=\"font-size: 12pt;\">The demand for flats and related properties in Sarjapur Road has surged rapidly due to its locality and major thoroughfares. It is in good connectivity with other significant areas like Electronic City, Koramangala, and Whitefield, among many more.</span></p>\r\n<p style=\"text-align: justify;\"><span style=\"font-size: 12pt;\">Bangalore&rsquo;s fast-growing economy plays a vital role in the rising demands for properties in Sarjapur Road. One of the biggest IT firms, \"><span style=\"font-size: 12pt;\"><strong>Ready to move in properties in Sarjapur Road </strong>are Inner Spaces Meadow in the Sun, Bren Imperia, Bren Champions Square, Century Infiniti, Mahaveer Ranches Phase 1, SJR Blue Waters, Klassik Landmark, SNN Raj Eternia, The Gran Carmen Address, and Ahad Excellanicia among others.</span></p>\r\n<p style=\"text-align: justify;\"><span style=\"font-size: 12pt;\">Going by the rapid growth of Sarjapur Road, investing in this area would be a smart move. There is a steady increase of flats and other properties for sale in Sarjapur Road and is expected to see a fair increase in the appreciation of the value in coming times.</span></p>",
            "Property_LocalityDiscription": "<p style=\"text-align: justify;\">Ever wondered why Sarjapur Road became the prime reality hotspot in <a title=\"Properties for Sale in Bangalore | Buy Property in Bangalore\" href=\"https://www.homes247.in/bangalore/property-sale\" rel=\"bookmark\">Bangalore</a> ?<br><br>The IT corridor in East Bangalore , within this last decade, has become the superstar in Bangalore's real estate market, with many of the top-notch developers of both the city and the country quickly developing their premium residential options spread across all the categories in the region.<br><br><a title=\"Properties for Sale in Sarjapur Road, Bangalore - Homes247.in\" href=\"https://www.homes247.in/bangalore/property-sale-in-sarjapur-road-5\" rel=\"bookmark\">Sarjapur Road</a> , now in Bangalore, stands for prime connectivity. It has excellent connectivity to the main roadway networks such as Hosa Road , Harlur Road, HSR Layout, etc., and to locales such as Whitefield, Koramangala, Electronic City, etc.</p>\n<p style=\"text-align: justify;\">Sarajapur Road prominence in Bangalore real estate is not only a matter of strategic location but also a combination of urban growth and demand What adds to the luster of Sarajapur is its natural blend of surroundings and modernity beautiful things. Moreover, lots of community thrives here, encouraging cultural events, markets, and interesting restaurants. So Sarjapur Road is not just the neighborhood; This is a social story, reflecting a heritage-oriented growth culture.<br><br>The roadway range lies in the heartland between the two titans of IT hubs, Electronic City and Whitefield, becoming the easiest or the most practical place to get a home near your workplace.<br><br>As it is close to these two locales, it is also near <a title=\"Properties in Central Bangalore | Homes247.in\" href=\"https://www.homes247.in/bangalore/zone/central-bangalore-50245\" target=\"_blank\" rel=\"noopener\"><strong>Central Bangalore</strong></a>, where most commercial and office spaces, hence again proximity factor, increase by the lot for the common man.<br><br>The vast stretch of land is also called the IT Corridor because the area is surrounded by multiple high-end IT companies and Tech Parks, all of which give the region a completely different outlook, as if a perfect blend of futuristic landscape and a cozy residential township. Now that's called a perfect neighborhood.</p>\n<p style=\"text-align: justify;\">Sarjapur Road has many benefits beyond its close vicinity; it is surrounded by a wide range of public amenities, including as retail centers, healthcare facilities, educational institutions, and entertainment venues. There are many <a title=\"Top Schools in Sarjapur Road - Best Education in Sarjapur Rd\" href=\"https://www.homes247.in/blogs/best-schools-in-sarjapur-road-bangalore-1045\" target=\"_blank\" rel=\"noopener\"><strong>schools on Sarjapur Road</strong></a> that serve different educational needs and boards. Many developers are building a range of home options next to Sarjapur Road because it's one of the most sought-after places for real estate.</p>\n<p>As a result, a variety of property types, including flats, villas, planned projects, low rises, and standalone homes, have become more and more prevalent on Sarjapur Road, which is a haven for home purchasers. In actuality, a buyer of a house in the area has a ton of possibilities. One of the main things that makes the road so great is its incredible access to all of Bangalore's cityscapes.</p>\n<p dir=\"ltr\">The locality has been witnessing a dramatic transformation in character in the recent past and is rapidly developing and expanding. This once-quiet neighborhood is now a trendy and modern hub of the city, crowded with workspaces and residential developments.</p>\n<p dir=\"ltr\">Sarjapur Road has been seeing a large movement of new residents employed in the numerous work hubs in the area. This increasing population has triggered the rapid and ongoing development of the physical infrastructure and social amenities in the neighborhood. The neighborhood boasts excellent physical infrastructure with a vast and well-developed road network and also several signal-free corridors.</p>\n<p dir=\"ltr\"><strong id=\"docs-internal-guid-969077ad-7fff-035c-3781-b405c2193b07\"></strong>Thus Sarjapur Road and the properties in Sarjapur Road become a popular choice for every denizen of Bangalore and thereby a definitive investment hubspot!</p>\n<p dir=\"ltr\">With its strategic location, excellent connectivity, world-class infrastructure, and serene environment, Sarjapur Road has emerged as a prime investment destination. The rising demand for housing and commercial spaces in the area has led to significant appreciation in property values, making it a lucrative investment option for both end-users and investors.</p>",
            "BuilderName": "Klassik Enterprises",
            "Status": "Ready to Move",
            "bhk": "3 BHK",
            "min_price": "14900000",
            "max_price": "47000000"
        }
    ],
    "basic_details": [
        {
            "property_description": "<p style=\"text-align: justify;\"><span style=\"font-size: 12pt;\"><strong>Klassik Landmark</strong>&nbsp;is an iconic project developed by <a title=\"Klassik Enterprises Bangalore|Klassik Enterprises Projects|Homes247.in\" href=\"https://www.homes247.in/bangalore/builder/klassik-enterprises-57\" rel=\"bookmark\">Klassik Enterprise</a>.&nbsp;which is located at the <a title=\"Properties for Sale in Sarjapur Road, Bangalore- Apartments for sale\" href=\"https://www.homes247.in/bangalore/property-sale-in-sarjapur-road-5\" rel=\"bookmark\">Sarjapur Road</a>, Bangalore.</span></p>\n<p style=\"text-align: justify;\"><span style=\"font-size: 12pt;\">The project is constructed and organized in a meticulous manner that offers spacious open spaces with panoramic scenery of balconies and a plethora of magnificent amenities. The project blossoms in your heart with its&nbsp;mesmerizing interiors. Klassik Landmark floor plans offer you a tincture of glory that highlights sovereignty and radiates magnificence.&nbsp;&nbsp;</span></p>\n<p style=\"text-align: justify;\"><span style=\"font-size: 12pt;\">The project consists of standalone 3 BHK apartments. The project is designed to have an opulent atmosphere that attracts buyers. The infrastructure of the project is one of the iconic features of&nbsp;<strong>Klassik Landmark</strong>. Another significant aspect of the development is the fact that it provides absolute privacy to residents, as the homes are separated from each other without common walls. So, you can live in a world of style and efficiency.</span></p>\n<p style=\"text-align: justify;\"><span style=\"font-size: 12pt;\">The facilities offered by the construction comprise an Olympic size swimming pool an infant's pool, a tennis court basketball Court and a cricket field as well as a jogging track. playground for children gymnasium, outdoor badminton courts, table tennis court, the snooker table and an amphitheatre.</span></p>\n<p style=\"text-align: justify;\"><span style=\"font-size: 12pt;\">The most notable feature in Klassik Landmark is that it is a testament to privacy.&nbsp;As stated in the description, each of the units is like an independent island, which provides a lifestyle unlike any other.&nbsp;The incredible size of spaces makes it among the top apartments in the city's top houses.</span></p>\n<h3 style=\"text-align: justify;\"><span style=\"font-size: 12pt;\">Klassik Landmark - Features and Specifications:</span></h3>\n<ol>\n<li style=\"text-align: justify; font-size: 12pt;\"><span style=\"font-size: 12pt;\">The project features an aerodynamic wing-shaped tower that enhances the ventilation of the property.</span></li>\n<li style font-size: 12pt;\"><span style=\"font-size: 12pt;\">Vaishnavi Tech Park</span></li>\n<li style=\"text-align: justify; font-size: 12pt;\"><span style=\"font-size: 12pt;\">Ozone Manay Tech Park</span></li>\n<li style=\"text-align: justify; font-size: 12pt;\"><span style=\"font-size: 12pt;\">AMR Tech Park</span></li>\n</ul>\n<h3 style=\"text-align: justify;\"><span style=\"font-size: 12pt;\">Sarjapur Road - Synopsis:</span></h3>\n<p style=\"text-align: justify;\">Bangalore has established itself as a strong presence in the real estate industry. The city is buzzing with real estate activity, and job possibilities are being offered to the largest sector of newcomers to the real estate market. The real estate market offers numerous opportunities for earning a substantial income. The developers' creative brains are coming up with innovative concepts, with the primary goal of creating high-quality projects that provide potential clients with a value-driven experience. The most difficult problem for developers is determining the ideal location for their project. Each location has unique qualities that impact purchasers' decision to purchase a house.</p>\n<h3 style=\"text-align: justify;\"><span style=\"font-size: 12pt;\">Why Sarjapur Road is called a prominent investment destination!!</span></h3>\n<p style=\"text-align: justify;\"><span style=\"font-size: 12pt;\">Sarjapur Road is a classic location for the construction of residential and commercial properties. It is one of the rapidly growing location in Bangalore and is one of the top destinations for investors. It has evolved as an emerging residential hub in Bangalore.Sarjapur Road is linked from Koramangala to Whitefield via the Outer Ring Road that connects Electronic City and HSR Layout. The planned peripheral Ring Road will connect Tumkur Road and Hosur Road that splits between Dodaballapura Road, Bellari Road along with <a title=\"Ready To Move Properties For Sale in Old Madras Road, East Bangalore\" href=\"https://www.homes247.in/bangalore/property-sale-in-old-madras-road-6\" rel=\"bookmark\">Old Madras Road</a>.</span></p>\n<p style=\"text-align: justify;\"><span style=\"font-size: 12pt;\">Sarjapur Road offers excellent connectivity to prominent areas like Silk Board, Outer Ring Road, Marathahalli, and <a title=\"Properties for Sale in Koramangala, Bangalore - Homes247.in\" href=\"https://www.homes247.in/bangalore/property-sale-in-koramangala-86\" rel=\"bookmark\">Koramangala</a>. The locality provides entrance to Electronic City from Chandapura Road, Haralur Road, and Hosur Road. Carelaram Bus Station and Daddakannelli Bus Stop are quite close to Sarjapur Road. This makes it an ideal location for residents, particularly those who work in the IT industry. In fact, several prominent residential projects, such <a title=\"GR Samskruthi Sarjapur, Bangalore | Price, Reviews &amp; Floorplans | Homes247.in\" href=\"https://www.homes247.in/property/bangalore/sarjapur/gr-samskruthi-1830\" target=\"_blank\" rel=\"noopener\"><strong>GR Samskruthi</strong></a> and <a title=\"Abhee Silicon Shine in Sarjapur Road, Bangalore - Homes247.in\" href=\"https://www.homes247.in/property/bangalore/sarjapur-road/abhee-silicon-shine-5681\" target=\"_blank\" rel=\"noopener\"><strong>Abhee Silicon Shine</strong></a>, are being created in this area to meet the growing demand for premium homes.</span></p>\n<p style=\"text-align: justify;\"><strong><span style=\"font-size: 12pt;\">The Desirability of Sarjapur Road:</span></strong></p>\n<p style=\"text-align: justify;\"><span style=\"font-size: 12pt;\">Looking for a lavish home can be challenging as it involves a lot of traveling and scouting. There are many reasons that have a diverse effect on people's lifestyle due to the increase in population. There are many circumstances like traffic jams and water problems you must look into before moving into Sarjapur Road. You will find numerous apartments for sale in Bangalore but looking for a desirable residential property is a crucial deciding factor involved in purchasing a property.&nbsp;</span></p>\n<p style=\"text-align: justify;\"><span style=\"font-size: 12pt;\">Let us look at some of the key factors that make Sarjapur Road a desirable location:</span></p>\n<p><strong><span style=\"font-size: 12pt;\">Easy Accessibility:</span></strong></p>\n<p style=\"text-align: justify;\"><span style=\"font-size: 12pt;\">Sarjapur Road is situated in the southeast part of Bangalore. The locality is developing drastically as compared to other sectors of <a title=\"Properties for Sale in Bangalore | Buy Property in Bangalore\" href=\"https://www.homes247.in/bangalore/property-sale\" rel=\"bookmark\">Bangalore</a>. Sarjapur Road has excellent road connectivity to the city's IT belts like Outer Ring Road, Marathahalli, Koramangala, Electronic city, and Whitefield. These mentioned roads make traveling much easier for the residents.&nbsp;</span></p>\n<p><span style=\"font-size: 12pt;\"><strong>Prominent Schools:</strong></span></p>\n<p style=\"text-align: justify;\">A health emergency or crisis can arise at any time, and it becomes a necessity to have all the medical facilities quite near to you so that you can acquire all the help you need. Sarjapur Road offers eminent hospitals like Columbia Asia Hospital and Narayana Multispeciality Clinic that provides 24*7 services to solve these circumstances.&nbsp; &nbsp;</span></p>\n<h3 style=\"text-align: justify;\"><span style=\"font-size: 12pt;\">About the Developer:</span></h3>\n<p><span style=\"font-size: 12pt;\">Klassik Enterprises, led by Mr. M Ramakrishna Reddy with over 15 years of expertise is a standout in the market for real estate. They look for to improve their customers' standards of life by providing them excellent apartments for at reasonable prices. They are known for their quality in design and construction their famous designs, Klassik Bench and Klassik Nest are establishing them as reliable builder throughout South India.</span></p>\n<p><span style=\"font-size: 12pt;\">With a team of dedicated professionals who are who are committed to timely project completion, Klassik Enterprises provides a variety of properties including residential and industrial.They have established a strong foundation in the real estate industry by continually raising the standard via outstanding workmanship, innovative technology, and social transparency. In the spirit of innovation and entrepreneurship, Klassik Enterprises strives to provide a better living experience and has earned favorable reviews and praise from well-known developers.</span></p>\n<p style=\"text-align: justify;\"><span style=\"font-size: 12pt;\">So ready to check out the elegant <strong>Klassik Landmark</strong>?</span></p>",
            "dimension": "11         ",
            "total_apartments": "590",
            "area_min": "1446",
            "area_max": "4561",
            "PossessionDate": "2016-03-03",
            "propertyType": "Apartments",
            "RERA_ID": "PRM/KA/RERA/1251/446/PR/171015/000760",
            "RegionName": "East Bangalore"
        }
    ],
    "amenities": [
        {
            "Name": "Auditorium"
        },
        {
            "Name": "Badminton Court"
        },
        {
            "Name": "Basket Ball Court"
        },
        {
            "Name": "Garden"
        },
        {
            "Name": "Maintenance Staff"
        },
        {
            "Name": "Power Backup"
        },
        {
            "Name": "Tennis Court"
        },
        {
            "Name": "Elevator"
        },
        {
            "Name": "Indoor Games"
        },
        {
            "Name": "Party House"
        },
        {
            "Name": "Water Supply"
        },
        {
            "Name": "Car Parking"
        },
        {
            "Name": "CCTV"
        },
        {
            "Name": "Club House"
        },
        {
            "Name": "Gym"
        },
        {
            "Name": "Jogging Track"
        },
        {
            "Name": "Rainwater Harvesting"
        },
        {
            "Name": "Sewage Treatment"
        },
        {
            "Name": "Swimming Pool"
        }
    ],
    "highlights": [
        {
            "highlight_point": "Grand Spacious Clubhouse"
        },
        {
            "highlight_point": "8.5 Acres Of Open, Vehicle Free Podium"
        },
        {
            "highlight_point": "30+ Luxury Amenities"
        },
        {
            "highlight_point": "Kaveri Water Connection"
        },
        {
            "highlight_point": "GAIL Pipeline & Curved Balconies Offer Wide Views"
        }
    ],
    "developer_info": [
        {
            "BuilderName": "Klassik Enterprises",
            "BuilderID": "57",
            "property_count": "4",
            "founded_year": "2000",
            "builder_details_desc": "<p style=\"text-align: justify;\"><strong>Klassik Enterprises</strong> Private Limited is a leading real estate company that took form in the year 2000. The group has about two decades of experience in the field oF quality, and commitment occupy the uppermost priorities.</p>\n<p style=\"text-align: justify;\">Klassik Enterprises doesn't just build homes They understand the importance of creating a healthy environment. Their projects often include green space, natural light, and health-promoting features. Commitment to quality is more than beauty. Klassik emphasizes the importance of using environmentally friendly materials and construction practices, not only making your home beautiful but also reducing its impact on the environment. Additionally, their dedication to detail is reflected in the quality of the home's finishes and fixtures. From sturdy doors and well-insulated windows to high-grade electrical insulation and plumbing, Klassik ensures every element is built to last.</p>\n<p style=\"text-align: justify;\">Choosing <a title=\"Klassik Landmark Sarjapur Road, Bangalore | Price, Reviews &amp; Floorplans | Homes247.in\" href=\"https://www.homes247.in/bangalore/builder/klassik-enterprises-57\" rel=\"Bookmark\">Klassik Enterprises</a> isn't just about buying a home, it is a lifestyle investment. His work is known for providing spacious living spaces that are perfect for people who value comfort and functionality. Aware of the importance of location, Klassik positioned its development in the sought-after neighborhoods of Bangalore, facilitating access to all the dynamism of the city.</p>\n<p style=\"text-align: justify;\">mes, are highly content with their living.</p>\n<p style=\"text-align: justify;\">A lot of them are looking to buy a second home with the Klassik. The homebuyers who choose Klassik to know that it is the best in Bangalore's thriving real estate sector.</p>\n<p style=\"text-align: justify;\">They have completed five projects and have two upcoming projects that are building involves some of the best architects in the city.</p>",
            "builder_listing_desc": "<p style=\"text-align: justify;\"><strong>Klassik Enterprises</strong> are renowned for creating dream homes that impress buyers. Klassik Enterprises has established itself as a symbol of excellence, innovation and transparency <a title=\"Real Estate in Bangalore|Flats in Bangalore|Homes247.in\" href=\"https://www.homes247.in/real-estate-in-bangalore\" rel=\"bookmark\">real estate in Bangalore</a> industry since 2003. Their unwavering commitment goes beyond aesthetics. <a title=\"Klassik Enterprises Bangalore|Klassik Enterprises Projects|Homes247.in\" href=\"https://www.homes247.in/bangalore/builder/klassik-enterprises-57\" rel=\"bookmark\">Klassik Enterprises</a> carefully uses the finest materials and construction techniques to provide designs that are not only beautiful but also durable. Their professional architects and designers are the geniuses behind these facilities that combine functionality and beauty for every living space. Every Klassik home embodies comfort, style and commitment to quality.</p>\n<p style=\"text-align: justify;\">Choosing Klassik Enterprises indicates more than simply acquiring a home. This is a lifestyle investment. The company work is noted for its endless living spaces, which are suitable for those who value both convenience and functionality. Klassik recognized the importance of location and chose to develop in one of Bangalore's most desired neighborhoods, providing convenient access to the city's bustle.<br><br>But Klassik Enterprises does not simply just build structures. They appreciate the importance of creating a healthy environment. Their projects usually include green spaces, natural lighting, and health-promoting features. This commitment to holistic living sets them apart in a very competitive sector.</project is Klassik Landmark, a beautiful <a title=\"3 BHK Flats in Sarjapur Road,Bangalore | 3 BHK Apartments for Sale in Sarjapur Road, Bangalore | Homes247.in\" href=\"https://www.homes247.in/btlc/3-bhk-flats-apartments-in-sarjapur-road-bangalore-5\" rel=\"Bookmark\">3 BHK flat on Sarjapur Road</a>. Klassik Ventures is known for finishing projects on time and within spending limits, giving you peace of confidence during the entire buying procedure. Whether you happen to be a young couple starting out or a developing family, Klassik Enterprises can supply you with a home that suits your needs and wants.</p>"
        }
    ]
}

# ============= TEST RUNNER =============

def run_full_pipeline_test():
    print("\n" + "="*80)
    print("        FULL MODEL PIPELINE TEST")
    print("="*80)
    print(f"🎯 Target FastAPI endpoint: {FASTAPI_URL}")
    print(f"🕐 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n📦 Sending test payload to /process-property-debug ...")

    try:
        response = requests.post(
            FASTAPI_URL,
            json=test_payload,
            headers={"Content-Type": "application/json"},
            timeout=300,
        )
    except Exception as e:
        print(f"\n❌ ERROR: Could not reach FastAPI server: {e}")
        print("   ➜ Is uvicorn running?")
        print("   ➜ Is the URL correct?")
        return

    print(f"\n📊 FastAPI Response:")
    print(f"   Status Code: {response.status_code}")
    try:
        data = response.json()
    except Exception:
        print(f"   Raw Response Text: {response.text[:500]}")
        return

    # Preview full JSON response (truncated)
    print(json.dumps(data, indent=2)[:3000])

    if not data.get("status"):
        print("\n❌ FastAPI returned status = False")
        return

    # ===== NEW: SAVE THE PAYLOAD SENT TO COMPANY API =====
    payload = data.get("payload")
    if payload is not None:
        filename = f"callback_payload_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            print("\n💾 Saved callback payload (data sent to company API) to:")
            print(f"   {filename}")
        except Exception as e:
            print("\n❌ Failed to save callback payload to file:")
            print(f"   {e}")
    else:
        print("\n⚠️ No 'payload' field found in FastAPI response.")
        print("   ➜ /process-property-debug might not be returning it.")

    # ===== Check callback result if present =====
    callback_result = data.get("callback_result")
    if callback_result is None:
        print("\n⚠️ No 'callback_result' field in response.")
        print("   ➜ This endpoint may not be /process-property-debug or code not updated.")
        return

    print("\n" + "-"*80)
    print("📡 CALLBACK RESULT (Company API)")
    print("-"*80)
    print(f"   ok:           {callback_result.get('ok')}")
    print(f"   status_code:  {callback_result.get('status_code')}")
    print(f"   error:        {callback_result.get('error')}")
    print(f"   response_text (first 200 chars):")
    rt = callback_result.get("response_text")
    print(f"   {repr(rt[:200]) if isinstance(rt, str) else rt}")

    # Quick interpretation
    if callback_result.get("ok") and callback_result.get("status_code") == 200:
        print("\n✅ SUCCESS: Full pipeline worked.")
        print("   - Input accepted")
        print("   - Content + reviews generated")
        print("   - Callback sent to company API")
        print("   - Company API responded (probably \"POST API HITTING\")")
    else:
        print("\n⚠️ Pipeline ran, but callback was NOT fully successful.")
        print("   ➜ Check 'error' and your FastAPI logs for more details.")

    print("\n" + "="*80)
    print("        TEST FINISHED")
    print("="*80)


if __name__ == "__main__":
    run_full_pipeline_test()
