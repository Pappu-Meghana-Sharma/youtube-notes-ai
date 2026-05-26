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
        
        # 1. Try loading cookies from environment variable YOUTUBE_COOKIES (JSON format)
        import json
        cookies_env = os.getenv("YOUTUBE_COOKIES")
        if cookies_env:
            try:
                cookies_data = json.loads(cookies_env)
                if isinstance(cookies_data, list):
                    for cookie in cookies_data:
                        session.cookies.set(cookie.get('name'), cookie.get('value'))
                elif isinstance(cookies_data, dict):
                    for name, value in cookies_data.items():
                        session.cookies.set(name, value)
            except Exception:
                pass
        else:
            # 2. Try loading cookies from local Netscape cookies file if present
            import http.cookiejar
            for cookies_file in ["cookies.txt", "youtube_cookies.txt"]:
                if os.path.exists(cookies_file):
                    try:
                        cj = http.cookiejar.MozillaCookieJar(cookies_file)
                        cj.load(ignore_discard=True, ignore_expires=True)
                        session.cookies.update(cj)
                        break
                    except Exception:
                        pass
        
        # 3. Set proxy if available in environment
        proxy = os.getenv("YOUTUBE_PROXY")
        if proxy:
            session.proxies = {
                "http": proxy,
                "https": proxy
            }
            
        ytt = YouTubeTranscriptApi(http_client=session)
        fetched = ytt.fetch(video_id)
        full_text = " ".join([entry.text if hasattr(entry, 'text') else entry['text'] for entry in fetched])
        return full_text, video_id, fetched
    except TranscriptsDisabled:
        raise ValueError("This video has transcripts disabled.")
    except NoTranscriptFound:
        raise ValueError("No transcript found for this video.")
    except Exception as e:
        err_msg = str(e)
        if "blocking" in err_msg.lower() or "block" in err_msg.lower() or "cookies" in err_msg.lower() or "proxy" in err_msg.lower() or "retrieve a transcript" in err_msg.lower():
            raise ValueError(
                "YouTube is blocking requests from this IP (especially common on cloud deployments like Streamlit Cloud).\n\n"
                "To resolve this, please either:\n"
                "1. Export your YouTube cookies as a JSON string and set the `YOUTUBE_COOKIES` environment variable (or Streamlit Secret).\n"
                "2. Place a `cookies.txt` file in the root of the project containing your exported YouTube cookies.\n"
                "3. Set up a proxy using the `YOUTUBE_PROXY` environment variable."
            )
        raise ValueError(f"Could not fetch transcript: {err_msg}")

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