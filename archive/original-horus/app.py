from flask import Flask, request, render_template, jsonify
import os
import io

# --- Original Imports for Image Classification and Chat ---
try:
    from class_labels import class_names
except ImportError:
    print("Warning: class_labels.py not found. Using default class_names for image classification.")
    class_names = ["Default Artifact"] # Placeholder

try:
    from llm_utils import generate_chat_response, get_greeting_message, get_available_languages, detect_language
except ImportError:
    print("Warning: llm_utils.py not found. Chat functionality will be a placeholder.")
    def generate_chat_response(user_message, artifact_name, artifact_description, language='en'):
        return "Chat response generation is currently unavailable due to missing llm_utils."
    
    def get_greeting_message(language='en'):
        return "Greetings! I am Horus AI, guardian of ancient Egyptian knowledge."
    
    def get_available_languages():
        return {
            'en': {'name': 'English', 'code': 'en'},
            'ar': {'name': 'العربية', 'code': 'ar'},
            'fr': {'name': 'Français', 'code': 'fr'},
            'de': {'name': 'Deutsch', 'code': 'de'}
        }
    
    def detect_language(text):
        return 'en'

from keras.saving import load_model
import numpy as np
from PIL import Image

# --- New Imports for Recommendation Logic (without sentence-transformers) ---
import pandas as pd
import re
from collections import Counter

# --- New Imports for Sentiment Analysis and Reddit Integration ---
import requests
import json
from textblob import TextBlob
import time
from datetime import datetime, timedelta

app = Flask(__name__)

# --- Sentiment Analysis Configuration ---
REDDIT_API_BASE = "https://www.reddit.com/r/travel/search.json"
SENTIMENT_CACHE = {}
SENTIMENT_CACHE_DURATION = 3600  # 1 hour cache

def get_reddit_sentiment(location_name, language='en'):
    """
    Get sentiment analysis from Reddit posts about Egyptian tourist locations
    """
    cache_key = f"{location_name}_{language}"
    current_time = time.time()
    
    # Check cache first
    if cache_key in SENTIMENT_CACHE:
        cache_data = SENTIMENT_CACHE[cache_key]
        if current_time - cache_data['timestamp'] < SENTIMENT_CACHE_DURATION:
            return cache_data['data']
    
    try:
        # Search Reddit for posts about the location
        search_terms = [
            f"{location_name} Egypt",
            f"{location_name} travel",
            f"{location_name} tourism",
            f"{location_name} visit"
        ]
        
        all_posts = []
        
        for term in search_terms:
            try:
                headers = {
                    'User-Agent': 'HorusAI-SentimentAnalysis/1.0'
                }
                
                params = {
                    'q': term,
                    'restrict_sr': 'on',
                    'sort': 'relevance',
                    't': 'year',
                    'limit': 10
                }
                
                response = requests.get(REDDIT_API_BASE, headers=headers, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    if 'data' in data and 'children' in data['data']:
                        posts = data['data']['children']
                        for post in posts:
                            post_data = post['data']
                            if post_data.get('selftext') and len(post_data['selftext']) > 50:
                                all_posts.append({
                                    'title': post_data.get('title', ''),
                                    'content': post_data.get('selftext', ''),
                                    'score': post_data.get('score', 0),
                                    'created': post_data.get('created_utc', 0)
                                })
                
                time.sleep(1)  # Be respectful to Reddit's API
                
            except Exception as e:
                print(f"Error fetching Reddit data for {term}: {e}")
                continue
        
        # Analyze sentiment
        sentiment_data = analyze_sentiment(all_posts, location_name, language)
        
        # Cache the results
        SENTIMENT_CACHE[cache_key] = {
            'timestamp': current_time,
            'data': sentiment_data
        }
        
        return sentiment_data
        
    except Exception as e:
        print(f"Error in sentiment analysis: {e}")
        return get_fallback_sentiment(location_name, language)

def analyze_sentiment(posts, location_name, language='en'):
    """
    Analyze sentiment from Reddit posts
    """
    if not posts:
        return get_fallback_sentiment(location_name, language)
    
    total_sentiment = 0
    positive_count = 0
    negative_count = 0
    neutral_count = 0
    analyzed_posts = []
    
    # Arabic sentiment keywords
    arabic_positive = ['ممتاز', 'رائع', 'جميل', 'مذهل', 'مفيد', 'مريح', 'آمن', 'نظيف', 'منظم', 'مضياف']
    arabic_negative = ['سيء', 'مزعج', 'مكلف', 'مزدحم', 'قذر', 'خطير', 'غير آمن', 'ممل', 'صعب', 'مخيب']
    
    for post in posts:
        text = f"{post['title']} {post['content']}"
        
        # Basic sentiment analysis
        if language == 'ar':
            # Arabic sentiment analysis
            positive_score = sum(1 for word in arabic_positive if word in text)
            negative_score = sum(1 for word in arabic_negative if word in text)
            
            if positive_score > negative_score:
                sentiment_score = 0.7 + (positive_score * 0.1)
                sentiment_label = 'إيجابي'
                positive_count += 1
            elif negative_score > positive_score:
                sentiment_score = 0.3 - (negative_score * 0.1)
                sentiment_label = 'سلبي'
                negative_count += 1
            else:
                sentiment_score = 0.5
                sentiment_label = 'محايد'
                neutral_count += 1
        else:
            # English sentiment analysis using TextBlob
            blob = TextBlob(text)
            sentiment_score = (blob.sentiment.polarity + 1) / 2  # Convert from [-1,1] to [0,1]
            
            if sentiment_score > 0.6:
                sentiment_label = 'Positive'
                positive_count += 1
            elif sentiment_score < 0.4:
                sentiment_label = 'Negative'
                negative_count += 1
            else:
                sentiment_label = 'Neutral'
                neutral_count += 1
        
        total_sentiment += sentiment_score
        
        analyzed_posts.append({
            'title': post['title'][:100] + '...' if len(post['title']) > 100 else post['title'],
            'sentiment': sentiment_label,
            'score': sentiment_score,
            'reddit_score': post['score']
        })
    
    # Calculate overall sentiment score (1-10 scale)
    if analyzed_posts:
        overall_score = (total_sentiment / len(analyzed_posts)) * 10
        overall_score = max(1, min(10, overall_score))  # Clamp between 1-10
    else:
        overall_score = 5.0
    
    # Determine overall sentiment
    if overall_score >= 7:
        overall_sentiment = 'إيجابي جداً' if language == 'ar' else 'Very Positive'
    elif overall_score >= 5:
        overall_sentiment = 'إيجابي' if language == 'ar' else 'Positive'
    elif overall_score >= 3:
        overall_sentiment = 'محايد' if language == 'ar' else 'Neutral'
    else:
        overall_sentiment = 'سلبي' if language == 'ar' else 'Negative'
    
    return {
        'location': location_name,
        'overall_score': round(overall_score, 1),
        'overall_sentiment': overall_sentiment,
        'total_posts': len(analyzed_posts),
        'positive_posts': positive_count,
        'negative_posts': negative_count,
        'neutral_posts': neutral_count,
        'sample_posts': analyzed_posts[:5],  # Show top 5 posts
        'language': language,
        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

def get_fallback_sentiment(location_name, language='en'):
    """
    Provide fallback sentiment data when Reddit is unavailable
    """
    # Pre-defined sentiment scores for major Egyptian attractions
    fallback_scores = {
        'pyramids': 8.5,
        'egyptian museum': 8.2,
        'karnak temple': 8.8,
        'valley of the kings': 8.6,
        'abu simbel': 9.1,
        'khan el-khalili': 7.8,
        'alexandria': 7.9,
        'aswan': 8.3,
        'luxor': 8.7,
        'cairo': 7.5
    }
    
    # Find best match
    best_match = None
    best_score = 0
    
    for key, score in fallback_scores.items():
        if key in location_name.lower():
            if len(key) > best_score:
                best_match = key
                best_score = len(key)
    
    if best_match:
        score = fallback_scores[best_match]
    else:
        score = 7.0  # Default score
    
    return {
        'location': location_name,
        'overall_score': score,
        'overall_sentiment': 'إيجابي' if language == 'ar' else 'Positive',
        'total_posts': 0,
        'positive_posts': 0,
        'negative_posts': 0,
        'neutral_posts': 0,
        'sample_posts': [],
        'language': language,
        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'note': 'Fallback data - Reddit analysis unavailable'
    }

# --- New Recommendation Logic Setup ---
ATTRACTIONS_DATA = [
    {
        "name": "Egyptian Museum",
        "city": "Cairo",
        "maps_url": "https://www.google.com/maps/search/?api=1&query=Egyptian+Museum+Cairo",
        "description": "Home to the world's largest collection of Pharaonic antiquities, including treasures from Tutankhamun's tomb.",
        "type": "Pharaonic",
        "popularity": 9,
        "key_artifacts": ["Tutankhamun's Death Mask", "Royal Mummies Collection", "Narmer Palette", "Statue of Khufu"],
        "highlights": "The museum houses over 120,000 artifacts, with the star attraction being King Tutankhamun's golden mask. Visitors can also explore the Royal Mummies Hall featuring perfectly preserved remains of Egypt's most powerful pharaohs.",
        "visiting_tips": "Visit early in the morning to avoid crowds. Plan at least 3 hours to see the main highlights. Photography is allowed in most areas but requires a special ticket.",
        "historical_significance": "Founded in 1902, the museum preserves Egypt's ancient heritage and provides invaluable insights into one of the world's earliest civilizations."
    },
    {
        "name": "Khan el-Khalili",
        "city": "Cairo",
        "maps_url": "https://www.google.com/maps/search/?api=1&query=Khan+el-Khalili+Cairo",
        "description": "Historic souk and bazaar dating to the 14th century, famous for traditional crafts, spices, and Egyptian souvenirs.",
        "type": "Islamic",
        "popularity": 8,
        "notable_features": ["El-Fishawi Café", "Gold District", "Spice Market", "El-Hussein Mosque"],
        "highlights": "This bustling medieval-style marketplace offers a sensory journey through narrow alleyways filled with shops selling everything from hand-crafted jewelry and copper goods to textiles, spices, and perfumes.",
        "visiting_tips": "Best experienced in late afternoon and evening. Bargaining is expected. Visit El-Fishawi café, Cairo's oldest café, for traditional Egyptian tea.",
        "historical_significance": "Established in 1382 as a caravanserai for traveling merchants, it remains the commercial heart of historic Cairo."
    },
    {
        "name": "Al-Azhar Park",
        "city": "Cairo",
        "maps_url": "https://www.google.com/maps/search/?api=1&query=Al-Azhar+Park+Cairo",
        "description": "A beautiful Islamic garden offering panoramic views of historic Cairo, featuring Islamic architectural elements.",
        "type": "Islamic",
        "popularity": 7,
        "notable_features": ["Lakeside Café", "Citadel View Restaurant", "Islamic-Style Gardens", "Historic Views"],
        "highlights": "This 30-hectare urban oasis provides a peaceful escape from Cairo's bustle with formal gardens, fountains, and stunning views of the Citadel and historic Cairo skyline.",
        "visiting_tips": "Visit in late afternoon to enjoy sunset views over the city. The park has excellent restaurants offering both Egyptian and international cuisine.",
        "historical_significance": "Built on what was once a 500-year-old garbage dump, this transformation project was funded by the Aga Khan Trust for Culture and has revitalized the surrounding historic district."
    },
    {
        "name": "Ibn Tulun Mosque",
        "city": "Cairo",
        "maps_url": "https://www.google.com/maps/search/?api=1&query=Ibn+Tulun+Mosque+Cairo",
        "description": "One of the oldest and largest mosques in Egypt with a unique spiral minaret and vast courtyard.",
        "type": "Islamic",
        "popularity": 7,
        "architectural_features": ["Spiral Minaret", "Vast Courtyard", "Stucco Decorations", "Gypsum Windows"],
        "highlights": "This 9th-century architectural masterpiece features a unique spiral minaret and an expansive open courtyard surrounded by elegant arcades with distinctive pointed arches.",
        "visiting_tips": "Visit in the morning light for the best photography. Dress modestly and remove shoes before entering the prayer hall. Climb the minaret for panoramic views of Cairo.",
        "historical_significance": "Built in 879 AD, it's the oldest mosque in Egypt that preserves its original form and one of the largest mosques in the world by land area."
    },
    {
        "name": "Karnak Temple",
        "city": "Luxor",
        "maps_url": "https://www.google.com/maps/search/?api=1&query=Karnak+Temple+Luxor",
        "description": "A vast temple complex dedicated to the Theban triad of Amun, Mut, and Khonsu, featuring massive columns and obelisks.",
        "type": "Pharaonic",
        "popularity": 9,
        "period": "New Kingdom to Ptolemaic",
        "notable_features": ["Great Hypostyle Hall", "Sacred Lake", "Avenue of Sphinxes", "Obelisks of Hatshepsut"],
        "highlights": "The temple's Great Hypostyle Hall contains 134 massive columns arranged in 16 rows, creating a forest of stone pillars that once supported a now-vanished roof. Many columns are over 10 meters tall and covered with intricate hieroglyphic carvings.",
        "visiting_tips": "Visit early morning or late afternoon to avoid the midday heat. Hire a knowledgeable guide to understand the complex's rich history. The Sound and Light show in the evening offers a different perspective.",
        "historical_significance": "Built over 2,000 years by successive pharaohs, it's the largest religious building ever constructed and was ancient Egypt's most important place of worship."
    },
    {
        "name": "Valley of the Kings",
        "city": "Luxor",
        "maps_url": "https://www.google.com/maps/search/?api=1&query=Valley+of+the+Kings+Luxor",
        "description": "Royal burial ground containing tombs of pharaohs from the New Kingdom, including Tutankhamun.",
        "type": "Pharaonic",
        "popularity": 9,
        "period": "New Kingdom",
        "notable_tombs": ["KV62 (Tutankhamun)", "KV17 (Seti I)", "KV7 (Ramses II)", "KV5 (Sons of Ramses II)"],
        "highlights": "This desert valley contains 63 magnificent royal tombs carved deep into the rock, with walls covered in vivid paintings depicting Egyptian mythology and the pharaoh's journey to the afterlife.",
        "visiting_tips": "Standard tickets include access to three tombs of your choice. Special tickets are required for premium tombs like Tutankhamun's. No photography is allowed inside the tombs. Visit early in the morning when temperatures are cooler.",
        "historical_significance": "For nearly 500 years (16th to 11th century BC), this secluded valley served as the burial place for most of Egypt's New Kingdom rulers, marking a shift from the earlier pyramid tombs."
    },
    {
        "name": "Luxor Temple",
        "city": "Luxor",
        "maps_url": "https://www.google.com/maps/search/?api=1&query=Luxor+Temple+Luxor",
        "description": "Ancient Egyptian temple complex located on the east bank of the Nile River, known for its colossal statues and beautiful colonnades.",
        "type": "Pharaonic",
        "popularity": 8,
        "period": "New Kingdom",
        "notable_pharaohs": ["Amenhotep III", "Ramses II"],
        "highlights": "Unlike other temples dedicated to gods, Luxor Temple was dedicated to the rejuvenation of kingship. It features a 25-meter tall pink granite obelisk (whose twin now stands in Paris), massive seated statues of Ramses II, and beautiful colonnaded courtyards.",
        "visiting_tips": "Visit at night when the temple is dramatically illuminated. The temple is centrally located in Luxor city and easily accessible on foot from many hotels.",
        "historical_significance": "Connected to Karnak Temple by the Avenue of Sphinxes, this temple was where many pharaohs were crowned, including potentially Alexander the Great."
    },
    {
        "name": "Temple of Hatshepsut",
        "city": "Luxor",
        "maps_url": "https://www.google.com/maps/search/?api=1&query=Temple+of+Hatshepsut+Luxor",
        "description": "Mortuary temple of the female pharaoh Hatshepsut, featuring terraced colonnades set against dramatic cliffs.",
        "type": "Pharaonic",
        "popularity": 8,
        "period": "New Kingdom",
        "dynasty": "18th Dynasty",
        "highlights": "This unique temple features three dramatic ascending terraces with colonnaded facades, set dramatically against the sheer cliffs of Deir el-Bahari. Relief sculptures depict the divine birth of Hatshepsut and her famous trading expedition to the land of Punt.",
        "visiting_tips": "Visit early morning for the best lighting and views. The site has limited shade, so bring sunscreen and water. A short electric train connects the parking area to the temple entrance.",
        "historical_significance": "Built for one of Egypt's few female pharaohs who ruled for 20 years as king. After her death, her successor Thutmose III attempted to erase her legacy by destroying her images."
    },
    {
        "name": "Abu Simbel",
        "city": "Aswan",
        "maps_url": "https://www.google.com/maps/search/?api=1&query=Abu+Simbel+Aswan",
        "description": "Massive rock temples built by Ramses II, featuring colossal statues and intricate carvings.",
        "type": "Pharaonic",
        "popularity": 9,
        "period": "New Kingdom",
        "dynasty": "19th Dynasty",
        "highlights": "Two massive rock temples with four 20-meter high seated statues of Ramses II guarding the entrance. Twice a year (February 22 and October 22), the sun penetrates the main temple to illuminate the innermost sanctuary statues.",
        "visiting_tips": "Most visitors arrive on day trips from Aswan by plane or convoy. Visit early morning to avoid crowds and heat. The Sound and Light show in the evening is spectacular.",
        "historical_significance": "In the 1960s, both temples were completely dismantled and relocated 65 meters higher to save them from submersion when the Aswan High Dam created Lake Nasser - one of the greatest archaeological rescue operations in history."
    },
    {
        "name": "Philae Temple",
        "city": "Aswan",
        "maps_url": "https://www.google.com/maps/search/?api=1&query=Philae+Temple+Aswan",
        "description": "Island temple complex dedicated to the goddess Isis, rescued from the rising waters of Lake Nasser after the Aswan Dam.",
        "type": "Pharaonic",
        "popularity": 8,
        "period": "Ptolemaic to Roman",
        "highlights": "Set on a picturesque island, this beautiful temple complex combines Egyptian and Greco-Roman architectural elements. The main temple is dedicated to Isis, sister-wife of Osiris and mother of Horus.",
        "visiting_tips": "Accessible only by boat, which adds to the experience. The Sound and Light show is among Egypt's best. Morning visits offer better lighting for photography.",
        "historical_significance": "This was the last active temple of the ancient Egyptian religion, with hieroglyphics still being added in the 5th century AD. The temple was completely dismantled and relocated when the Aswan Dam was built."
    },
    {
        "name": "The Unfinished Obelisk",
        "city": "Aswan",
        "maps_url": "https://www.google.com/maps/search/?api=1&query=The+Unfinished+Obelisk+Aswan",
        "description": "Enormous obelisk abandoned in the quarry when cracks appeared, providing insights into ancient stoneworking techniques.",
        "type": "Pharaonic",
        "popularity": 7,
        "period": "New Kingdom",
        "highlights": "This massive unfinished obelisk would have been the largest ever erected at 42 meters tall and weighing 1,200 tons. Its partial carving offers unique insights into ancient Egyptian stone quarrying and carving techniques.",
        "visiting_tips": "Visit in the morning when temperatures are cooler. A knowledgeable guide can explain the ancient quarrying techniques visible at the site.",
        "historical_significance": "Likely commissioned by Queen Hatshepsut, it was abandoned when cracks appeared during carving. It demonstrates the incredible stone-working skills of ancient Egyptians without modern technology."
    },
    {
        "name": "Elephantine Island",
        "city": "Aswan",
        "maps_url": "https://www.google.com/maps/search/?api=1&query=Elephantine+Island+Aswan",
        "description": "Island with ruins of the Temple of Khnum and a nilometer used to measure the Nile flood levels.",
        "type": "Pharaonic",
        "popularity": 6,
        "period": "Multiple periods",
        "highlights": "This peaceful island in the middle of the Nile features ancient temple ruins, a museum with artifacts spanning 5,000 years, and one of the oldest nilometers used to measure the critical Nile floods.",
        "visiting_tips": "Easily reached by local ferry or felucca. The Aswan Museum displays artifacts from the island. The Nubian villages on the southern end offer cultural experiences and colorful architecture.",
        "historical_significance": "Served as Egypt's southern frontier for much of its history, with strategic and economic importance as the gateway to Nubia and Africa. Archaeological evidence shows continuous settlement since the Predynastic period."
    },
    {
        "name": "Bibliotheca Alexandrina",
        "city": "Alexandria",
        "maps_url": "https://www.google.com/maps/search/?api=1&query=Bibliotheca+Alexandrina+Alexandria",
        "description": "Modern library and cultural center built to recapture the spirit of the ancient Library of Alexandria.",
        "type": "Modern",
        "popularity": 8,
        "highlights": "This striking modern architectural marvel houses multiple libraries, four museums, a planetarium, and numerous art galleries and exhibition spaces. The main reading room can accommodate 2,000 readers under its sloping glass roof.",
        "visiting_tips": "Join a guided tour to fully appreciate the architecture and facilities. The Antiquities Museum and Manuscript Museum inside are worth visiting. Check the website for cultural events and exhibitions.",
        "historical_significance": "Built as a memorial to the ancient Library of Alexandria, once the largest in the world and center of learning in the ancient world until its destruction in antiquity."
    },
    {
        "name": "Citadel of Qaitbay",
        "city": "Alexandria",
        "maps_url": "https://www.google.com/maps/search/?api=1&query=Citadel+of+Qaitbay+Alexandria",
        "description": "15th-century defensive fortress built on the site of the ancient Lighthouse of Alexandria.",
        "type": "Islamic",
        "popularity": 8,
        "highlights": "This picturesque medieval fortress features thick walls, winding passages, and panoramic views of the Mediterranean. Built with stones from the collapsed Lighthouse of Alexandria, one of the Seven Wonders of the Ancient World.",
        "visiting_tips": "Visit late afternoon for beautiful sunset views over the Mediterranean. Wear comfortable shoes as there are many stairs to climb. The Naval Museum inside has modest displays but interesting artifacts.",
        "historical_significance": "Built in 1477 by Sultan Qaitbay on the exact site of the famous Lighthouse of Alexandria (Pharos), which had collapsed after an earthquake. It served as an important defensive stronghold against Ottoman attacks."
    },
    {
        "name": "Catacombs of Kom El Shoqafa",
        "city": "Alexandria",
        "maps_url": "https://www.google.com/maps/search/?api=1&query=Catacombs+of+Kom+El+Shoqafa+Alexandria",
        "description": "Vast Roman-era underground necropolis combining Egyptian, Greek, and Roman artistic elements.",
        "type": "Greco-Roman",
        "popularity": 7,
        "highlights": "These three-level underground tomb complexes feature a unique blend of Pharaonic, Greek and Roman artistic elements. The main tomb chamber has sculptures showing Egyptian gods in Roman dress, demonstrating the cultural fusion of the time.",
        "visiting_tips": "Bring a sweater as it can be cool underground. The site requires some stair climbing. Photography is permitted but without flash.",
        "historical_significance": "Dating from the 2nd century AD, these are considered one of the Seven Wonders of the Middle Ages. They demonstrate the multicultural nature of Roman Alexandria with their fusion of artistic styles."
    },
    {
        "name": "Montazah Palace Gardens",
        "city": "Alexandria",
        "maps_url": "https://www.google.com/maps/search/?api=1&query=Montazah+Palace+Gardens+Alexandria",
        "description": "Extensive royal gardens surrounding the Montazah Palace with beaches, woods, and formal gardens.",
        "type": "Modern",
        "popularity": 7,
        "highlights": "This 150-acre royal park features beautiful landscaped gardens, palm-lined avenues, and the distinctive Montazah Palace with its blend of Turkish and Florentine architectural styles. The park includes private beaches and woods.",
        "visiting_tips": "A perfect escape from Alexandria's urban bustle. While the palace itself is not open to the public, the gardens and beaches are accessible with an entrance ticket. Bring a picnic and swimwear in summer.",
        "historical_significance": "Built by Khedive Abbas II, the last Muhammad Ali Dynasty ruler, in 1892 as a summer residence for the Egyptian royal family. After the 1952 revolution, it became a presidential palace."
    },
    {
        "name": "Great Pyramids of Giza",
        "city": "Giza",
        "maps_url": "https://www.google.com/maps/search/?api=1&query=Great+Pyramids+of+Giza+Giza",
        "description": "The last remaining wonder of the ancient world, massive structures built as tombs for the pharaohs.",
        "type": "Pharaonic",
        "popularity": 10,
        "period": "Old Kingdom",
        "dynasty": "4th Dynasty",
        "notable_pharaohs": ["Khufu", "Khafre", "Menkaure"],
        "highlights": "The Great Pyramid of Khufu stands 147 meters tall and contains over 2.3 million stone blocks weighing 2.5-15 tons each. The precision of construction is remarkable - the base is level to within 2.1 cm, and the sides are aligned to the cardinal directions with an accuracy of up to 0.05 degrees.",
        "visiting_tips": "Arrive early morning or late afternoon to avoid crowds and midday heat. Entrance tickets to the pyramid interiors are limited and sold separately. Camel and horse rides are negotiable but agree on price beforehand.",
        "historical_significance": "Built around 2560 BC, the Great Pyramid remained the tallest human-made structure in the world for nearly 4,000 years. The complex demonstrates the Egyptians' advanced knowledge of mathematics, astronomy, and engineering."
    },
    {
        "name": "Great Sphinx of Giza",
        "city": "Giza",
        "maps_url": "https://www.google.com/maps/search/?api=1&query=Great+Sphinx+of+Giza+Giza",
        "description": "Massive limestone statue with the body of a lion and the head of a human, thought to represent King Khafre.",
        "type": "Pharaonic",
        "popularity": 9,
        "period": "Old Kingdom",
        "dynasty": "4th Dynasty",
        "highlights": "This enigmatic monument stands 20 meters tall and 73 meters long, making it the largest monolithic statue in the world. Carved from a single ridge of limestone, it has captured human imagination for thousands of years.",
        "visiting_tips": "Visit early morning or close to sunset for dramatic lighting and photographs. The Sphinx is viewed from a viewing platform at its base - you cannot touch or climb it.",
        "historical_significance": "Shrouded in mystery regarding its exact purpose and construction date. Between its paws stands the Dream Stela, placed by Thutmose IV, telling how the Sphinx appeared in his dream promising kingship if he cleared the sand covering it."
    },
    {
        "name": "Pyramids of Giza Sound and Light Show",
        "city": "Giza",
        "maps_url": "https://www.google.com/maps/search/?api=1&query=Pyramids+of+Giza+Sound+and+Light+Show+Giza",
        "description": "Nighttime spectacle that brings ancient history to life through dramatic narration, music, and illumination of the pyramids and Sphinx.",
        "type": "Pharaonic",
        "popularity": 8,
        "highlights": "This evening show uses dramatic lighting effects, music, and narration to tell the story of ancient Egypt. The pyramids and Sphinx are illuminated in changing colors while the voice of the Sphinx recounts 5,000 years of Egyptian history.",
        "visiting_tips": "Shows are presented in different languages on different nights - check the schedule. Booking in advance is recommended in high season. Bring a jacket as desert evenings can be cool.",
        "historical_significance": "Though a modern attraction, the show helps visitors connect with the ancient history and mythology surrounding these monuments, using advanced technology to tell ancient stories."
    },
    {
        "name": "Tomb of Meresankh III",
        "city": "Giza",
        "maps_url": "https://www.google.com/maps/search/?api=1&query=Tomb+of+Meresankh+III+Giza",
        "description": "Exceptionally well-preserved tomb of a queen from the 4th Dynasty with vivid colors and statues.",
        "type": "Pharaonic",
        "popularity": 7,
        "period": "Old Kingdom",
        "dynasty": "4th Dynasty",
        "highlights": "This hidden gem features remarkably preserved colorful reliefs and ten life-sized statues of women carved from the living rock. The burial chamber walls retain their vibrant original colors after more than 4,500 years.",
        "visiting_tips": "Located in the Eastern Cemetery near the Great Pyramid. Less visited than other attractions, offering a more intimate experience. A special ticket may be required as it's often opened on rotation with other tombs.",
        "historical_significance": "Meresankh III was the granddaughter of King Khufu and wife of King Khafre. Her tomb provides rare insights into the lives of royal women in the Old Kingdom and features some of the best-preserved Old Kingdom paintings."
    }
]

attractions_df = pd.DataFrame(ATTRACTIONS_DATA)

# Remove sentence-transformers related variables
RECOMMENDATION_SYSTEM_READY = True
print("Simple keyword-based recommendation system loaded successfully!")

# --- Original Image Classification Model Setup ---
MODEL_PATH = os.path.join(os.path.dirname(__file__), "last_model_bgd.keras")
image_classification_model = None
if os.path.exists(MODEL_PATH):
    try:
        image_classification_model = load_model(MODEL_PATH)
        print(f"Image classification model loaded successfully from {MODEL_PATH}")
    except Exception as e:
        print(f"Error loading Keras model from {MODEL_PATH}: {e}")
        image_classification_model = None
else:
    print(f"Warning: Image classification model file not found at {MODEL_PATH}. Classification will be mocked.")

# --- Original Image Classification Functions (Unchanged) ---
def preprocess_image(image_bytes):
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img = img.resize((224, 224))
    img_array = np.array(img).astype(np.float32) / 255.0
    img_array = np.expand_dims(img_array, axis=0)
    return img_array

def classify_image(image_bytes):
    if image_classification_model is None:
        print("Image classification model not loaded, using mock classification.")
        cn = class_names[0] if class_names and len(class_names) > 0 else "Mocked Artifact"
        return cn, f"This is a mocked English description for {cn} as the model is not available."
    
    if not image_bytes:
        return "Error: No image data", ""

    try:
        preprocessed_image = preprocess_image(image_bytes)
        predictions = image_classification_model.predict(preprocessed_image)
        class_idx = int(np.argmax(predictions[0]))
        
        if 0 <= class_idx < len(class_names):
            predicted_class_name = class_names[class_idx]
        else:
            predicted_class_name = "Unknown Artifact"
            print(f"Warning: Predicted class index {class_idx} is out of bounds for class_names.")

        description = f"This is a magnificent {predicted_class_name}, a true masterpiece of ancient Egyptian art, reflecting the rich history and culture of the civilization."
        return predicted_class_name, description
    except Exception as e:
        print(f"Error during image classification: {e}")
        return "Error during classification", str(e)

# --- New Simple Keyword-Based Recommendation Function ---
def calculate_keyword_similarity(interests, attraction_keywords):
    """Calculate similarity score based on keyword matching"""
    if not interests or not attraction_keywords:
        return 0.0
    
    # Normalize interests to lowercase
    interests_lower = [interest.lower().strip() for interest in interests]
    attraction_keywords_lower = [keyword.lower().strip() for keyword in attraction_keywords]
    
    # Count matches
    matches = 0
    for interest in interests_lower:
        for keyword in attraction_keywords_lower:
            if interest in keyword or keyword in interest:
                matches += 1
    
    # Calculate similarity score (0-1)
    max_possible_matches = max(len(interests_lower), len(attraction_keywords_lower))
    return matches / max_possible_matches if max_possible_matches > 0 else 0.0

def generate_text_recommendations(current_location, interests, liked_places=None, duration=None, top_n=3):
    """Generate recommendations using simple keyword matching and duration-based planning"""
    
    if attractions_df.empty:
        return "No attractions data available for recommendations."
    
    # Parse interests
    if isinstance(interests, str):
        interests = [interest.strip() for interest in interests.split(',') if interest.strip()]
    if not interests:
        interests = ["egyptian history", "culture"]
    
    # Determine number of recommendations based on duration
    if duration:
        try:
            days = int(duration)
            # Adjust recommendations based on days (2-3 attractions per day)
            top_n = min(max(days * 2, 3), len(attractions_df))  # At least 3, at most all attractions
        except (ValueError, TypeError):
            days = 1
            top_n = 3
    else:
        days = 1
        top_n = 3
    
    recommendations = attractions_df.copy()
    
    # Location filtering
    if current_location and current_location.lower() not in ['all', 'any']:
        recommendations['location_score'] = (recommendations['city'].str.lower() == current_location.lower()).astype(float)
    else:
        recommendations['location_score'] = 1.0
    
    # Interest matching using keywords
    recommendations['interest_score'] = 0.0
    for idx, row in recommendations.iterrows():
        keywords = row.get('keywords', [])
        if not keywords:
            # Fallback: extract keywords from description if no keywords field
            description_words = re.findall(r'\b\w+\b', row['description'].lower())
            keywords = list(set([word for word in description_words if len(word) > 3]))
        
        similarity_score = calculate_keyword_similarity(interests, keywords)
        recommendations.at[idx, 'interest_score'] = similarity_score
    
    # History-based scoring (liked places)
    recommendations['history_score'] = 0.0
    if liked_places and len(liked_places) > 0:
        liked_places_lower = [place.lower().strip() for place in liked_places]
        for idx, row in recommendations.iterrows():
            for liked_place in liked_places_lower:
                if liked_place in row['name'].lower() or row['name'].lower() in liked_place:
                    # Find similar attractions (same type or city)
                    if row['type'].lower() in [r['type'].lower() for _, r in recommendations.iterrows()]:
                        recommendations.at[idx, 'history_score'] += 0.3
                    if row['city'].lower() in [r['city'].lower() for _, r in recommendations.iterrows()]:
                        recommendations.at[idx, 'history_score'] += 0.2
    
    # Calculate final score
    recommendations['final_score'] = (
        0.2 * recommendations['location_score'] +
        0.5 * recommendations['interest_score'] +
        0.2 * recommendations['history_score'] +
        0.1 * (recommendations['popularity'] / 10)
    )
    
    # Get top recommendations
    top_recommendations_df = recommendations.sort_values('final_score', ascending=False).head(top_n)
    
    if top_recommendations_df.empty:
        return "No specific recommendations found based on your preferences. Try broadening your search!"

    # Format results with duration-based itinerary using markdown
    if duration and days > 1:
        results_text = f"# Recommended {days}-Day Egyptian Itinerary\n\n"
        attractions_per_day = max(1, top_n // days)
        
        for day in range(1, days + 1):
            results_text += f"## Day {day}\n\n"
            start_idx = (day - 1) * attractions_per_day
            end_idx = min(day * attractions_per_day, len(top_recommendations_df))
            
            day_attractions = top_recommendations_df.iloc[start_idx:end_idx]
            
            if day_attractions.empty:
                results_text += "*Rest day or explore local areas*\n\n"
                continue
                
            for i, (idx, row) in enumerate(day_attractions.iterrows(), 1):
                results_text += f"### {i}. {row['name']} ({row['city']}) - {row['type']} 🏺\n\n"
                match_score = round(row["final_score"] * 100, 1) if "final_score" in row else "N/A"
                results_text += f"**Match Score:** {match_score}%\n\n"
                results_text += f"**Description:** {row['description'][:150]}...\n\n"
                
                # Add highlights if available
                if 'highlights' in row and row['highlights']:
                    results_text += f"**Highlights:** {row['highlights'][:200]}...\n\n"
                
                # Add visiting tips if available
                if 'visiting_tips' in row and row['visiting_tips']:
                    results_text += f"**Visiting Tips:** {row['visiting_tips'][:150]}...\n\n"
                if 'maps_url' in row and row['maps_url']:
                    results_text += f"[📍 View on Google Maps]({row['maps_url']})\n\n"
                results_text += "---\n\n"
    else:
        results_text = "# Top Recommended Egyptian Attractions\n\n"
        for i, (idx, row) in enumerate(top_recommendations_df.iterrows(), 1):
            results_text += f"## {i}. {row['name']} ({row['city']}) - {row['type']} 🏺\n\n"
            match_score = round(row["final_score"] * 100, 1) if "final_score" in row else "N/A"
            results_text += f"**Match Score:** {match_score}%\n\n"
            results_text += f"**Description:** {row['description']}\n\n"
            
            # Add highlights if available
            if 'highlights' in row and row['highlights']:
                results_text += f"**Highlights:** {row['highlights']}\n\n"
            
            # Add visiting tips if available
            if 'visiting_tips' in row and row['visiting_tips']:
                results_text += f"**Visiting Tips:** {row['visiting_tips']}\n\n"
            if 'maps_url' in row and row['maps_url']:
                results_text += f"[📍 View on Google Maps]({row['maps_url']})\n\n"
            results_text += "---\n\n"
    
    # Add summary section
    results_text += "---\n\n"
    results_text += "## Summary\n\n"
    results_text += f"Based on your preferences for **{interests}** and duration of **{days} day(s)**, "
    results_text += f"we've selected the best attractions that match your interests. "
    results_text += "Each location has been carefully chosen to provide an authentic Egyptian experience.\n\n"
    
    results_text += "**Happy exploring!** 🏛️✨"
    
    return results_text.strip()

# --- Original Routes (Unchanged) ---
@app.route("/")
def index():
    return render_template("horos1.html")

@app.route("/about_us")
def about_us():
    return render_template("about_us.html")

@app.route("/page2_image_result")
def result_page():
    return render_template("page2_image_result.html")

@app.route("/page3_recommendation_result")
def recommendation_display_page():
    return render_template("page3_recommendation_result.html")

@app.route("/pharaoh_quiz")
def pharaoh_quiz():
    return render_template("pharaoh_quiz.html")

@app.route("/upload_image", methods=["POST"])
def upload_image_route():
    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400
    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "No image selected for uploading"}), 400
    try:
        image_bytes = file.read()
        class_name, description = classify_image(image_bytes)
        if "Error" in class_name:
             return jsonify({"error": description or class_name}), 500
        return jsonify({"class_name": class_name, "description": description})
    except Exception as e:
        print(f"Error in /upload_image route: {e}")
        return jsonify({"error": "An unexpected error occurred during image processing."}), 500

# --- Modified /get_recommendations Route ---
@app.route("/get_recommendations", methods=["POST"])
def get_recommendations_route():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided for recommendations"}), 400
        
    location = data.get("location")
    interests = data.get("interests")
    liked_places_input = data.get("liked_places")
    duration = data.get("duration")  # Get duration parameter

    liked_places_list = []
    if isinstance(liked_places_input, str) and liked_places_input.strip():
        liked_places_list = [p.strip() for p in liked_places_input.split(',') if p.strip()]
    elif isinstance(liked_places_input, list):
        liked_places_list = [str(p).strip() for p in liked_places_input if str(p).strip()]

    current_location_param = location if location else "All"
    interests_param = interests if interests else "history, culture"

    try:
        recommendations_text_output = generate_text_recommendations(
            current_location_param, 
            interests_param, 
            liked_places_list,
            duration=duration,  # Pass duration to the function
            top_n=3
        )
        return jsonify({"recommendations": recommendations_text_output})
    except Exception as e:
        print(f"Error in /get_recommendations route: {e}")
        fallback_message = "We encountered an issue generating recommendations. Please try again later."
        return jsonify({"error": str(e), "recommendations": fallback_message}), 500

# --- Enhanced Chat Route with Multi-language Support ---
@app.route("/chat_with_horus", methods=["POST"])
def chat_with_horus_route():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided for chat"}),400
        
    user_message = data.get("user_message")
    artifact_name = data.get("artifact_name")
    artifact_description = data.get("artifact_description")
    language = data.get("language", "en")  # Default to English

    if not user_message or not artifact_name or not artifact_description:
        return jsonify({"error": "Missing required fields for chat (user_message, artifact_name, artifact_description)"}), 400

    try:
        if 'generate_chat_response' in globals() and callable(generate_chat_response):
            bot_response = generate_chat_response(user_message, artifact_name, artifact_description, language)
        else:
            bot_response = "Chat functionality is currently unavailable."
        return jsonify({"bot_response": bot_response})
    except Exception as e:
        print(f"Error in /chat_with_horus route: {e}")
        return jsonify({"error": "An unexpected error occurred while generating chat response."}), 500

# --- New Route for Getting Available Languages ---
@app.route("/get_languages", methods=["GET"])
def get_languages_route():
    try:
        if 'get_available_languages' in globals() and callable(get_available_languages):
            languages = get_available_languages()
        else:
            languages = {
                'en': {'name': 'English', 'code': 'en'},
                'ar': {'name': 'العربية', 'code': 'ar'},
                'fr': {'name': 'Français', 'code': 'fr'},
                'de': {'name': 'Deutsch', 'code': 'de'}
            }
        return jsonify({"languages": languages})
    except Exception as e:
        print(f"Error in /get_languages route: {e}")
        return jsonify({"error": "Failed to get languages"}), 500

# --- New Route for Getting Greeting Message ---
@app.route("/get_greeting", methods=["POST"])
def get_greeting_route():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON data provided"}), 400
        
    language = data.get("language", "en")
    
    try:
        if 'get_greeting_message' in globals() and callable(get_greeting_message):
            greeting = get_greeting_message(language)
        else:
            greeting = "Greetings! I am Horus AI, guardian of ancient Egyptian knowledge."
        return jsonify({"greeting": greeting})
    except Exception as e:
        print(f"Error in /get_greeting route: {e}")
        return jsonify({"error": "Failed to get greeting"}), 500

# --- Test route to verify the endpoint is working ---
@app.route("/test_greeting", methods=["GET"])
def test_greeting_route():
    return jsonify({"message": "Greeting route is working!", "status": "success"})

# --- Sentiment Analysis Route ---
@app.route("/get_sentiment", methods=["POST"])
def get_sentiment_route():
    """Get sentiment analysis for a tourist location"""
    try:
        data = request.get_json()
        location_name = data.get('location_name', '')
        language = data.get('language', 'en')
        
        if not location_name:
            return jsonify({
                'success': False,
                'error': 'Location name is required'
            }), 400
        
        # Get sentiment analysis
        sentiment_data = get_reddit_sentiment(location_name, language)
        
        return jsonify({
            'success': True,
            'sentiment_data': sentiment_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Error getting sentiment analysis.'
        }), 500

@app.route("/learn_hieroglyphs")
def learn_hieroglyphs():
    return render_template("learn_hieroglyphs.html")

# --- Updated __main__ Block ---
if __name__ == "__main__":
    if image_classification_model is None:
        print("IMPORTANT: The Keras model file 'last_model_bgd.keras' was not found or failed to load.")
        print("The application will run with MOCKED image classification results.")
    else:
        print("Image classification Keras model loaded successfully.")
        
    print("Simple keyword-based recommendation system is ready.")
    print("Make sure to add 'keywords' field to each attraction in ATTRACTIONS_DATA for better recommendations.")
    
    # Debug: Print available routes
    print("\n=== Available Routes ===")
    for rule in app.url_map.iter_rules():
        print(f"{rule.endpoint}: {rule.rule}")
    print("========================\n")
        
    app.run(debug=True, port=5000)