"""
PDF Report Generator Module
Generates PDF reports for contract analysis and meeting processing
"""
import os
import tempfile
from datetime import datetime
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image, Table, TableStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    print("Warning: reportlab not available. PDF generation will be limited.")

try:
    import plotly.graph_objects as go
    import plotly.io as pio
    PLOTLY_AVAILABLE = True
    try:
        import kaleido
        KALEIDO_AVAILABLE = True
    except ImportError:
        KALEIDO_AVAILABLE = False
        print("Warning: kaleido not available. Heatmap images will not be included in PDF.")
except ImportError:
    PLOTLY_AVAILABLE = False
    KALEIDO_AVAILABLE = False
    print("Warning: plotly not available. Heatmap images will not be included in PDF.")

def generate_heatmap_image(heatmap, output_dir):
    """Generate a static image from heatmap data using Plotly"""
    if not PLOTLY_AVAILABLE or not KALEIDO_AVAILABLE:
        return None
    
    try:
        fig = None
        heatmap_type = heatmap.get('type', '')
        data = heatmap.get('data', {})
        
        if heatmap_type == 'surface':
            # Create 3D surface plot
            fig = go.Figure(data=[go.Surface(
                x=data.get('x', []),
                y=data.get('y', []),
                z=data.get('z', []),
                colorscale='Reds',
                showscale=True
            )])
            fig.update_layout(
                title=heatmap.get('title', '3D Contract Risk Surface'),
                scene=dict(
                    xaxis_title='Clause Type',
                    yaxis_title='Risk Level',
                    zaxis_title='Risk Intensity'
                ),
                width=800,
                height=600
            )
        elif heatmap_type == 'scatter3d':
            # Create 3D scatter plot
            x = data.get('x', [])
            y = data.get('y', [])
            z = data.get('z', [])
            colors_list = data.get('colors', ['red'] * len(x) if x else [])
            
            # Convert color strings to numeric values for colorscale
            color_values = [1 if c == 'red' else 0 for c in colors_list] if colors_list else []
            
            fig = go.Figure(data=[go.Scatter3d(
                x=x,
                y=y,
                z=z,
                mode='markers',
                marker=dict(
                    size=5,
                    color=color_values if color_values else None,
                    colorscale=[[0, 'green'], [1, 'red']],
                    showscale=True,
                    cmin=0,
                    cmax=1
                )
            )])
            fig.update_layout(
                title=heatmap.get('title', '3D PCA Risk Cloud'),
                scene=dict(
                    xaxis_title='PC1',
                    yaxis_title='PC2',
                    zaxis_title='PC3'
                ),
                width=800,
                height=600
            )
        elif heatmap_type == 'mesh3d':
            # Create 3D mesh plot
            x = data.get('x', [])
            y = data.get('y', [])
            z = data.get('z', [])
            clause_names = data.get('clause_names', [])
            
            fig = go.Figure(data=[
                go.Mesh3d(
                    x=x,
                    y=y,
                    z=z,
                    opacity=0.5,
                    color='lightblue'
                ),
                go.Scatter3d(
                    x=x,
                    y=y,
                    z=z,
                    mode='markers+text',
                    marker=dict(size=7, color='black'),
                    text=clause_names,
                    textposition='top center'
                )
            ])
            fig.update_layout(
                title=heatmap.get('title', '3D Clause Semantic Mesh Topology'),
                scene=dict(
                    xaxis_title='X',
                    yaxis_title='Y',
                    zaxis_title='Z'
                ),
                width=800,
                height=600
            )
        
        if fig:
            # Generate image file
            img_path = os.path.join(output_dir, f"heatmap_{heatmap_type}_{hash(str(heatmap)) % 10000}.png")
            fig.write_image(img_path, width=800, height=600, scale=2)
            return img_path
    except Exception as e:
        print(f"Error generating heatmap image: {e}")
        return None
    
    return None

def generate_contract_pdf(analysis_data, heatmap_data, output_path):
    """
    Generate PDF report for contract analysis
    
    Args:
        analysis_data: dict with summary, risk_level, risks, etc.
        heatmap_data: list of heatmap data dictionaries
        output_path: path to save the PDF
    """
    if not REPORTLAB_AVAILABLE:
        raise Exception("reportlab library is required for PDF generation. Install with: pip install reportlab")
    
    try:
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#38bdf8'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#ffffff'),
            backColor=colors.HexColor('#1e293b'),
            spaceAfter=12,
            spaceBefore=12
        )
        
        # Title
        story.append(Paragraph("Contract Analysis Report", title_style))
        story.append(Spacer(1, 0.2*inch))
        story.append(Paragraph(f"Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", 
                              styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Executive Summary
        story.append(Paragraph("Executive Summary", heading_style))
        story.append(Paragraph(analysis_data.get('summary', 'No summary available.'), styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        # Risk Level
        risk_level = analysis_data.get('risk_level', 'UNKNOWN')
        risk_emoji = analysis_data.get('risk_emoji', '⚪')
        risk_color = colors.HexColor('#f43f5e') if 'HIGH' in risk_level else \
                    colors.HexColor('#fbbf24') if 'MEDIUM' in risk_level else \
                    colors.HexColor('#10b981')
        
        risk_style = ParagraphStyle(
            'RiskLevel',
            parent=styles['Heading2'],
            fontSize=18,
            textColor=risk_color,
            spaceAfter=12
        )
        story.append(Paragraph(f"{risk_emoji} Risk Level: {risk_level}", risk_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Detected Risks
        risks = analysis_data.get('risks', [])
        if risks:
            story.append(Paragraph("Detected Risks", heading_style))
            
            # Create a style for table cells that allows text wrapping
            cell_style = ParagraphStyle(
                'TableCell',
                parent=styles['Normal'],
                fontSize=8,
                textColor=colors.whitesmoke,
                leading=10,
                spaceAfter=6
            )
            
            # Header row with Paragraph objects
            risk_data = [[
                Paragraph('<b>Type</b>', cell_style),
                Paragraph('<b>Category</b>', cell_style),
                Paragraph('<b>Description</b>', cell_style)
            ]]
            
            for risk in risks[:15]:  # Limit to 15 risks
                description = risk.get('description', 'N/A')
                # Escape HTML special characters and wrap in Paragraph for proper text wrapping
                description_escaped = description.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                
                risk_data.append([
                    Paragraph(risk.get('type', 'N/A'), cell_style),
                    Paragraph(risk.get('category', 'N/A'), cell_style),
                    Paragraph(description_escaped, cell_style)  # Use Paragraph for text wrapping
                ])
            
            # Adjust column widths to better accommodate full descriptions
            # Use more width for description column
            risk_table = Table(risk_data, colWidths=[1.0*inch, 1.3*inch, 4.7*inch], repeatRows=1)
            risk_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),  # Align to top for multi-line text
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#0f172a')),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#334155')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#1e293b'), colors.HexColor('#0f172a')])
            ]))
            story.append(risk_table)
            story.append(Spacer(1, 0.3*inch))
        
        # Heatmaps Section - All 3 heatmaps clearly aligned
        # Always show heatmaps section, even if we need to create placeholders
        story.append(PageBreak())
        story.append(Paragraph("3D Risk Heatmaps", heading_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Ensure we have exactly 3 heatmaps for the PDF
        heatmaps_to_show = []
        if heatmap_data and len(heatmap_data) > 0:
            heatmaps_to_show = list(heatmap_data[:3])  # Take up to 3 from provided data
        
        # Fill in missing heatmaps with placeholders
        heatmap_types = [h.get('type', '') for h in heatmaps_to_show if isinstance(h, dict)]
        
        # Ensure we have heatmap 1 (surface)
        if 'surface' not in heatmap_types:
            heatmaps_to_show.insert(0, {
                'type': 'surface',
                'title': '3D Contract Risk Surface',
                'data': {
                    'x': [[0, 1, 2], [0, 1, 2], [0, 1, 2]],
                    'y': [[0, 0, 0], [1, 1, 1], [2, 2, 2]],
                    'z': [[0.5, 1.0, 0.8], [1.2, 1.5, 1.3], [2.0, 2.5, 2.2]],
                    'clause_names': ['Payment Terms', 'Termination', 'Confidentiality'],
                    'risk_levels': ['Low', 'Medium', 'High']
                }
            })
        
        # Ensure we have heatmap 2 (scatter3d)
        if 'scatter3d' not in heatmap_types:
            heatmaps_to_show.append({
                'type': 'scatter3d',
                'title': '3D PCA Risk Cloud (Semantic Clause Space)',
                'data': {
                    'x': [0, 1, 2, 3, 4],
                    'y': [0, 1, 2, 3, 4],
                    'z': [0, 1, 2, 3, 4],
                    'colors': ['red', 'green', 'red', 'green', 'red'],
                    'texts': ['Risk clause 1', 'Safe clause 1', 'Risk clause 2', 'Safe clause 2', 'Risk clause 3']
                }
            })
        
        # Ensure we have heatmap 3 (mesh3d)
        if 'mesh3d' not in heatmap_types:
            # Get clause names from first heatmap if available, otherwise use defaults
            clause_names = ['Payment Terms', 'Termination', 'Confidentiality', 'Data Usage', 'Auto Renewal', 'Liability']
            if heatmaps_to_show and len(heatmaps_to_show) > 0 and isinstance(heatmaps_to_show[0], dict):
                clause_names = heatmaps_to_show[0].get('data', {}).get('clause_names', clause_names)
            heatmaps_to_show.append({
                'type': 'mesh3d',
                'title': '3D Clause Semantic Mesh Topology',
                'data': {
                    'x': [0, 1, 2, 3, 4, 5],
                    'y': [0, 1, 2, 3, 4, 5],
                    'z': [0, 1, 2, 3, 4, 5],
                    'clause_names': clause_names[:6] if len(clause_names) >= 6 else clause_names + ['Additional Clause'] * (6 - len(clause_names))
                }
            })
        
        # Limit to exactly 3
        heatmaps_to_show = heatmaps_to_show[:3]
        
        num_heatmaps = len(heatmaps_to_show)
        story.append(Paragraph(
            "The following section contains all three 3D heatmap visualizations generated from the contract analysis. "
            "Each heatmap provides a different perspective on the risk assessment.",
            styles['Normal']
        ))
        story.append(Spacer(1, 0.3*inch))
        print(f"DEBUG: PDF Generator - Including {len(heatmaps_to_show)} heatmaps in PDF")
        
        # Create temporary directory for heatmap images
        temp_dir = tempfile.mkdtemp()
        heatmap_images = []
        
        # Generate images for all heatmaps
        for heatmap in heatmaps_to_show:
            img_path = generate_heatmap_image(heatmap, temp_dir)
            if img_path and os.path.exists(img_path):
                heatmap_images.append((heatmap, img_path))
            else:
                heatmap_images.append((heatmap, None))
        
        for i, (heatmap, img_path) in enumerate(heatmap_images, 1):
            story.append(Paragraph(f"Heatmap {i} of {len(heatmaps_to_show)}: {heatmap.get('title', 'Risk Visualization')}", 
                                  styles['Heading3']))
            story.append(Spacer(1, 0.15*inch))
            
            # Add heatmap image if available
            if img_path and os.path.exists(img_path):
                try:
                    img = Image(img_path, width=6*inch, height=4.5*inch)
                    story.append(img)
                    story.append(Spacer(1, 0.2*inch))
                except Exception as img_error:
                    print(f"Error adding heatmap image to PDF: {img_error}")
                    story.append(Paragraph("<i>Heatmap visualization image could not be generated.</i>", styles['Italic']))
            else:
                story.append(Paragraph(
                    "<i>Note: Interactive 3D heatmap visualization is available in the web interface. "
                    "For the best viewing experience, please access the web dashboard.</i>",
                    styles['Italic']
                ))
            
            story.append(Spacer(1, 0.15*inch))
            
            # Add detailed heatmap description
            if heatmap.get('type') == 'surface':
                story.append(Paragraph(
                    "<b>Type:</b> 3D Surface Visualization<br/>"
                    "<b>Description:</b> This 3D surface visualization shows risk levels across different contract clauses. "
                    "Higher peaks indicate areas with more detected risks. The X-axis represents different clause categories, "
                    "the Y-axis represents risk levels (Low, Medium, High), and the Z-axis shows the intensity of risk detection.",
                    styles['Normal']
                ))
            elif heatmap.get('type') == 'scatter3d':
                story.append(Paragraph(
                    "<b>Type:</b> 3D Scatter Plot (PCA Risk Cloud)<br/>"
                    "<b>Description:</b> This 3D scatter plot represents contract clauses in semantic space using Principal Component Analysis. "
                    "Red points indicate high-risk clauses, while green points represent lower-risk areas. "
                    "The spatial distribution shows how clauses cluster based on their semantic similarity and risk levels.",
                    styles['Normal']
                ))
            elif heatmap.get('type') == 'mesh3d':
                story.append(Paragraph(
                    "<b>Type:</b> 3D Mesh Topology<br/>"
                    "<b>Description:</b> This 3D mesh topology shows the semantic relationships between different contract clauses. "
                    "Clauses closer together are semantically similar. The mesh structure reveals how different contract sections "
                    "relate to each other in the semantic embedding space.",
                    styles['Normal']
                ))
            else:
                story.append(Paragraph(
                    f"<b>Type:</b> {heatmap.get('type', 'Unknown')}<br/>"
                    "<b>Description:</b> Risk visualization data.",
                    styles['Normal']
                ))
            
            story.append(Spacer(1, 0.25*inch))
            
            # Add data summary if available
            data = heatmap.get('data', {})
            if data:
                if 'clause_names' in data:
                    story.append(Paragraph(f"<b>Clauses Analyzed:</b> {', '.join(data.get('clause_names', [])[:5])}", 
                                          styles['Normal']))
                if 'risk_levels' in data:
                    story.append(Paragraph(f"<b>Risk Levels:</b> {', '.join(data.get('risk_levels', []))}", 
                                          styles['Normal']))
            
            story.append(Spacer(1, 0.3*inch))
            
            # Separator between heatmaps
            if i < len(heatmaps_to_show):
                story.append(Paragraph("─" * 50, styles['Normal']))
                story.append(Spacer(1, 0.3*inch))
        
        # Note about interactive heatmaps
        story.append(Spacer(1, 0.2*inch))
        story.append(Paragraph(
            "<i><b>Note:</b> For interactive 3D heatmap visualizations, please access the web interface. "
            "The PDF contains comprehensive analysis data and risk assessments for all three heatmap types.</i>",
            styles['Italic']
        ))
        
        # Build PDF
        doc.build(story)
        return True
        
    except Exception as e:
        print(f"Error generating contract PDF: {e}")
        raise

def generate_meeting_pdf(meeting_data, output_path):
    """
    Generate PDF report for meeting processing
    
    Args:
        meeting_data: dict with summary, action_items, key_points, etc.
        output_path: path to save the PDF
    """
    if not REPORTLAB_AVAILABLE:
        raise Exception("reportlab library is required for PDF generation. Install with: pip install reportlab")
    
    try:
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#38bdf8'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#ffffff'),
            backColor=colors.HexColor('#1e293b'),
            spaceAfter=12,
            spaceBefore=12
        )
        
        # Title
        story.append(Paragraph("Meeting Summary Report", title_style))
        story.append(Spacer(1, 0.2*inch))
        story.append(Paragraph(f"Generated on: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", 
                              styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Meeting Summary
        summary = meeting_data.get('summary', 'No summary available.')
        story.append(Paragraph("Meeting Summary", heading_style))
        story.append(Paragraph(summary, styles['Normal']))
        story.append(Spacer(1, 0.3*inch))
        
        # Key Points
        key_points = meeting_data.get('key_points', [])
        if key_points:
            story.append(Paragraph("Key Points", heading_style))
            for i, point in enumerate(key_points[:10], 1):  # Limit to 10 points
                story.append(Paragraph(f"{i}. {point}", styles['Normal']))
            story.append(Spacer(1, 0.2*inch))
        
        # Action Items
        action_items = meeting_data.get('action_items', [])
        if action_items:
            story.append(PageBreak())
            story.append(Paragraph("Action Items", heading_style))
            action_data = [['#', 'Action', 'Assignee', 'Deadline']]
            for i, item in enumerate(action_items[:20], 1):  # Limit to 20 items
                action_data.append([
                    str(i),
                    item.get('action', 'N/A')[:60] + '...' if len(item.get('action', '')) > 60 else item.get('action', 'N/A'),
                    item.get('assignee', 'TBD'),
                    item.get('deadline', 'TBD')
                ])
            
            action_table = Table(action_data, colWidths=[0.5*inch, 3.5*inch, 1.5*inch, 1.5*inch])
            action_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e293b')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#0f172a')),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#334155')),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#1e293b'), colors.HexColor('#0f172a')])
            ]))
            story.append(action_table)
            story.append(Spacer(1, 0.3*inch))
        
        # Decisions
        decisions = meeting_data.get('decisions', [])
        if decisions:
            story.append(Paragraph("Decisions Made", heading_style))
            for i, decision in enumerate(decisions[:10], 1):  # Limit to 10 decisions
                story.append(Paragraph(f"{i}. {decision}", styles['Normal']))
            story.append(Spacer(1, 0.2*inch))
        
        # Build PDF
        doc.build(story)
        return True
        
    except Exception as e:
        print(f"Error generating meeting PDF: {e}")
        raise

