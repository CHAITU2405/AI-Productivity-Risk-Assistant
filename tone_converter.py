"""
Tone Converter Module
Handles tone analysis and conversion using transformers for analysis and Gemini API for conversion
"""
import os
import warnings
from transformers import pipeline
from dotenv import load_dotenv

# Suppress deprecation warning for google.generativeai
with warnings.catch_warnings():
    warnings.simplefilter("ignore", FutureWarning)
    import google.generativeai as genai

# Load environment variables
load_dotenv()

# Global models (loaded once)
_tone_classifier = None
_gemini_configured = False

def configure_gemini():
    """Configure Gemini API with key from environment"""
    global _gemini_configured
    if not _gemini_configured:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            # Fallback to default (user should set this in .env file)
            api_key = "AIzaSyBijLYDKCbgHqAiM5EDA6Rt6dJiSJ42hx8"
            print("Warning: Using default API key. Please set GEMINI_API_KEY in .env file for production.")
        
        genai.configure(api_key=api_key)
        _gemini_configured = True
    return genai

def load_models():
    """Load ML models (lazy loading)"""
    global _tone_classifier
    try:
        if _tone_classifier is None:
            print("Loading tone classifier model...")
            _tone_classifier = pipeline(
                "text-classification",
                model="j-hartmann/emotion-english-distilroberta-base",
                return_all_scores=True
            )
            print("Tone classifier loaded successfully")
        
        # Configure Gemini for tone conversion
        configure_gemini()
    except Exception as e:
        print(f"Error loading models: {e}")
        raise
    return _tone_classifier

def analyze_tone(text):
    """Analyze the tone of input text"""
    classifier = load_models()
    scores = classifier(text)[0]
    dominant = max(scores, key=lambda x: x["score"])
    return {
        "tone": dominant["label"],
        "score": float(dominant["score"]),
        "all_scores": {item["label"]: float(item["score"]) for item in scores}
    }

def convert_tone(text, target_tone):
    """
    Convert text to specified tone using Gemini API
    
    Args:
        text: Input text to convert
        target_tone: Target tone (professional, persuasive, empathetic, executive, viral, etc.)
    
    Returns:
        Converted text
    """
    if not text or not text.strip():
        return text
    
    text = text.strip()
    
    # Try Gemini API conversion first
    try:
        return _convert_with_gemini(text, target_tone)
    except Exception as e:
        print(f"Gemini conversion failed: {e}, falling back to rule-based")
        # Fallback to rule-based conversion
        tone_mapping = {
            'professional': _convert_to_professional,
            'persuasive': _convert_to_persuasive,
            'empathetic': _convert_to_empathetic,
            'executive': _convert_to_executive,
            'viral': _convert_to_viral,
            # Legacy support
            'polite': _convert_to_polite,
            'formal': _convert_to_formal,
            'friendly': _convert_to_friendly,
            'neutral': lambda x: x,
            'angry': _convert_to_angry,
            # Frontend also uses these
            'Professional': _convert_to_professional,
            'Diplomatic': _convert_to_professional,
            'Assertive': _convert_to_executive
        }
        
        converter = tone_mapping.get(target_tone.lower(), _convert_to_professional)
        return converter(text)

def _convert_with_gemini(text, target_tone):
    """Convert text using Gemini API"""
    try:
        configure_gemini()
        
        # Create detailed prompts for different tones
        tone_descriptions = {
            'professional': "professional, diplomatic, and business-appropriate tone. Use formal language, proper grammar, and maintain a respectful and courteous approach.",
            'persuasive': "persuasive and compelling tone. Make it engaging, use strong action words, highlight benefits, and create a sense of urgency or opportunity.",
            'empathetic': "empathetic and understanding tone. Show care, consideration, and emotional intelligence. Use warm and supportive language.",
            'executive': "concise, direct, and executive tone. Be brief, action-oriented, and authoritative. Remove unnecessary words and get straight to the point.",
            'viral': "viral, engaging, and exciting tone. Make it shareable, use emojis appropriately, create excitement, and make it conversational and energetic.",
            'polite': "polite and courteous tone. Use please, thank you, and respectful language throughout.",
            'formal': "formal and professional tone. Use complete sentences, proper grammar, and formal business language.",
            'friendly': "friendly and warm tone. Be conversational, approachable, and use casual but respectful language.",
            'diplomatic': "diplomatic and tactful tone. Be careful with word choice, avoid direct confrontation, and maintain professionalism.",
            'assertive': "assertive and confident tone. Be direct, clear, and confident without being aggressive.",
        }
        
        tone_description = tone_descriptions.get(target_tone.lower(), tone_descriptions['professional'])
        
        # Create the prompt for Gemini
        prompt = f"""Rewrite the following text in a {tone_description}

Original text: "{text}"

Requirements:
- Maintain the original meaning and key information
- Transform the entire text to match the requested tone
- Do not just add a prefix - rewrite the whole message
- Keep it natural and readable
- Return only the rewritten text, no explanations

Rewritten text:"""
        
        # Use Gemini model to generate the rewritten text
        model = genai.GenerativeModel(model_name="gemini-2.5-flash")  # Using same model as meeting processor
        
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 2048,  # Increased for longer responses
            }
        )
        
        # Extract the generated text
        rewritten_text = response.text.strip()
        
        # Clean up the response - remove any quotes or extra formatting
        rewritten_text = rewritten_text.strip('"').strip("'").strip()
        
        # If the response seems valid, return it
        if rewritten_text and len(rewritten_text) > len(text) * 0.3:
            return rewritten_text
        else:
            raise ValueError("Gemini did not generate a proper conversion")
            
    except Exception as e:
        error_msg = str(e)
        # Handle specific Gemini API errors
        if "quota" in error_msg.lower() or "429" in error_msg:
            raise Exception("Gemini API quota exceeded. Please check your API usage or wait for quota reset.")
        elif "api key" in error_msg.lower() or "401" in error_msg or "403" in error_msg:
            raise Exception("Invalid or missing Gemini API key. Please check your GEMINI_API_KEY environment variable.")
        else:
            raise Exception(f"Gemini API error: {error_msg}")

def _convert_to_professional(text):
    """Convert to professional and diplomatic tone"""
    import re
    
    text = text.strip()
    
    # Comprehensive replacements for professional tone
    replacements = {
        # Contractions
        r"\bcan't\b": "cannot",
        r"\bwon't\b": "will not",
        r"\bdon't\b": "do not",
        r"\bdoesn't\b": "does not",
        r"\bdidn't\b": "did not",
        r"\bisn't\b": "is not",
        r"\baren't\b": "are not",
        r"\bwasn't\b": "was not",
        r"\bweren't\b": "were not",
        r"\bhaven't\b": "have not",
        r"\bhasn't\b": "has not",
        r"\bhadn't\b": "had not",
        r"\bI'm\b": "I am",
        r"\byou're\b": "you are",
        r"\bwe're\b": "we are",
        r"\bthey're\b": "they are",
        r"\bit's\b": "it is",
        r"\bthat's\b": "that is",
        r"\bwhat's\b": "what is",
        
        # Direct commands to polite requests
        r"\bI need\b": "I would appreciate",
        r"\bYou must\b": "Please ensure that you",
        r"\bYou need to\b": "It would be helpful if you could",
        r"\bYou should\b": "I recommend that you",
        r"\bYou have to\b": "It is necessary to",
        
        # Urgency softening
        r"\bright now\b": "at your earliest convenience",
        r"\basap\b": "as soon as possible",
        r"\bas soon as possible\b": "at your earliest convenience",
        r"\burgent\b": "time-sensitive",
        r"\bimmediately\b": "promptly",
        r"\bquickly\b": "in a timely manner",
        
        # Casual to formal
        r"\bhey\b": "Hello",
        r"\bhi\b": "Hello",
        r"\byeah\b": "yes",
        r"\bnope\b": "no",
        r"\bsure\b": "certainly",
        r"\bokay\b": "understood",
        r"\bok\b": "understood",
        
        # Aggressive to diplomatic
        r"\bI want\b": "I would like",
        r"\bI demand\b": "I would appreciate",
        r"\bYou're wrong\b": "I believe there may be a misunderstanding",
        r"\bThat's wrong\b": "I believe there may be an error",
    }
    
    # Apply replacements (case-insensitive where appropriate)
    for pattern, replacement in replacements.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    # Fix punctuation
    if text.endswith('!'):
        text = text[:-1] + '.'
    
    # Ensure proper capitalization
    if text and not text[0].isupper():
        text = text[0].upper() + text[1:] if len(text) > 1 else text.upper()
    
    # Remove multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def _convert_to_persuasive(text):
    """Convert to persuasive and sales-oriented tone"""
    import re
    
    text = text.strip()
    
    # Enhance with compelling language
    enhancements = {
        r"\bneed\b": "opportunity",
        r"\bmust\b": "should strongly consider",
        r"\bimportant\b": "crucial advantage",
        r"\bgood\b": "excellent",
        r"\bgreat\b": "outstanding",
        r"\bhelp\b": "benefit",
        r"\bwant\b": "desire",
        r"\bshould\b": "would benefit from",
        r"\bcan\b": "have the power to",
        r"\bthink\b": "consider",
        r"\bbelieve\b": "are confident",
    }
    
    # Apply enhancements
    for pattern, replacement in enhancements.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    # Add engaging framing if not already present
    engaging_phrases = ["imagine", "consider", "discover", "unlock", "leverage", "transform"]
    if not any(text.lower().startswith(phrase) for phrase in engaging_phrases):
        # Add a compelling opener
        if not text[0].isupper():
            text = text.capitalize()
        text = f"Consider the impact: {text}"
    
    # Enhance with action-oriented language
    text = text.replace(".", "—a game-changing opportunity.").replace("!", "—an exciting opportunity!")
    
    # Remove excessive punctuation
    text = re.sub(r'[!]{2,}', '!', text)
    text = re.sub(r'[.]{2,}', '.', text)
    
    return text

def _convert_to_empathetic(text):
    """Convert to empathetic and understanding tone"""
    import re
    
    text = text.strip()
    
    # Soften the language comprehensively
    soft_replacements = {
        r"\byou must\b": "it would be helpful if you could",
        r"\byou need to\b": "we could benefit from",
        r"\bI need\b": "I would appreciate",
        r"\bI want\b": "I would like",
        r"\bI demand\b": "I would appreciate",
        r"\burgent\b": "time-sensitive",
        r"\bimmediately\b": "when you have a moment",
        r"\bquickly\b": "at your convenience",
        r"\byou should\b": "it might be helpful if you",
        r"\byou have to\b": "it would be beneficial to",
        r"\bproblem\b": "challenge",
        r"\bissue\b": "situation",
        r"\bwrong\b": "different perspective",
        r"\bfailed\b": "didn't work as expected",
        r"\berror\b": "unexpected outcome",
    }
    
    # Apply replacements
    for pattern, replacement in soft_replacements.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    # Add empathetic framing if not already present
    empathetic_phrases = ["i understand", "i recognize", "i appreciate", "i see", "i know"]
    if not any(text.lower().startswith(phrase) for phrase in empathetic_phrases):
        text = f"I understand that {text.lower()}"
    
    # Ensure proper capitalization
    if text and not text[0].isupper():
        text = text[0].upper() + text[1:] if len(text) > 1 else text.upper()
    
    return text

def _convert_to_executive(text):
    """Convert to executive and direct tone"""
    import re
    
    text = text.strip()
    
    # Remove filler words
    filler_words = ["actually", "basically", "literally", "really", "very", "quite", "rather", "somewhat", "pretty"]
    words = text.split()
    words = [w for w in words if w.lower() not in filler_words]
    text = " ".join(words)
    
    # Make it action-oriented and direct
    executive_replacements = {
        r"\bshould\b": "must",
        r"\bcould\b": "will",
        r"\bmight\b": "will",
        r"\bperhaps\b": "",
        r"\bmaybe\b": "",
        r"\bI think\b": "I believe",
        r"\bI feel\b": "I know",
        r"\bwe should consider\b": "we will",
        r"\bit would be good\b": "it is essential",
        r"\bplease\b": "",
        r"\bkindly\b": "",
    }
    
    for pattern, replacement in executive_replacements.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    # Remove unnecessary words
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Ensure proper capitalization
    if text and not text[0].isupper():
        text = text[0].upper() + text[1:] if len(text) > 1 else text.upper()
    
    # Remove trailing period for more impact (executive style)
    if text.endswith('.'):
        text = text[:-1]
    
    return text

def _convert_to_viral(text):
    """Convert to viral and engaging tone"""
    import re
    
    text = text.strip()
    
    # Add emojis and engaging language
    viral_enhancements = {
        r"\bgreat\b": "amazing 🚀",
        r"\bgood\b": "awesome ✨",
        r"\bimportant\b": "game-changing 💡",
        r"\bexcited\b": "pumped 🔥",
        r"\bexcellent\b": "incredible 🎯",
        r"\bamazing\b": "mind-blowing 🔥",
        r"\bfantastic\b": "epic ⚡",
        r"\bwonderful\b": "stunning ✨",
    }
    
    for pattern, replacement in viral_enhancements.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    # Make it more conversational and inclusive
    text = text.replace("I", "we")
    text = re.sub(r'\bmy\b', 'our', text, flags=re.IGNORECASE)
    
    # Add engaging punctuation and emojis
    if not any(emoji in text for emoji in ['🚀', '✨', '🔥', '💡', '🎯', '⚡']):
        if text.endswith('.'):
            text = text[:-1] + " 🚀"
        elif not text.endswith(('!', '?')):
            text = text + " 🚀"
    
    # Enhance with exclamation if needed
    if not text.endswith('!'):
        text = text.replace('.', '!', 1)  # Replace first period with exclamation
    
    return text

# Legacy conversion functions
def _convert_to_polite(text):
    """Convert to polite tone"""
    import re
    text = text.strip()
    
    # Apply polite replacements
    polite_replacements = {
        r"\bI need\b": "I would appreciate",
        r"\bI want\b": "I would like",
        r"\byou must\b": "please consider",
        r"\byou should\b": "it would be helpful if you could",
    }
    
    for pattern, replacement in polite_replacements.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    if not text.lower().startswith(("please", "i would", "it would", "kindly")):
        text = f"Please note that {text.lower()}"
    
    if text and not text[0].isupper():
        text = text[0].upper() + text[1:] if len(text) > 1 else text.upper()
    
    return text

def _convert_to_formal(text):
    """Convert to formal tone"""
    import re
    text = text.strip()
    
    # Apply formal replacements
    formal_replacements = {
        r"\bcan't\b": "cannot",
        r"\bwon't\b": "will not",
        r"\bdon't\b": "do not",
        r"\bI'm\b": "I am",
        r"\byou're\b": "you are",
        r"\bwe're\b": "we are",
        r"\bhey\b": "",
        r"\bhi\b": "",
    }
    
    for pattern, replacement in formal_replacements.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    text = re.sub(r'\s+', ' ', text).strip()
    
    if not text.lower().startswith(("this is", "i am writing", "please be advised")):
        text = f"This is to formally inform you that {text.lower()}"
    
    if text and not text[0].isupper():
        text = text[0].upper() + text[1:] if len(text) > 1 else text.upper()
    
    return text

def _convert_to_friendly(text):
    """Convert to friendly tone"""
    import re
    text = text.strip()
    
    # Make it more conversational
    friendly_replacements = {
        r"\bcannot\b": "can't",
        r"\bwill not\b": "won't",
        r"\bdo not\b": "don't",
        r"\bI would like\b": "I'd like",
        r"\bI would appreciate\b": "I'd appreciate",
        r"\bplease ensure\b": "make sure",
        r"\bkindly\b": "",
    }
    
    for pattern, replacement in friendly_replacements.items():
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    
    text = re.sub(r'\s+', ' ', text).strip()
    
    if not text.lower().startswith(("hey", "hi", "hello")):
        text = f"Hey! 😊 {text}"
    
    return text

def _convert_to_angry(text):
    """Convert to angry tone"""
    text = text.strip().upper()
    if not text.endswith('!'):
        text += "!"
    return text

