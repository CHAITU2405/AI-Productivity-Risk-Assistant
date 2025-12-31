from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
import sqlite3
import os
import hashlib
import json
from datetime import datetime
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from tone_converter import convert_tone, analyze_tone
from meeting_processor import process_meeting_audio, process_meeting_transcript
from contract_analyzer import analyze_contract
from report_generator import generate_contract_pdf, generate_meeting_pdf

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MEETING_UPLOAD_FOLDER'] = 'uploads/meetings'
app.config['CONTRACT_UPLOAD_FOLDER'] = 'uploads/contracts'
app.config['REPORTS_FOLDER'] = 'reports'
app.config['DATABASE'] = 'workguard.db'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size
app.config['ALLOWED_EXTENSIONS'] = {'mp3', 'mp4', 'wav', 'm4a', 'webm', 'ogg', 'avi', 'mov'}
app.config['ALLOWED_PDF_EXTENSIONS'] = {'pdf'}

# Ensure uploads and reports directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['MEETING_UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['CONTRACT_UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['REPORTS_FOLDER'], exist_ok=True)

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Initialize database
def init_db():
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  email TEXT UNIQUE NOT NULL,
                  password_hash TEXT NOT NULL,
                  first_name TEXT,
                  last_name TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Reports table (for both contract and meeting reports)
    c.execute('''CREATE TABLE IF NOT EXISTS reports
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  report_type TEXT NOT NULL,
                  title TEXT,
                  filename TEXT,
                  pdf_path TEXT,
                  report_data TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users(id))''')
    
    # Rewrites table (for tone converter - no PDF needed)
    c.execute('''CREATE TABLE IF NOT EXISTS rewrites
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  original_text TEXT,
                  rewritten_text TEXT,
                  tone TEXT,
                  created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users(id))''')
    
    # Settings table
    c.execute('''CREATE TABLE IF NOT EXISTS settings
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  key TEXT,
                  value TEXT,
                  FOREIGN KEY (user_id) REFERENCES users(id))''')
    
    conn.commit()
    conn.close()

def get_user_id():
    """Get current user ID from session"""
    return session.get('user_id')

def require_login(f):
    """Decorator to require login"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    """Landing page - public, no login required"""
    return render_template('index.html')

@app.route('/dashboard')
@require_login
def dashboard():
    """Dashboard page - shows recent reports, requires login"""
    # Get recent reports for dashboard
    user_id = get_user_id()
    conn = sqlite3.connect(app.config['DATABASE'])
    c = conn.cursor()
    c.execute('''SELECT id, report_type, title, filename, created_at 
                 FROM reports 
                 WHERE user_id = ? 
                 ORDER BY created_at DESC 
                 LIMIT 10''', (user_id,))
    recent_reports = c.fetchall()
    conn.close()
    
    reports = [{
        'id': r[0],
        'type': r[1],
        'title': r[2],
        'filename': r[3],
        'created_at': r[4]
    } for r in recent_reports]
    
    return render_template('dashboard.html', recent_reports=reports)

@app.route('/login')
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/register')
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/contract')
@require_login
def contract():
    return render_template('contract.html')

@app.route('/meetings')
@require_login
def meetings():
    return render_template('meetings.html')

@app.route('/rewrite')
@require_login
def rewrite():
    return render_template('rewrite.html')

@app.route('/settings')
@require_login
def settings():
    return render_template('settings.html')

@app.route('/api/view_report/<int:report_id>')
@require_login
def view_report(report_id):
    """Get report data for viewing"""
    try:
        user_id = get_user_id()
        conn = sqlite3.connect(app.config['DATABASE'])
        c = conn.cursor()
        c.execute('SELECT report_type, report_data FROM reports WHERE id = ? AND user_id = ?', (report_id, user_id))
        report = c.fetchone()
        conn.close()
        
        if not report:
            return jsonify({'status': 'error', 'error': 'Report not found'}), 404
        
        report_type = report[0]
        report_data_json = report[1]
        
        import json as json_lib
        report_data = json_lib.loads(report_data_json) if report_data_json else {}
        
        # Add report_id and status to response
        report_data['report_id'] = report_id
        report_data['status'] = 'success'
        
        return jsonify(report_data)
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/download_report/<int:report_id>')
@require_login
def download_report(report_id):
    """Download a PDF report - regenerates if needed to include all heatmaps"""
    try:
        user_id = get_user_id()
        conn = sqlite3.connect(app.config['DATABASE'])
        c = conn.cursor()
        c.execute('SELECT pdf_path, filename, report_type, report_data FROM reports WHERE id = ? AND user_id = ?', (report_id, user_id))
        report = c.fetchone()
        conn.close()
        
        if not report:
            return jsonify({'status': 'error', 'error': 'Report not found'}), 404
        
        pdf_path = report[0]
        filename = report[1] or 'report.pdf'
        report_type = report[2]
        report_data_json = report[3]
        
        # If PDF doesn't exist or is a contract report, regenerate it to ensure all heatmaps are included
        if not os.path.exists(pdf_path) or report_type == 'contract':
            try:
                import json as json_lib
                report_data = json_lib.loads(report_data_json) if report_data_json else {}
                
                if report_type == 'contract':
                    # Regenerate contract PDF with all heatmaps
                    heatmap_data = report_data.get('heatmap_data', [])
                    print(f"DEBUG: Download - Found {len(heatmap_data)} heatmaps in stored data")
                    
                    # Ensure we have all 3 heatmaps - if not, try to generate missing ones
                    if len(heatmap_data) < 3:
                        print(f"WARNING: Only {len(heatmap_data)} heatmaps found in stored data, expected 3")
                        print(f"Available heatmap types: {[h.get('type', 'unknown') for h in heatmap_data]}")
                        # The PDF generator will handle showing what's available
                    
                    # Always regenerate to ensure PDF is up to date
                    try:
                        generate_contract_pdf(report_data, heatmap_data, pdf_path)
                        print(f"DEBUG: PDF regenerated successfully with {len(heatmap_data)} heatmaps")
                    except Exception as pdf_gen_error:
                        print(f"ERROR regenerating PDF: {pdf_gen_error}")
                        import traceback
                        traceback.print_exc()
                        raise
                elif report_type == 'meeting':
                    # Regenerate meeting PDF
                    generate_meeting_pdf(report_data, pdf_path)
            except Exception as regen_error:
                print(f"Error regenerating PDF: {regen_error}")
                # If regeneration fails and file doesn't exist, return error
                if not os.path.exists(pdf_path):
                    return jsonify({'status': 'error', 'error': 'PDF file not found and could not be regenerated'}), 404
        
        if not os.path.exists(pdf_path):
            return jsonify({'status': 'error', 'error': 'PDF file not found'}), 404
        
        return send_file(pdf_path, as_attachment=True, download_name=filename)
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

# Authentication API Routes
@app.route('/api/register', methods=['POST'])
def register_user():
    """Register a new user"""
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        
        if not email or not password:
            return jsonify({'status': 'error', 'error': 'Email and password are required'}), 400
        
        conn = sqlite3.connect(app.config['DATABASE'])
        c = conn.cursor()
        
        # Check if user exists
        c.execute('SELECT id FROM users WHERE email = ?', (email,))
        if c.fetchone():
            conn.close()
            return jsonify({'status': 'error', 'error': 'Email already registered'}), 400
        
        # Create user
        password_hash = generate_password_hash(password)
        c.execute('''INSERT INTO users (email, password_hash, first_name, last_name)
                     VALUES (?, ?, ?, ?)''',
                 (email, password_hash, first_name, last_name))
        user_id = c.lastrowid
        conn.commit()
        conn.close()
        
        # Auto-login
        session['user_id'] = user_id
        session['email'] = email
        
        return jsonify({
            'status': 'success',
            'message': 'Registration successful',
            'user_id': user_id,
            'redirect': '/dashboard'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login_user():
    """Login user"""
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({'status': 'error', 'error': 'Email and password are required'}), 400
        
        conn = sqlite3.connect(app.config['DATABASE'])
        c = conn.cursor()
        c.execute('SELECT id, password_hash, first_name, last_name FROM users WHERE email = ?', (email,))
        user = c.fetchone()
        conn.close()
        
        if not user or not check_password_hash(user[1], password):
            return jsonify({'status': 'error', 'error': 'Invalid email or password'}), 401
        
        session['user_id'] = user[0]
        session['email'] = email
        session['first_name'] = user[2]
        session['last_name'] = user[3]
        
        return jsonify({
            'status': 'success',
            'message': 'Login successful',
            'user_id': user[0],
            'redirect': '/dashboard'
        })
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

# API Routes
@app.route('/api/analyze_contract', methods=['POST'])
@require_login
def analyze_contract_endpoint():
    """Analyze contract PDF for risks using AI"""
    try:
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'status': 'error', 'error': 'No file selected'}), 400
        
        # Check file extension
        if not (file.filename.lower().endswith('.pdf')):
            return jsonify({
                'status': 'error',
                'error': 'Invalid file type. Please upload a PDF file.'
            }), 400
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['CONTRACT_UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # Analyze contract
            result = analyze_contract(filepath)
            
            # Clean up uploaded file
            try:
                os.remove(filepath)
            except:
                pass
            
            if 'error' in result:
                return jsonify({
                    'status': 'error',
                    'error': result['error']
                }), 500
            
            # Generate PDF report
            user_id = get_user_id()
            import json as json_lib
            pdf_filename = f"contract_report_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            pdf_path = os.path.join(app.config['REPORTS_FOLDER'], pdf_filename)
            
            # Ensure we have all 3 heatmaps
            heatmap_data = result.get('heatmap_data', [])
            print(f"DEBUG: Heatmaps in result: {len(heatmap_data)}")
            if len(heatmap_data) < 3:
                print(f"WARNING: Only {len(heatmap_data)} heatmaps found, expected 3. Available types: {[h.get('type') for h in heatmap_data]}")
            
            try:
                generate_contract_pdf(result, heatmap_data, pdf_path)
                print(f"DEBUG: PDF generated successfully with {len(heatmap_data)} heatmaps")
            except Exception as pdf_error:
                print(f"PDF generation error: {pdf_error}")
                import traceback
                traceback.print_exc()
                # Continue even if PDF generation fails
            
            # Store report in database
            try:
                conn = sqlite3.connect(app.config['DATABASE'])
                c = conn.cursor()
                report_title = f"Contract Analysis: {filename}"
                c.execute('''INSERT INTO reports (user_id, report_type, title, filename, pdf_path, report_data)
                             VALUES (?, ?, ?, ?, ?, ?)''',
                         (user_id, 'contract', report_title, filename, pdf_path, json_lib.dumps(result)))
                report_id = c.lastrowid
                conn.commit()
                conn.close()
                
                # Add report_id to response
                result['report_id'] = report_id
                result['pdf_path'] = pdf_path
            except Exception as db_error:
                print(f"Database error: {db_error}")
            
            return jsonify(result)
            
        except Exception as e:
            # Clean up file on error
            try:
                os.remove(filepath)
            except:
                pass
            return jsonify({
                'status': 'error',
                'error': f'Processing failed: {str(e)}'
            }), 500
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/api/process_meeting', methods=['POST'])
@require_login
def process_meeting():
    """Process meeting audio/video file or transcript"""
    try:
        # Check if file is uploaded
        if 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                return jsonify({'status': 'error', 'error': 'No file selected'}), 400
            
            if not allowed_file(file.filename):
                return jsonify({
                    'status': 'error',
                    'error': f'File type not allowed. Allowed types: {", ".join(app.config["ALLOWED_EXTENSIONS"])}'
                }), 400
            
            # Save uploaded file
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['MEETING_UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            try:
                # Process audio/video file with Gemini
                result = process_meeting_audio(filepath)
                
                # Clean up uploaded file
                try:
                    os.remove(filepath)
                except:
                    pass
                
                if 'error' in result:
                    return jsonify({
                        'status': 'error',
                        'error': result['error']
                    }), 500
                
                # Generate PDF report
                user_id = get_user_id()
                import json as json_lib
                pdf_filename = f"meeting_report_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                pdf_path = os.path.join(app.config['REPORTS_FOLDER'], pdf_filename)
                
                meeting_data = {
                    'summary': result.get('summary', ''),
                    'key_points': result.get('key_points', []),
                    'action_items': result.get('action_items', []),
                    'deadlines': result.get('deadlines', []),
                    'participants': result.get('participants', []),
                    'decisions': result.get('decisions', [])
                }
                
                try:
                    generate_meeting_pdf(meeting_data, pdf_path)
                except Exception as pdf_error:
                    print(f"PDF generation error: {pdf_error}")
                    # Continue even if PDF generation fails
                
                # Store report in database
                try:
                    conn = sqlite3.connect(app.config['DATABASE'])
                    c = conn.cursor()
                    report_title = f"Meeting: {filename}"
                    c.execute('''INSERT INTO reports (user_id, report_type, title, filename, pdf_path, report_data)
                                 VALUES (?, ?, ?, ?, ?, ?)''',
                             (user_id, 'meeting', report_title, filename, pdf_path, json_lib.dumps(meeting_data)))
                    report_id = c.lastrowid
                    conn.commit()
                    conn.close()
                except Exception as db_error:
                    print(f"Database error: {db_error}")
                
                return jsonify({
                    'status': 'success',
                    'summary': result.get('summary', ''),
                    'key_points': result.get('key_points', []),
                    'action_items': result.get('action_items', []),
                    'deadlines': result.get('deadlines', []),
                    'participants': result.get('participants', []),
                    'decisions': result.get('decisions', []),
                    'raw_response': result.get('raw_response', ''),
                    'report_id': report_id,
                    'pdf_path': pdf_path
                })
                
            except Exception as e:
                # Clean up file on error
                try:
                    os.remove(filepath)
                except:
                    pass
                return jsonify({
                    'status': 'error',
                    'error': f'Processing failed: {str(e)}'
                }), 500
        
        # If no file, check for transcript text
        elif request.is_json:
            data = request.json
            transcript = data.get('transcript', '')
            
            if not transcript or not transcript.strip():
                return jsonify({
                    'status': 'error',
                    'error': 'Please provide either a file or transcript text'
                }), 400
            
            # Process transcript with Gemini
            result = process_meeting_transcript(transcript)
            
            if 'error' in result:
                return jsonify({
                    'status': 'error',
                    'error': result['error']
                }), 500
            
            # Generate PDF report
            user_id = get_user_id()
            import json as json_lib
            pdf_filename = f"meeting_report_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            pdf_path = os.path.join(app.config['REPORTS_FOLDER'], pdf_filename)
            
            meeting_data = {
                'summary': result.get('summary', ''),
                'key_points': result.get('key_points', []),
                'action_items': result.get('action_items', []),
                'deadlines': result.get('deadlines', []),
                'participants': result.get('participants', []),
                'decisions': result.get('decisions', [])
            }
            
            try:
                generate_meeting_pdf(meeting_data, pdf_path)
            except Exception as pdf_error:
                print(f"PDF generation error: {pdf_error}")
                # Continue even if PDF generation fails
            
            # Store report in database
            try:
                conn = sqlite3.connect(app.config['DATABASE'])
                c = conn.cursor()
                report_title = "Meeting: Transcript"
                c.execute('''INSERT INTO reports (user_id, report_type, title, filename, pdf_path, report_data)
                             VALUES (?, ?, ?, ?, ?, ?)''',
                         (user_id, 'meeting', report_title, 'transcript.txt', pdf_path, json_lib.dumps(meeting_data)))
                report_id = c.lastrowid
                conn.commit()
                conn.close()
            except Exception as db_error:
                print(f"Database error: {db_error}")
            
            return jsonify({
                'status': 'success',
                'summary': result.get('summary', ''),
                'key_points': result.get('key_points', []),
                'action_items': result.get('action_items', []),
                'deadlines': result.get('deadlines', []),
                'participants': result.get('participants', []),
                'decisions': result.get('decisions', []),
                'raw_response': result.get('raw_response', ''),
                'report_id': report_id,
                'pdf_path': pdf_path
            })
        
        else:
            return jsonify({
                'status': 'error',
                'error': 'Please provide either a file or transcript text'
            }), 400
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/api/analyze_tone', methods=['POST'])
@require_login
def analyze_tone_endpoint():
    """Analyze the tone of input text"""
    try:
        data = request.json
        text = data.get('text', '')
        
        if not text or not text.strip():
            return jsonify({
                'status': 'error',
                'error': 'Please provide text to analyze'
            }), 400
        
        analysis = analyze_tone(text)
        return jsonify({
            'status': 'success',
            'tone': analysis.get('tone', 'unknown'),
            'confidence': analysis.get('score', 0),
            'all_scores': analysis.get('all_scores', {})
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/api/rewrite_text', methods=['POST'])
@require_login
def rewrite_text():
    """Rewrite text with specified tone using AI tone converter"""
    try:
        data = request.json
        original_text = data.get('text', '')
        tone = data.get('tone', 'professional')
        
        if not original_text or not original_text.strip():
            return jsonify({
                'status': 'error',
                'error': 'Please provide text to rewrite'
            }), 400
        
        # Analyze original tone
        tone_analysis = analyze_tone(original_text)
        
        # Convert to target tone
        rewritten_text = convert_tone(original_text, tone)
        
        # Store in database
        try:
            conn = sqlite3.connect(app.config['DATABASE'])
            c = conn.cursor()
            c.execute('''INSERT INTO rewrites (original_text, rewritten_text, tone, created_date)
                         VALUES (?, ?, ?, ?)''',
                     (original_text, rewritten_text, tone, datetime.now()))
            conn.commit()
            conn.close()
        except Exception as db_error:
            # Log but don't fail the request
            print(f"Database error: {db_error}")
        
        return jsonify({
            'status': 'success',
            'rewritten_text': rewritten_text,
            'original_tone': tone_analysis.get('tone', 'unknown'),
            'tone_confidence': tone_analysis.get('score', 0)
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)

