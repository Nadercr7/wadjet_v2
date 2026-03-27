import google.generativeai as genai
import os
import re

# Configure the Gemini API key
GEMINI_API_KEY = "AIzaSyAKFSwrM7uXWTTW1qraZl74wuDcXj_lWZQ"
genai.configure(api_key=GEMINI_API_KEY)

# Language configurations
LANGUAGES = {
    'en': {
        'name': 'English',
        'code': 'en',
        'prompt_prefix': 'You are Horus AI, an expert on ancient Egyptian artifacts. Please respond in English.',
        'greeting': 'Greetings! I am Horus AI, guardian of ancient Egyptian knowledge. I\'ve analyzed your artifact and I\'m here to answer any questions you may have about it. What would you like to know?'
    },
    'ar': {
        'name': 'العربية',
        'code': 'ar',
        'prompt_prefix': 'أنت حورس الذكي، خبير في القطع الأثرية المصرية القديمة. يرجى الرد باللغة العربية.',
        'greeting': 'تحياتي! أنا حورس الذكي، حارس المعرفة المصرية القديمة. لقد حللت قطعتك الأثرية وأنا هنا للإجابة على أي أسئلة لديك عنها. ماذا تريد أن تعرف؟'
    },
    'fr': {
        'name': 'Français',
        'code': 'fr',
        'prompt_prefix': 'Vous êtes Horus AI, expert en artefacts égyptiens anciens. Veuillez répondre en français.',
        'greeting': 'Salutations ! Je suis Horus AI, gardien de la connaissance égyptienne ancienne. J\'ai analysé votre artefact et je suis ici pour répondre à toutes vos questions à ce sujet. Que souhaitez-vous savoir ?'
    },
    'de': {
        'name': 'Deutsch',
        'code': 'de',
        'prompt_prefix': 'Sie sind Horus AI, ein Experte für altägyptische Artefakte. Bitte antworten Sie auf Deutsch.',
        'greeting': 'Grüße! Ich bin Horus AI, Hüter des altägyptischen Wissens. Ich habe Ihr Artefakt analysiert und bin hier, um alle Ihre Fragen dazu zu beantworten. Was möchten Sie wissen?'
    }
}

def detect_language(text):
    """
    Simple language detection based on character sets and common words.
    """
    # Check for Arabic characters
    if re.search(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]', text):
        return 'ar'
    
    # Check for French characters and words
    french_words = ['bonjour', 'salut', 'merci', 'oui', 'non', 'comment', 'pourquoi', 'où', 'quand']
    if any(word in text.lower() for word in french_words):
        return 'fr'
    
    # Check for German characters and words
    german_words = ['hallo', 'guten', 'danke', 'ja', 'nein', 'wie', 'warum', 'wo', 'wann', 'ä', 'ö', 'ü', 'ß']
    if any(word in text.lower() for word in german_words) or re.search(r'[äöüß]', text.lower()):
        return 'de'
    
    # Default to English
    return 'en'

def format_markdown(text):
    """
    Convert plain text to markdown format for better display.
    """
    if not text:
        return text
    
    # Convert line breaks to markdown
    text = text.replace('\n\n', '\n\n')
    
    # Add emphasis to important terms
    text = re.sub(r'\b(ancient|egyptian|pharaoh|pyramid|temple|artifact|tomb|hieroglyph|mummy|gods?|goddess)\b', r'**\1**', text, flags=re.IGNORECASE)
    
    # Format lists
    lines = text.split('\n')
    formatted_lines = []
    in_list = False
    
    for line in lines:
        line = line.strip()
        if line.startswith(('-', '•', '*', '1.', '2.', '3.')):
            if not in_list:
                formatted_lines.append('')
            formatted_lines.append(f'• {line[1:].strip()}')
            in_list = True
        elif line and in_list:
            formatted_lines.append('')
            formatted_lines.append(line)
            in_list = False
        else:
            formatted_lines.append(line)
    
    return '\n'.join(formatted_lines)

def generate_chat_response(user_message, artifact_name, artifact_description, language='en'):
    """
    Generates a response from the Gemini LLM based on user message and artifact context.
    Supports multiple languages and markdown formatting.
    """
    try:
        # Validate language
        if language not in LANGUAGES:
            language = 'en'
        
        model = genai.GenerativeModel('models/gemini-2.5-flash')
        
        # Get language-specific prompt
        lang_config = LANGUAGES[language]
        
        # Construct prompt with language-specific instructions
        prompt = (
            f"{lang_config['prompt_prefix']}\n\n"
            f"Context: A user is asking about an artifact identified as '{artifact_name}'. "
            f"Description: '{artifact_description}'.\n\n"
            f"Instructions: Please respond in {lang_config['name']} and format your response with markdown for better readability. "
            f"Use **bold** for important terms, bullet points for lists, and proper paragraph breaks.\n\n"
            f"User: {user_message}\n"
            f"Horus AI:"
        )

        response = model.generate_content(prompt)
        response_text = response.text
        
        # Format the response with markdown
        formatted_response = format_markdown(response_text)
        
        return formatted_response
        
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        error_messages = {
            'en': "I apologize, I encountered an issue trying to respond. Please try again later.",
            'ar': "أعتذر، واجهت مشكلة في محاولة الرد. يرجى المحاولة مرة أخرى لاحقاً.",
            'fr': "Je m'excuse, j'ai rencontré un problème en essayant de répondre. Veuillez réessayer plus tard.",
            'de': "Entschuldigung, ich hatte ein Problem beim Versuch zu antworten. Bitte versuchen Sie es später erneut."
        }
        return error_messages.get(language, error_messages['en'])

def get_greeting_message(language='en'):
    """
    Get the appropriate greeting message for the selected language.
    """
    if language not in LANGUAGES:
        language = 'en'
    return LANGUAGES[language]['greeting']

def get_available_languages():
    """
    Get list of available languages.
    """
    return LANGUAGES
