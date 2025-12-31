# AI Productivity & Risk Assistant

A unified platform that helps professionals work faster, safer, and smarter by handling everyday document and communication challenges in one place. This application analyzes contracts to highlight hidden risks, processes meeting recordings to extract action items, and rewrites messages to maintain professional tone.

## 🎯 Problem Statement

In today's workplace, professionals spend hours:
- Reading contracts they don't fully understand
- Re-watching meetings to find action points
- Rewriting emails to sound professional

Small mistakes in any of these areas can lead to legal risk, missed deadlines, or workplace conflict. This platform addresses all three challenges in one unified solution.

## ✨ Key Features

### 1. **Contract Analyzer** 📄
- **PDF Contract Analysis**: Upload contract PDFs and get instant risk analysis
- **Risk Detection**: Identifies critical risks, standard terms, and potential issues
- **3D Heatmap Visualizations**: Three interactive heatmaps showing:
  - PCA-based risk distribution
  - Clause-by-clause risk analysis
  - Mesh visualization of risk patterns
- **PDF Reports**: Download comprehensive PDF reports with all heatmaps and risk descriptions
- **Risk Categories**: Categorizes risks by type (Critical, High, Medium, Low)

### 2. **Meeting Processor** 🎤
- **Audio/Video Processing**: Supports MP3, MP4, WAV, M4A, WebM, OGG, AVI, MOV formats
- **Intelligent Transcription**: Uses Google Gemini API for accurate transcription
- **Action Item Extraction**: Automatically identifies tasks with:
  - Task descriptions
  - Assigned owners
  - Deadlines
  - Priority levels
- **Meeting Summary**: Generates comprehensive summaries
- **Key Points & Decisions**: Extracts important discussion points and decisions
- **PDF Reports**: Download formatted meeting reports

### 3. **Tone Architect** ✍️
- **Tone Analysis**: Detects the emotional tone of your text
- **AI-Powered Rewriting**: Uses Google Gemini API to rewrite entire messages (not just prefixes)
- **Multiple Tone Options**:
  - **Professional**: Diplomatic, business-appropriate, formal
  - **Persuasive**: Engaging, compelling, action-oriented
  - **Empathetic**: Warm, understanding, supportive
  - **Executive**: Concise, direct, authoritative
  - **Viral**: Engaging, shareable, energetic
  - **Polite**: Courteous and respectful
  - **Formal**: Professional business language
  - **Friendly**: Conversational and approachable
- **Complete Text Transformation**: Rewrites the entire message to match the desired tone

## 🚀 Getting Started

### Prerequisites

- **Python 3.8 or higher**
- **pip** (Python package manager)
- **Google Gemini API Key** - Get it from [Google AI Studio](https://makersuite.google.com/app/apikey)

### Installation Steps

1. **Clone the repository**:
```bash
git clone https://github.com/CHAITU2405/AI-Productivity-Risk-Assistant.git
cd AI-Productivity-Risk-Assistant
```

2. **Create a virtual environment**:
```bash
python -m venv venv
```

3. **Activate the virtual environment**:

   On Windows:
   ```bash
   venv\Scripts\activate
   ```

   On macOS/Linux:
   ```bash
   source venv/bin/activate
   ```

4. **Install dependencies**:
```bash
pip install -r requirements.txt
```

5. **Set up environment variables**:
   - Create a `.env` file in the project root
   - Add your Gemini API key:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```
   - **Note**: If you don't set this, the app will use a default key (not recommended for production)

6. **Initialize the database** (automatic on first run):
   - The SQLite database will be created automatically when you first run the app

7. **Run the application**:
```bash
python app.py
```

8. **Access the application**:
   - Open your browser and navigate to: `http://localhost:5000`
   - Register a new account or login to get started

## 📁 Project Structure

```
AI-Productivity-Risk-Assistant/
├── app.py                      # Main Flask application
├── contract_analyzer.py        # Contract analysis logic
├── meeting_processor.py        # Meeting processing with Gemini API
├── tone_converter.py            # Tone analysis and conversion
├── report_generator.py         # PDF report generation
├── requirements.txt             # Python dependencies
├── README.md                   # This file
├── workguard.db                # SQLite database (auto-created)
├── templates/                  # HTML templates
│   ├── index.html             # Landing page
│   ├── login.html             # Login page
│   ├── register.html          # Registration page
│   ├── dashboard.html         # User dashboard
│   ├── contract.html          # Contract analyzer interface
│   ├── meetings.html          # Meeting processor interface
│   └── rewrite.html           # Tone converter interface
├── uploads/                    # Uploaded files (auto-created)
│   ├── contracts/             # Contract PDFs
│   └── meetings/             # Meeting audio/video files
├── reports/                    # Generated PDF reports (auto-created)
└── unwanted/                   # Unwanted/test files
```

## 🔐 User Authentication

The application includes a complete user authentication system:
- **User Registration**: Create an account with email and password
- **Secure Login**: Password hashing using Werkzeug
- **Session Management**: Secure session-based authentication
- **Protected Routes**: All features require login
- **User-Specific Data**: Each user's reports and data are isolated

## 📊 Dashboard Features

After logging in, users can:
- **View Recent Reports**: See all contract and meeting analyses
- **Download Reports**: Download PDF reports anytime
- **View Reports**: Click "View" to see full analysis results
- **Quick Access**: Navigate to Contract Analyzer, Meeting Processor, or Tone Architect
- **Statistics**: View usage statistics

## 🔌 API Endpoints

### Public Routes
- `GET /` - Landing page
- `GET /login` - Login page
- `GET /register` - Registration page

### Protected Routes (Require Login)
- `GET /dashboard` - User dashboard
- `GET /contract` - Contract analysis page
- `GET /meetings` - Meeting processor page
- `GET /rewrite` - Tone converter page
- `GET /settings` - Settings page

### API Endpoints
- `POST /api/register` - Register new user
- `POST /api/login` - User login
- `POST /api/analyze_contract` - Analyze contract PDF
- `POST /api/process_meeting` - Process meeting audio/video or transcript
- `POST /api/analyze_tone` - Analyze text tone
- `POST /api/rewrite_text` - Rewrite text with specified tone
- `GET /api/view_report/<id>` - View saved report data
- `GET /api/download_report/<id>` - Download PDF report

## 🛠️ Technology Stack

- **Backend**: Python Flask
- **Database**: SQLite
- **AI/ML**:
  - Google Gemini API (Meeting processing & Tone conversion)
  - Transformers (Tone analysis)
  - Sentence Transformers (Contract analysis)
- **PDF Processing**: pdfplumber, ReportLab
- **Visualization**: Plotly.js, Three.js
- **Frontend**: HTML, CSS, JavaScript, Bootstrap

## 📝 How It Works

### Contract Analysis Flow
1. User uploads a PDF contract
2. Text is extracted from the PDF
3. AI analyzes the contract for risks
4. Risk levels are calculated and categorized
5. Three 3D heatmaps are generated
6. PDF report is created with all analysis
7. Report is saved to user's dashboard

### Meeting Processing Flow
1. User uploads audio/video file or pastes transcript
2. File is uploaded to Gemini API (if audio/video)
3. Gemini transcribes and analyzes the meeting
4. Action items, deadlines, and key points are extracted
5. Structured data is returned
6. PDF report is generated
7. Report is saved to user's dashboard

### Tone Conversion Flow
1. User enters text and selects target tone
2. Original tone is analyzed
3. Text is sent to Gemini API with tone conversion prompt
4. Gemini rewrites the entire message
5. Converted text is returned
6. History is saved to database

## 🔒 Security Features

- Password hashing with Werkzeug
- Session-based authentication
- User data isolation
- Secure file uploads
- SQL injection protection (parameterized queries)

## 📦 Dependencies

Key Python packages:
- `Flask` - Web framework
- `google-generativeai` - Gemini API client
- `transformers` - NLP models
- `sentence-transformers` - Sentence embeddings
- `pdfplumber` - PDF text extraction
- `reportlab` - PDF generation
- `plotly` - Visualizations
- `kaleido` - Static image export
- `scikit-learn` - Machine learning utilities

See `requirements.txt` for complete list.

## 🐛 Troubleshooting

### Common Issues

1. **"Module not found" errors**:
   - Make sure virtual environment is activated
   - Run `pip install -r requirements.txt`

2. **Gemini API errors**:
   - Check your API key in `.env` file
   - Verify API quota at [Google AI Studio](https://ai.dev/usage)
   - Check internet connection

3. **Database errors**:
   - Delete `workguard.db` and restart the app (will recreate database)
   - Check file permissions

4. **Port already in use**:
   - Change port in `app.py`: `app.run(debug=True, port=5001)`

## 🚀 Deployment

For production deployment:
1. Set `debug=False` in `app.py`
2. Use a production WSGI server (e.g., Gunicorn)
3. Set up proper environment variables
4. Use a production database (PostgreSQL recommended)
5. Configure proper file storage (S3, etc.)
6. Set up SSL/HTTPS

## 📄 License

This project is open source and available for use.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📧 Support

For issues and questions, please open an issue on GitHub.

---

**Made with ❤️ to help professionals work smarter, not harder.**
