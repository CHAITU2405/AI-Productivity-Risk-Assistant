"""
Meeting Audio/Video Processor using Google Gemini API
"""
import os
import time
import warnings
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Suppress deprecation warning for google.generativeai (still works, just deprecated)
with warnings.catch_warnings():
    warnings.simplefilter("ignore", FutureWarning)
    import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configure Gemini API
def configure_gemini():
    """Configure Gemini API with key from environment or config"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        # Fallback to default (user should set this in .env file)
        api_key = "AIzaSyBijLYDKCbgHqAiM5EDA6Rt6dJiSJ42hx8"  # User provided key
        print("Warning: Using default API key. Please set GEMINI_API_KEY in .env file for production.")
    
    genai.configure(api_key=api_key)
    return genai

def process_meeting_audio(audio_file_path):
    """
    Process meeting audio/video file using Gemini API
    Based on working Colab implementation
    
    Args:
        audio_file_path: Path to the audio/video file
        
    Returns:
        dict with summary, action_items, key_points, and deadlines
    """
    try:
        configure_gemini()  # Just configure, don't need return value
        
        print(f"Uploading '{audio_file_path}' to Gemini...")
        
        # 1. Upload file
        try:
            audio_file = genai.upload_file(path=audio_file_path)
        except Exception as e:
            error_msg = str(e)
            print(f"Upload failed: {e}")
            
            # Check for quota/rate limit errors
            if "quota" in error_msg.lower() or "429" in error_msg or "rate limit" in error_msg.lower():
                return {
                    'error': "API quota exceeded. Please check your Gemini API usage at https://ai.dev/usage or wait for quota reset. You may need to upgrade your plan or get a new API key."
                }
            elif "401" in error_msg or "unauthorized" in error_msg.lower() or "invalid" in error_msg.lower():
                return {
                    'error': "Invalid API key. Please check your GEMINI_API_KEY in .env file or get a new key from https://makersuite.google.com/app/apikey"
                }
            
            return {
                'error': f"Upload failed: {error_msg}"
            }
        
        print(f"Upload complete. File Name: {audio_file.name}")
        
        # 2. Polling - wait for file to be processed (using Colab logic)
        file_name = audio_file.name
        retry_count = 0
        
        while True:
            try:
                audio_file = genai.get_file(file_name)
                
                if audio_file.state.name == "ACTIVE":
                    print("Processing complete. Ready.")
                    break
                elif audio_file.state.name == "FAILED":
                    raise ValueError("Processing failed.")
                elif audio_file.state.name == "PROCESSING":
                    print("Processing... (waiting 5s)")
                    time.sleep(5)
            except Exception as e:
                retry_count += 1
                print(f"Server error ({retry_count}/10): {e}")
                time.sleep(5)
                
                # If it fails 10 times in a row, kill it to prevent infinite loops
                if retry_count > 10:
                    print("Critical: File is stuck on server side. Aborting.")
                    return {
                        'error': "File processing timed out after 10 retries. Please try again."
                    }
        
        # 3. Generate Content with detailed prompt
        print("Analyzing...")
        
        # First get a simple summary (like Colab)
        simple_prompt = "Summarize this meeting and list action items."
        model = genai.GenerativeModel(model_name="gemini-2.5-flash")  # Using same model as Colab
        
        try:
            response = model.generate_content([audio_file, simple_prompt])
            response_text = response.text
            print(response_text)  # Debug output
            
            # Now get structured data with a more detailed prompt
            detailed_prompt = """Analyze this meeting recording and provide a comprehensive summary in the following JSON format:

{
    "summary": "A clear, concise summary of the entire meeting (2-3 paragraphs)",
    "key_points": ["Key point 1", "Key point 2", "Key point 3"],
    "action_items": [
        {
            "task": "Task description",
            "owner": "Person responsible",
            "deadline": "Deadline if mentioned, or 'Not specified'",
            "priority": "high/medium/low"
        }
    ],
    "deadlines": ["Deadline 1", "Deadline 2"],
    "participants": ["Participant 1", "Participant 2"],
    "decisions": ["Decision 1", "Decision 2"]
}

Extract all action items with clear owners and deadlines. Identify all deadlines mentioned in the meeting. List all key decisions made. Provide a summary that gives complete clarity about what happened in the meeting."""
            
            detailed_response = model.generate_content([audio_file, detailed_prompt])
            detailed_text = detailed_response.text
            
            # Try to extract JSON from response
            import json
            import re
            
            # Try to find JSON in the response
            json_match = re.search(r'\{.*\}', detailed_text, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group())
                    return result
                except json.JSONDecodeError:
                    # If JSON parsing fails, parse the simple response
                    pass
            
            # Fallback: parse the simple response for action items
            # Try to extract action items from the simple response
            action_items = []
            lines = response_text.split('\n')
            for line in lines:
                if any(keyword in line.lower() for keyword in ['action', 'task', 'todo', 'need to', 'will']):
                    action_items.append({
                        'task': line.strip(),
                        'owner': 'Not specified',
                        'deadline': 'Not specified',
                        'priority': 'medium'
                    })
            
            return {
                'summary': response_text,
                'key_points': [],
                'action_items': action_items if action_items else [],
                'deadlines': [],
                'participants': [],
                'decisions': [],
                'raw_response': response_text
            }
            
        except Exception as e:
            error_msg = str(e)
            print(f"Generation failed: {e}")
            
            # Check for quota/rate limit errors
            if "quota" in error_msg.lower() or "429" in error_msg or "rate limit" in error_msg.lower():
                return {
                    'error': "API quota exceeded. Please check your Gemini API usage at https://ai.dev/usage or wait for quota reset. You may need to upgrade your plan or get a new API key."
                }
            elif "401" in error_msg or "unauthorized" in error_msg.lower() or "invalid" in error_msg.lower():
                return {
                    'error': "Invalid API key. Please check your GEMINI_API_KEY in .env file or get a new key from https://makersuite.google.com/app/apikey"
                }
            
            return {
                'error': f"Content generation failed: {error_msg}"
            }
            
    except Exception as e:
        print(f"Error processing meeting: {e}")
        return {
            'error': f"Processing error: {str(e)}"
        }
    finally:
        # Clean up uploaded file if possible
        try:
            if 'audio_file' in locals() and hasattr(audio_file, 'name'):
                genai.delete_file(audio_file.name)
        except:
            pass

def process_meeting_transcript(transcript_text):
    """
    Process meeting transcript text (fallback if no audio)
    
    Args:
        transcript_text: Text transcript of the meeting
        
    Returns:
        dict with summary, action_items, key_points, and deadlines
    """
    try:
        configure_gemini()  # Just configure, don't need return value
        
        prompt = f"""Analyze this meeting transcript and provide a comprehensive summary in the following JSON format:

{{
    "summary": "A clear, concise summary of the entire meeting (2-3 paragraphs)",
    "key_points": ["Key point 1", "Key point 2", "Key point 3"],
    "action_items": [
        {{
            "task": "Task description",
            "owner": "Person responsible",
            "deadline": "Deadline if mentioned, or 'Not specified'",
            "priority": "high/medium/low"
        }}
    ],
    "deadlines": ["Deadline 1", "Deadline 2"],
    "participants": ["Participant 1", "Participant 2"],
    "decisions": ["Decision 1", "Decision 2"]
}}

Meeting Transcript:
{transcript_text}

Extract all action items with clear owners and deadlines. Identify all deadlines mentioned in the meeting. List all key decisions made. Provide a summary that gives complete clarity about what happened in the meeting."""
        
        model = genai.GenerativeModel(model_name="gemini-2.0-flash-exp")
        response = model.generate_content(prompt)
        
        # Parse response similar to audio processing
        import json
        import re
        
        response_text = response.text
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        
        if json_match:
            try:
                result = json.loads(json_match.group())
                return result
            except json.JSONDecodeError:
                pass
        
        return {
            'summary': response_text,
            'key_points': [],
            'action_items': [],
            'deadlines': [],
            'participants': [],
            'decisions': [],
            'raw_response': response_text
        }
        
    except Exception as e:
        error_msg = str(e)
        
        # Check for quota/rate limit errors
        if "quota" in error_msg.lower() or "429" in error_msg or "rate limit" in error_msg.lower():
            return {
                'error': "API quota exceeded. Please check your Gemini API usage at https://ai.dev/usage or wait for quota reset. You may need to upgrade your plan or get a new API key."
            }
        elif "401" in error_msg or "unauthorized" in error_msg.lower() or "invalid" in error_msg.lower():
            return {
                'error': "Invalid API key. Please check your GEMINI_API_KEY in .env file or get a new key from https://makersuite.google.com/app/apikey"
            }
        
        return {
            'error': f"Processing error: {error_msg}"
        }

