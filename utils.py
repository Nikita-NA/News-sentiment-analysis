import requests
from bs4 import BeautifulSoup
from newspaper import Article
import pandas as pd
import nltk
from typing import List, Dict
import logging
from datetime import datetime
import time
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Download required NLTK data
nltk.download('punkt')

def get_news_articles(company_name: str, num_articles: int = 10, start_date: datetime = None, end_date: datetime = None) -> List[Dict]:
    """
    Fetch news articles related to the given company name from Bing News.
    Returns a list of dictionaries containing article information.
    """
    # Try to fetch up to 3x the requested number to account for failures
    articles = get_bing_news_articles(company_name, num_articles * 3, start_date, end_date)
    return articles[:num_articles]

def get_bing_news_articles(company_name: str, num_articles: int, start_date: datetime = None, end_date: datetime = None) -> List[Dict]:
    """Fetch articles from Bing News search results."""
    search_query = company_name.replace(' ', '+')
    
    # Add time range to the URL if provided
    time_range = ""
    if start_date and end_date:
        # Convert dates to Bing's format (e.g., "2024-01-01..2024-01-31")
        time_range = f"&qft=interval%3d%22{start_date.strftime('%Y-%m-%d')}..{end_date.strftime('%Y-%m-%d')}%22"
    
    url = f"https://www.bing.com/news/search?q={search_query}{time_range}&FORM=HDRSC6"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    articles = []
    max_retries = 3
    retry_delay = 2
    
    try:
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=headers, timeout=15)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Try different selectors for news cards
                news_cards = soup.find_all('a', {'class': 'title'})
                if not news_cards:
                    news_cards = soup.find_all('div', {'class': 'news-card'})
                if not news_cards:
                    news_cards = soup.find_all('div', {'class': 'news-item'})
                
                if not news_cards:
                    logger.warning("No news cards found in the response")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    return []
                
                for link in news_cards[:num_articles]:
                    try:
                        article_url = link.get('href')
                        if not article_url:
                            continue
                            
                        # Add random delay between requests
                        time.sleep(random.uniform(1, 3))
                        
                        article = Article(article_url)
                        article.download()
                        article.parse()
                        article.nlp()
                        
                        if article.title and article.text:
                            sentiment = get_sentiment(article.text)
                            # Ensure we have a valid date
                            article_date = article.publish_date if article.publish_date else datetime.now()
                            articles.append({
                                'title': article.title,
                                'summary': article.summary,
                                'text': article.text,
                                'url': article_url,
                                'sentiment': sentiment,
                                'topics': article.keywords[:5] if article.keywords else [],
                                'source': 'Bing News',
                                'date': article_date.strftime('%Y-%m-%d')
                            })
                            logger.info(f"Successfully processed article: {article.title}")
                    except Exception as e:
                        logger.warning(f"Error processing article {article_url}: {str(e)}")
                        continue
                
                if articles:
                    break
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error on attempt {attempt + 1}: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                    continue
                raise
                
        return articles
        
    except Exception as e:
        logger.error(f"Error fetching from Bing News: {str(e)}")
        return []

def get_sentiment(text: str) -> str:
    # Placeholder for sentiment analysis
    return 'Neutral'

def analyze_sentiment_distribution(articles: List[Dict]) -> Dict:
    sentiment_counts = {
        'Positive': 0,
        'Negative': 0,
        'Neutral': 0
    }
    for article in articles:
        sentiment_counts[article['sentiment']] += 1
    return sentiment_counts

def get_comparative_analysis(articles: List[Dict]) -> Dict:
    analysis = {
        'sentiment_distribution': analyze_sentiment_distribution(articles),
        'common_topics': get_common_topics(articles),
        'overall_sentiment': get_overall_sentiment(articles),
        'source_distribution': get_source_distribution(articles)
    }
    return analysis

def get_common_topics(articles: List[Dict]) -> List[str]:
    all_topics = []
    for article in articles:
        all_topics.extend(article['topics'])
    topic_freq = pd.Series(all_topics).value_counts()
    return topic_freq.head(5).index.tolist()

def get_overall_sentiment(articles: List[Dict]) -> str:
    sentiment_counts = analyze_sentiment_distribution(articles)
    max_sentiment = max(sentiment_counts.items(), key=lambda x: x[1])
    return max_sentiment[0]

def get_source_distribution(articles: List[Dict]) -> Dict:
    source_counts = {}
    for article in articles:
        source = article.get('source', 'Unknown')
        source_counts[source] = source_counts.get(source, 0) + 1
    return source_counts

def filter_by_date_range(articles: List[Dict], start_date: datetime, end_date: datetime) -> List[Dict]:
    """Filter articles by date range."""
    filtered_articles = []
    for article in articles:
        try:
            article_date = datetime.strptime(article.get('date', ''), '%Y-%m-%d')
            # Convert start_date and end_date to datetime if they are date objects
            start = datetime.combine(start_date, datetime.min.time()) if hasattr(start_date, 'date') else start_date
            end = datetime.combine(end_date, datetime.max.time()) if hasattr(end_date, 'date') else end_date
            if start <= article_date <= end:
                filtered_articles.append(article)
        except (ValueError, TypeError) as e:
            logger.warning(f"Error processing article date: {str(e)}")
            continue
    return filtered_articles 