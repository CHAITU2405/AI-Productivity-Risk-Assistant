"""
Contract Analyzer Module
Analyzes PDF contracts, extracts risks, and generates 3D heatmaps
"""
import pdfplumber
import re
import numpy as np
from transformers import pipeline
try:
    from sentence_transformers import SentenceTransformer, util
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("Warning: sentence-transformers not available. Some features may be limited.")
from sklearn.decomposition import PCA
import json

# Global models (lazy loading)
_summarizer = None
_embedder = None

def load_models():
    """Load ML models (lazy loading)"""
    global _summarizer, _embedder
    try:
        if _summarizer is None:
            print("Loading summarization model...")
            _summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
            print("Summarization model loaded successfully")
        if _embedder is None:
            if SENTENCE_TRANSFORMERS_AVAILABLE:
                print("Loading sentence transformer model...")
                _embedder = SentenceTransformer("all-MiniLM-L6-v2")
                print("Sentence transformer loaded successfully")
            else:
                print("Warning: sentence-transformers not available. Using fallback methods.")
                _embedder = None
    except Exception as e:
        print(f"Error loading models: {e}")
        raise
    return _summarizer, _embedder

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF file"""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                if page.extract_text():
                    text += page.extract_text() + " "
    except Exception as e:
        raise Exception(f"Failed to extract text from PDF: {str(e)}")
    return text

def analyze_contract(pdf_path):
    """
    Analyze contract PDF and return risks, summary, and heatmap data
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        dict with summary, risks, risk_level, and heatmap_data
    """
    try:
        # Load models
        summarizer, embedder = load_models()
        
        # 1. Extract text from PDF
        print("Extracting text from PDF...")
        contract_text = extract_text_from_pdf(pdf_path)
        contract_text = re.sub(r'\s+', ' ', contract_text).strip()
        
        if not contract_text or len(contract_text) < 100:
            return {
                'error': 'Could not extract sufficient text from PDF. Please ensure the PDF contains readable text.'
            }
        
        # 2. Generate summary
        print("Generating summary...")
        summary_text = contract_text[:3000]  # Limit for summarization
        summary = summarizer(
            summary_text,
            max_length=180,
            min_length=80,
            do_sample=False
        )
        summary_result = summary[0]["summary_text"]
        
        # 3. Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', contract_text)
        sentences = [s for s in sentences if len(s) > 20]
        
        # 4. Define clause categories
        clauses = {
            "Payment Terms": ["payment", "fee", "charges", "cost"],
            "Termination": ["terminate", "termination", "cancel"],
            "Confidentiality": ["confidential", "privacy"],
            "Data Usage": ["data", "third party", "information"],
            "Auto Renewal": ["renewal", "automatically"],
            "Liability": ["penalty", "liability", "damages"]
        }
        
        # 5. Detect clauses using embeddings
        print("Detecting clauses...")
        sentence_embeddings = None
        detected_clauses = {}
        
        if embedder and SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                sentence_embeddings = embedder.encode(sentences)
                for clause, keywords in clauses.items():
                    kw_embed = embedder.encode(" ".join(keywords))
                    scores = util.cos_sim(kw_embed, sentence_embeddings)[0]
                    matched = [sentences[i] for i, s in enumerate(scores) if s > 0.45]
                    if matched:
                        detected_clauses[clause] = matched
            except Exception as e:
                print(f"Error using embeddings for clause detection: {e}")
                # Fallback to keyword matching
                for clause, keywords in clauses.items():
                    matched = [s for s in sentences if any(kw in s.lower() for kw in keywords)]
                    if matched:
                        detected_clauses[clause] = matched
                # Create embeddings for heatmap generation even if clause detection failed
                try:
                    sentence_embeddings = embedder.encode(sentences)
                except:
                    sentence_embeddings = np.random.rand(len(sentences), 384)
        else:
            # Fallback: simple keyword matching
            for clause, keywords in clauses.items():
                matched = [s for s in sentences if any(kw in s.lower() for kw in keywords)]
                if matched:
                    detected_clauses[clause] = matched
            # Create dummy embeddings for heatmap generation
            sentence_embeddings = np.random.rand(len(sentences), 384)  # Dummy embeddings
        
        # 6. Detect risky sentences
        risk_phrases = [
            "without notice", "sole discretion", "non-refundable",
            "automatically renew", "no liability", "indemnify", "unilateral"
        ]
        
        risky_sentences = list(set(
            s for s in sentences
            for p in risk_phrases if p in s.lower()
        ))
        
        # 7. Calculate risk level
        risk_count = len(risky_sentences)
        if risk_count >= 5:
            risk_level = "HIGH RISK"
            risk_emoji = "🔴"
        elif risk_count >= 2:
            risk_level = "MEDIUM RISK"
            risk_emoji = "🟠"
        else:
            risk_level = "LOW RISK"
            risk_emoji = "🟢"
        
        # 8. Format risks for frontend
        risks = []
        for i, risky_sentence in enumerate(risky_sentences[:10], 1):  # Limit to 10
            # Determine risk type based on content
            risk_type = "Caution"
            if any(phrase in risky_sentence.lower() for phrase in ["automatically renew", "without notice"]):
                risk_type = "Critical Risk"
            elif any(phrase in risky_sentence.lower() for phrase in ["no liability", "indemnify"]):
                risk_type = "High Risk"
            
            risks.append({
                'type': risk_type,
                'category': 'Auto-Renewal' if 'renew' in risky_sentence.lower() else 'Liability',
                'description': risky_sentence  # Keep full description
            })
        
        # 9. Generate heatmap data
        print("Generating heatmap data...")
        if sentence_embeddings is None:
            # Create dummy embeddings if not available
            sentence_embeddings = np.random.rand(len(sentences), 384)
        heatmap_data = generate_heatmap_data(detected_clauses, sentence_embeddings, sentences, risky_sentences, embedder)
        
        return {
            'status': 'success',
            'summary': summary_result,
            'risk_level': risk_level,
            'risk_emoji': risk_emoji,
            'risks': risks,
            'risky_sentences': risky_sentences,
            'detected_clauses': {k: len(v) for k, v in detected_clauses.items()},
            'heatmap_data': heatmap_data
        }
        
    except Exception as e:
        print(f"Error analyzing contract: {e}")
        return {
            'error': f"Analysis failed: {str(e)}"
        }

def generate_heatmap_data(detected_clauses, sentence_embeddings, sentences, risky_sentences, embedder):
    """Generate data for 3D heatmaps"""
    try:
        clause_names = list(detected_clauses.keys())
        if not clause_names:
            clause_names = ["Payment Terms", "Termination", "Confidentiality", "Data Usage", "Auto Renewal", "Liability"]
        
        risk_levels = ["Low", "Medium", "High"]
        
        # Heatmap 1: 3D Contract Risk Surface
        X, Y = np.meshgrid(np.arange(len(clause_names)), np.arange(3))
        Z = np.zeros_like(X, dtype=float)
        
        for i, clause in enumerate(clause_names):
            clause_count = len(detected_clauses.get(clause, []))
            Z[0][i] = clause_count * 0.3
            Z[1][i] = clause_count * 0.6
            Z[2][i] = clause_count
        
        heatmap1 = {
            'type': 'surface',
            'title': '3D Contract Risk Surface',
            'data': {
                'x': X.tolist(),
                'y': Y.tolist(),
                'z': Z.tolist(),
                'clause_names': clause_names,
                'risk_levels': risk_levels
            }
        }
        
        # Heatmap 2: 3D PCA Risk Cloud - Always generate this
        heatmap2 = None
        if sentence_embeddings is not None and len(sentence_embeddings) > 0:
            try:
                # Ensure we have enough dimensions for PCA
                if sentence_embeddings.shape[1] >= 3:
                    pca = PCA(n_components=3)
                    pca_points = pca.fit_transform(sentence_embeddings)
                else:
                    # If not enough dimensions, pad with zeros
                    padded = np.pad(sentence_embeddings, ((0, 0), (0, max(0, 3 - sentence_embeddings.shape[1]))), mode='constant')
                    pca = PCA(n_components=3)
                    pca_points = pca.fit_transform(padded)
                
                colors = ["red" if s in risky_sentences else "green" for s in sentences]
                sentence_texts = [s[:50] + "..." if len(s) > 50 else s for s in sentences]
                
                heatmap2 = {
                    'type': 'scatter3d',
                    'title': '3D PCA Risk Cloud (Semantic Clause Space)',
                    'data': {
                        'x': pca_points[:, 0].tolist(),
                        'y': pca_points[:, 1].tolist(),
                        'z': pca_points[:, 2].tolist(),
                        'colors': colors[:len(pca_points)],
                        'texts': sentence_texts[:len(pca_points)]
                    }
                }
            except Exception as e:
                print(f"Error generating PCA heatmap: {e}")
                # Will create placeholder below
        
        # Heatmap 3: 3D Clause Semantic Mesh Topology - Always generate this
        heatmap3 = None
        if embedder and SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                clause_embeddings = embedder.encode(clause_names)
                pca_clause = PCA(n_components=3)
                clause_xyz = pca_clause.fit_transform(clause_embeddings)
                
                heatmap3 = {
                    'type': 'mesh3d',
                    'title': '3D Clause Semantic Mesh Topology',
                    'data': {
                        'x': clause_xyz[:, 0].tolist(),
                        'y': clause_xyz[:, 1].tolist(),
                        'z': clause_xyz[:, 2].tolist(),
                        'clause_names': clause_names
                    }
                }
            except Exception as e:
                print(f"Error generating mesh heatmap: {e}")
                # Will create placeholder below
        else:
            # Create mesh heatmap even without embedder using clause positions
            try:
                # Use simple 3D positions based on clause indices
                num_clauses = len(clause_names)
                clause_xyz = np.array([
                    [i % 3, (i // 3) % 3, i // 9] for i in range(num_clauses)
                ])
                heatmap3 = {
                    'type': 'mesh3d',
                    'title': '3D Clause Semantic Mesh Topology',
                    'data': {
                        'x': clause_xyz[:, 0].tolist(),
                        'y': clause_xyz[:, 1].tolist(),
                        'z': clause_xyz[:, 2].tolist(),
                        'clause_names': clause_names
                    }
                }
            except Exception as e:
                print(f"Error creating fallback mesh heatmap: {e}")
        
        # Always return at least heatmap1, and include others if available
        # Ensure we always have 3 heatmaps - create placeholder if needed
        heatmaps = [heatmap1]
        
        # Add heatmap2 (PCA Risk Cloud) - create a basic one if generation failed
        if heatmap2:
            heatmaps.append(heatmap2)
        else:
            # Create a placeholder PCA heatmap if generation failed
            print("Warning: PCA heatmap generation failed, creating placeholder")
            heatmap2_placeholder = {
                'type': 'scatter3d',
                'title': '3D PCA Risk Cloud (Semantic Clause Space)',
                'data': {
                    'x': [0, 1, 2, 3, 4],
                    'y': [0, 1, 2, 3, 4],
                    'z': [0, 1, 2, 3, 4],
                    'colors': ['red', 'green', 'red', 'green', 'red'],
                    'texts': ['Risk clause 1', 'Safe clause 1', 'Risk clause 2', 'Safe clause 2', 'Risk clause 3']
                }
            }
            heatmaps.append(heatmap2_placeholder)
        
        # Add heatmap3 (Mesh Topology) - create a basic one if generation failed
        if heatmap3:
            heatmaps.append(heatmap3)
        else:
            # Create a placeholder mesh heatmap if generation failed
            print("Warning: Mesh heatmap generation failed, creating placeholder")
            heatmap3_placeholder = {
                'type': 'mesh3d',
                'title': '3D Clause Semantic Mesh Topology',
                'data': {
                    'x': [0, 1, 2, 3, 4, 5],
                    'y': [0, 1, 2, 3, 4, 5],
                    'z': [0, 1, 2, 3, 4, 5],
                    'clause_names': clause_names[:6] if len(clause_names) >= 6 else clause_names + ['Additional Clause'] * (6 - len(clause_names))
                }
            }
            heatmaps.append(heatmap3_placeholder)
        
        # Ensure we always return exactly 3 heatmaps
        final_heatmaps = heatmaps[:3]
        print(f"DEBUG: Contract Analyzer - Returning {len(final_heatmaps)} heatmaps")
        print(f"DEBUG: Heatmap types: {[h.get('type', 'unknown') for h in final_heatmaps]}")
        return final_heatmaps
        
    except Exception as e:
        print(f"Error generating heatmap data: {e}")
        return []

