import os
import requests
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
import re

def extract_video_id(url: str) -> str:
    patterns = [
        r"v=([a-zA-Z0-9_-]{11})",
        r"youtu\.be/([a-zA-Z0-9_-]{11})",
        r"embed/([a-zA-Z0-9_-]{11})"
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError("Could not extract video ID. Check the URL.")

def get_transcript(url: str) -> tuple[str, str, list[dict]]:
    video_id = extract_video_id(url)
    try:
        session = requests.Session()
        # Set a real browser User-Agent to bypass generic scraping bans
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        })
        
        # Set proxy if available in environment
        proxy = os.getenv("YOUTUBE_PROXY")
        if proxy:
            session.proxies = {
                "http": proxy,
                "https": proxy
            }
            
        ytt = YouTubeTranscriptApi(http_client=session)
        fetched = ytt.fetch(video_id)
        full_text = " ".join([entry['text'] if isinstance(entry, dict) else entry.text for entry in fetched])
        return full_text, video_id, fetched
    except TranscriptsDisabled:
        raise ValueError("This video has transcripts disabled.")
    except NoTranscriptFound:
        raise ValueError("No transcript found for this video.")
    except Exception as e:
        raise ValueError(f"Could not fetch transcript: {str(e)}")

def chunk_transcript(text: str, chunk_size: int = 3000) -> list[str]:
    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0
    for word in words:
        current_chunk.append(word)
        current_length += len(word) + 1
        if current_length >= chunk_size:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
            current_length = 0
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    return chunks