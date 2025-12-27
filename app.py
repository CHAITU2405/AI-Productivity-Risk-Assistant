from flask import Flask, render_template, request, jsonify
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['DATABASE'] = 'workguard.db'

# Ensure uploads directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize database
def init_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    
    # Contracts table
    c.execute('''CREATE TABLE IF NOT EXISTS contracts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  filename TEXT,
                  upload_date TIMESTAMP,
                  risk_score REAL,
                  analysis_data TEXT)''')
    
    # Meetings table
    c.execute('''CREATE TABLE IF NOT EXISTS meetings
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  transcript TEXT,
                  processed_date TIMESTAMP,
                  action_items TEXT)''')
    
    # Rewrites table
    c.execute('''CREATE TABLE IF NOT EXISTS rewrites
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  original_text TEXT,
                  rewritten_text TEXT,
                  tone TEXT,
                  created_date TIMESTAMP)''')
    
    # Settings table
    c.execute('''CREATE TABLE IF NOT EXISTS settings
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  key TEXT UNIQUE,
                  value TEXT)''')
    
    conn.commit()
    conn.close()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/contract')
def contract():
    return render_template('contract.html')

@app.route('/meetings')
def meetings():
    return render_template('meetings.html')

@app.route('/rewrite')
def rewrite():
    return render_template('rewrite.html')

@app.route('/settings')
def settings():
    return render_template('settings.html')

# API Routes
@app.route('/api/analyze_contract', methods=['POST'])
def analyze_contract():
    """Analyze contract for risks"""
    # Basic implementation - will be enhanced later
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # TODO: Add actual contract analysis logic (PDF parsing, NLP, etc.)
    # For now, return mock data
    return jsonify({
        'status': 'success',
        'risks': [
            {
                'type': 'Critical Risk',
                'category': 'Auto-Renewal',
                'description': 'Clause 4.2 locks you into a 5-year term automatically unless cancelled 180 days prior.'
            },
            {
                'type': 'Caution',
                'category': 'Indemnity Cap',
                'description': 'Liability cap is set to $1,000, which is below industry standard for this service type.'
            }
        ]
    })

@app.route('/api/process_meeting', methods=['POST'])
def process_meeting():
    """Process meeting transcript and extract action items"""
    data = request.json
    transcript = data.get('transcript', '')
    
    # TODO: Add actual NLP processing logic
    # For now, return mock data
    action_items = [
        {
            'task': 'Update Security Protocols',
            'owner': 'John',
            'due': 'Monday',
            'priority': 'high'
        },
        {
            'task': 'Send Client Contract',
            'owner': 'Sarah',
            'due': 'Tomorrow',
            'priority': 'medium'
        },
        {
            'task': 'Organize Team Lunch',
            'owner': 'Mike',
            'due': 'Next Week',
            'priority': 'low'
        }
    ]
    
    return jsonify({
        'status': 'success',
        'action_items': action_items
    })

@app.route('/api/rewrite_text', methods=['POST'])
def rewrite_text():
    """Rewrite text with specified tone"""
    data = request.json
    original_text = data.get('text', '')
    tone = data.get('tone', 'Professional')
    
    # TODO: Add actual text rewriting logic
    # Mock responses for now
    responses = {
        'Professional': "We noticed the deadline has passed. Could you please provide an update? It is crucial we receive the files to maintain our schedule.",
        'Diplomatic': "I wanted to check in regarding the missed deadline. We are concerned about the timeline and would appreciate the files as soon as possible.",
        'Assertive': "The deadline for this deliverable has passed. Please submit the files immediately to ensure we do not jeopardize the project."
    }
    
    return jsonify({
        'status': 'success',
        'rewritten_text': responses.get(tone, responses['Professional'])
    })

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)

