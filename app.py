import streamlit as st
from utils import get_news_articles
from advanced_analysis import get_source_credibility

import logging
import io
from gtts import gTTS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set page config
st.set_page_config(
    page_title="News Sentiment Analysis",
    page_icon="📰",
    layout="wide"
)

# Title and description
st.title("📰 News Sentiment Analysis")
st.markdown("""
This application analyzes news articles related to a company and provides sentiment analysis.
Enter a company name below to get started.
""")

# Sidebar for advanced options
st.sidebar.header("Advanced Options")

# Sidebar info section
st.sidebar.markdown(
    """
    ### ℹ️ About this app

    - Fetches the latest news articles for any company.
    - Analyzes and displays the sentiment (Positive, Negative, Neutral) for each article.
    - Shows a summary and a credibility score for each article.
    - Lets you listen to each summary using text-to-speech.
    - Lets you clear the app history and start fresh.

    ---
    """
)

# Number of articles to display
num_articles = st.sidebar.slider(
    "Number of Articles to Display",
    min_value=1,
    max_value=15,
    value=5,
    help="Choose how many articles you want to see (1-15)"
)

# Add Clear History button to sidebar
if st.sidebar.button("Clear History"):
    st.session_state.clear()
    st.experimental_rerun()

# Main content
company_name = st.text_input("Enter Company Name", placeholder="e.g., Apple, Microsoft, Tesla")

if company_name:
    with st.spinner("Fetching and analyzing news articles..."):
        try:
            # Get news articles with user-selected count (latest N)
            articles = get_news_articles(company_name, num_articles)
            
            if articles:
                # Show warning if fewer than requested articles are found
                if len(articles) < num_articles:
                    st.warning(f"Only {len(articles)} articles found for the given company name.")
                # Display individual articles
                st.subheader(f"Article Analysis (Showing {len(articles)} latest articles)")
                for i, article in enumerate(articles, 1):
                    with st.expander(f"{i}. {article['title']} ({article['source']})"):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            st.write("**Summary:**")
                            st.write(article['summary'])
                            st.markdown("**Play Summary Audio**")
                            tts = gTTS(text=article['summary'], lang='en')
                            audio_bytes = io.BytesIO()
                            tts.write_to_fp(audio_bytes)
                            audio_bytes.seek(0)
                            st.audio(audio_bytes, format='audio/mp3')
                        
                        with col2:
                            # Display source credibility
                            credibility = get_source_credibility(article['url'])
                            st.write(f"**Source Credibility:** {credibility:.2f}")
                            
                            sentiment_color = {
                                'Positive': 'green',
                                'Negative': 'red',
                                'Neutral': 'gray'
                            }[article['sentiment']]
                            
                            st.markdown(
                                f"<h3 style='color: {sentiment_color};'>{article['sentiment']}</h3>",
                                unsafe_allow_html=True
                            )
                            st.markdown(f"[Read Full Article]({article['url']})")
            else:
                st.error("No articles found for the given company name. Please try a different company.")
        except Exception as e:
            logger.error(f"Error in main application: {str(e)}")
            st.error("An error occurred while fetching articles. Please try again later.")
else:
    st.info("Please enter a company name to begin the analysis.") 