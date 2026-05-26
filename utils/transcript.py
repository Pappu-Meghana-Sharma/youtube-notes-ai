import os
import re
import requests
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import WebshareProxyConfig
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
from dotenv import load_dotenv

load_dotenv()

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

def _fetch_via_supadata(video_id: str) -> tuple[str, list]:
    api_key = os.getenv("SUPADATA_API_KEY")
    if not api_key:
        raise ValueError("No Supadata key")
    response = requests.get(
        "https://api.supadata.ai/v1/youtube/transcript",
        params={"videoId": video_id, "text": True},
        headers={"x-api-key": api_key},
        timeout=15
    )
    data = response.json()
    if "error" in data or "content" not in data:
        raise ValueError(f"Supadata error: {data}")
    return data["content"], []

def _fetch_via_webshare(video_id: str) -> tuple[str, list]:
    username = os.getenv("WEBSHARE_USERNAME")
    password = os.getenv("WEBSHARE_PASSWORD")
    if not username or not password:
        raise ValueError("No WebShare credentials")
    ytt = YouTubeTranscriptApi(
        proxy_config=WebshareProxyConfig(
            proxy_username=username,
            proxy_password=password,
        )
    )
    fetched = ytt.fetch(video_id)
    full_text = " ".join([
        entry.text if hasattr(entry, 'text') else entry['text']
        for entry in fetched
    ])
    return full_text, fetched

def _fetch_direct(video_id: str) -> tuple[str, list]:
    ytt = YouTubeTranscriptApi()
    fetched = ytt.fetch(video_id)
    full_text = " ".join([
        entry.text if hasattr(entry, 'text') else entry['text']
        for entry in fetched
    ])
    return full_text, fetched

def get_transcript(url: str) -> tuple[str, str, list]:
    video_id = extract_video_id(url)

    # Try direct first (works locally)
    # Then Supadata (best for cloud, 100 free/month)
    # Then WebShare (proxy fallback)
    attempts = [
        ("direct", _fetch_direct),
        ("supadata", _fetch_via_supadata),
        ("webshare", _fetch_via_webshare),
    ]

    last_error = None
    for name, fetch_fn in attempts:
        try:
            full_text, fetched = fetch_fn(video_id)
            return full_text, video_id, fetched
        except (TranscriptsDisabled, NoTranscriptFound) as e:
            # These are definitive — no point trying other methods
            raise ValueError(str(e))
        except Exception as e:
            last_error = e
            continue

    raise ValueError(
        f"Could not fetch transcript after all attempts. Last error: {str(last_error)}"
    )

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