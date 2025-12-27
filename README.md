# AI Productivity & Risk Assistant

A unified platform that helps professionals work faster, safer, and smarter by handling everyday document and communication challenges in one place.

## Features

- **Contract Analysis**: Analyzes contracts to highlight hidden risks in simple language
- **Meeting Processor**: Converts meeting notes or emails into clear action items with deadlines
- **Tone Architect**: Rewrites messages to maintain a polite and professional tone before they are sent

## Setup

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. Create a virtual environment:
```bash
python -m venv venv
```

2. Activate the virtual environment:

On Windows:
```bash
venv\Scripts\activate
```

On macOS/Linux:
```bash
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
python app.py
```

5. Open your browser and navigate to:
```
http://localhost:5000
```

## Project Structure

```
.
├── app.py                 # Flask application
├── requirements.txt       # Python dependencies
├── templates/             # HTML templates
│   ├── index.html
│   ├── contract.html
│   ├── meetings.html
│   ├── rewrite.html
│   └── settings.html
├── uploads/              # Uploaded files (created automatically)
└── workguard.db          # SQLite database (created automatically)
```

## API Endpoints

- `GET /` - Dashboard
- `GET /contract` - Contract analysis page
- `GET /meetings` - Meeting processor page
- `GET /rewrite` - Tone architect page
- `GET /settings` - Settings page
- `POST /api/analyze_contract` - Analyze contract document
- `POST /api/process_meeting` - Process meeting transcript
- `POST /api/rewrite_text` - Rewrite text with specified tone

## Database

The application uses SQLite for data storage. The database is automatically initialized when the application starts.

## Notes

- This is a basic implementation. AI processing logic will be enhanced in future updates.
- File uploads are stored in the `uploads/` directory.
- The database schema is created automatically on first run.

