import spacy
from transformers import pipeline
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
from typing import List, Dict
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import openpyxl
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load spaCy model
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    import subprocess
    subprocess.run(["python", "-m", "spacy", "download", "en_core_web_sm"])
    nlp = spacy.load("en_core_web_sm")

# Load sentiment analysis model
sentiment_analyzer = pipeline("sentiment-analysis", model="finiteautomata/bertweet-base-sentiment-analysis")

# News source credibility scores (expanded database)
SOURCE_CREDIBILITY = {
    # Major News Organizations
    'reuters.com': 0.95,
    'bloomberg.com': 0.93,
    'wsj.com': 0.92,
    'ft.com': 0.91,
    'cnbc.com': 0.89,
    'bbc.com': 0.90,
    'theguardian.com': 0.88,
    'nytimes.com': 0.92,
    'washingtonpost.com': 0.91,
    'apnews.com': 0.94,
    
    # Business News
    'forbes.com': 0.87,
    'businessinsider.com': 0.85,
    'marketwatch.com': 0.86,
    'fortune.com': 0.87,
    
    # Technology News
    'techcrunch.com': 0.84,
    'wired.com': 0.86,
    'theverge.com': 0.83,
    
    # Industry-specific
    'zdnet.com': 0.82,
    'venturebeat.com': 0.81,
    'engadget.com': 0.80,
    
    # Default score for unknown sources
    'default': 0.70
}

def get_source_credibility(url: str) -> float:
    """Get credibility score for a news source using an enhanced scoring system."""
    try:
        # Extract domain from URL
        domain = url.split('/')[2].lower()
        
        # Check if domain is in our database
        if domain in SOURCE_CREDIBILITY:
            return SOURCE_CREDIBILITY[domain]
        
        # Check for subdomains of known sources
        for known_domain, score in SOURCE_CREDIBILITY.items():
            if known_domain in domain:
                return score
        
        # Additional checks for unknown sources
        if any(keyword in domain for keyword in ['news', 'press', 'media']):
            return 0.75  # Slightly higher score for news-focused domains
        
        return SOURCE_CREDIBILITY['default']
    except (IndexError, AttributeError) as e:
        print(f"Error processing URL {url}: {str(e)}")
        return SOURCE_CREDIBILITY['default']

def extract_entities(text: str) -> Dict[str, List[str]]:
    """Extract named entities from text using spaCy."""
    doc = nlp(text)
    entities = {
        'PERSON': [],
        'ORG': [],
        'GPE': [],  # Geo-Political Entities
        'PRODUCT': [],
        'MONEY': []
    }
    
    for ent in doc.ents:
        if ent.label_ in entities:
            entities[ent.label_].append(ent.text)
    
    return entities

def create_sentiment_timeline(articles: List[Dict]) -> go.Figure:
    """Create a timeline of sentiment scores."""
    try:
        dates = []
        sentiments = []
        
        for article in articles:
            try:
                date = datetime.strptime(article.get('date', ''), '%Y-%m-%d')
                sentiment = 1 if article['sentiment'] == 'Positive' else (-1 if article['sentiment'] == 'Negative' else 0)
                dates.append(date)
                sentiments.append(sentiment)
            except (ValueError, KeyError) as e:
                print(f"Error processing article date: {str(e)}")
                continue
        
        if not dates:
            raise ValueError("No valid dates found in articles")
        
        df = pd.DataFrame({'date': dates, 'sentiment': sentiments})
        df = df.sort_values('date')
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['date'], y=df['sentiment'],
                                mode='lines+markers',
                                name='Sentiment Trend'))
        
        fig.update_layout(title='Sentiment Trend Over Time',
                         xaxis_title='Date',
                         yaxis_title='Sentiment Score',
                         yaxis_range=[-1.2, 1.2])
        
        return fig
    except Exception as e:
        print(f"Error creating sentiment timeline: {str(e)}")
        # Return empty figure
        return go.Figure()

def export_report(articles: List[Dict], analysis: Dict, format: str = 'pdf') -> str:
    """Export the analysis report in the specified format."""
    if format == 'pdf':
        return export_pdf(articles, analysis)
    elif format == 'excel':
        return export_excel(articles, analysis)
    elif format == 'csv':
        return export_csv(articles, analysis)
    else:
        raise ValueError(f"Unsupported format: {format}")

def export_pdf(articles: List[Dict], analysis: Dict) -> str:
    """Export report as PDF."""
    filename = f"news_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []
    
    # Add title
    elements.append(Paragraph("News Analysis Report", styles['Title']))
    elements.append(Spacer(1, 12))
    
    # Add sentiment analysis
    elements.append(Paragraph("Sentiment Analysis", styles['Heading1']))
    sentiment_data = [[k, v] for k, v in analysis['sentiment_distribution'].items()]
    t = Table(sentiment_data)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    elements.append(t)
    elements.append(Spacer(1, 12))
    
    # Add articles
    elements.append(Paragraph("Articles", styles['Heading1']))
    for article in articles:
        elements.append(Paragraph(article['title'], styles['Heading2']))
        elements.append(Paragraph(f"Sentiment: {article['sentiment']}", styles['Normal']))
        elements.append(Paragraph(article['summary'], styles['Normal']))
        elements.append(Spacer(1, 12))
    
    doc.build(elements)
    return filename

def export_excel(articles: List[Dict], analysis: Dict) -> str:
    """Export report as Excel."""
    filename = f"news_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    wb = openpyxl.Workbook()
    
    # Add sentiment analysis
    ws = wb.active
    ws.title = "Sentiment Analysis"
    ws.append(["Sentiment", "Count"])
    for sentiment, count in analysis['sentiment_distribution'].items():
        ws.append([sentiment, count])
    
    # Add articles
    ws = wb.create_sheet("Articles")
    ws.append(["Title", "Sentiment", "Summary", "URL"])
    for article in articles:
        ws.append([
            article['title'],
            article['sentiment'],
            article['summary'],
            article['url']
        ])
    
    wb.save(filename)
    return filename

def export_csv(articles: List[Dict], analysis: Dict) -> str:
    """Export report as CSV."""
    filename = f"news_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    # Convert articles to DataFrame
    df = pd.DataFrame(articles)
    df.to_csv(filename, index=False)
    
    return filename

def filter_by_date_range(articles: List[Dict], start_date: datetime, end_date: datetime) -> List[Dict]:
    """Filter articles by date range."""
    filtered_articles = []
    for article in articles:
        try:
            article_date = datetime.strptime(article.get('date', ''), '%Y-%m-%d')
            # Convert start_date and end_date to datetime if they are date objects
            start = datetime.combine(start_date, datetime.min.time()) if isinstance(start_date, datetime.date) else start_date
            end = datetime.combine(end_date, datetime.max.time()) if isinstance(end_date, datetime.date) else end_date
            if start <= article_date <= end:
                filtered_articles.append(article)
        except (ValueError, TypeError) as e:
            logger.warning(f"Error processing article date: {str(e)}")
            continue
    return filtered_articles

def analyze_sentiment_distribution(articles: List[Dict]) -> Dict:
    """Analyze the distribution of sentiments in articles."""
    sentiment_counts = {
        'Positive': 0,
        'Negative': 0,
        'Neutral': 0
    }
    for article in articles:
        sentiment_counts[article['sentiment']] += 1
    return sentiment_counts 