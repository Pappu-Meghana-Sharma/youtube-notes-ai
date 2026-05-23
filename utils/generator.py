import os
from google import genai
from dotenv import load_dotenv

load_dotenv(override=True)

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL = "gemini-2.5-flash"

def _generate(prompt: str) -> str:
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt
    )
    return response.text

def generate_notes(transcript: str) -> str:
    prompt = f"""
You are an expert at converting lecture transcripts into clean, structured study notes.

Given the transcript below, generate:
- A one-paragraph overview of the lecture
- Topic-wise notes with clear headings
- Key takeaways as bullet points

Be concise. Use markdown formatting.

Transcript:
{transcript[:6000]}
"""
    return _generate(prompt)

def generate_flashcards(transcript: str) -> str:
    prompt = f"""
You are a study assistant. From the transcript below, create exactly 8 flashcards.

Format each flashcard exactly like this:
**Q:** [question]
**A:** [answer]

Focus on key concepts, definitions, and important facts.

Transcript:
{transcript[:6000]}
"""
    return _generate(prompt)

def generate_quiz(transcript: str) -> str:
    prompt = f"""
You are a professor creating a quiz. From the transcript below, create exactly 5 
multiple choice questions.

Format each question exactly like this:
**Q1.** [question]
- A) [option]
- B) [option]
- C) [option]
- D) [option]
**Answer:** [correct option]

Transcript:
{transcript[:6000]}
"""
    return _generate(prompt)

def generate_summary(transcript: str) -> str:
    prompt = f"""
Summarize this lecture transcript in exactly 5 bullet points.
Each bullet should be one clear, informative sentence.
Use markdown bullet points.

Transcript:
{transcript[:6000]}
"""
    return _generate(prompt)

def generate_chat_response(prompt: str, chat_history: list, timestamped_transcript: str, video_id: str) -> str:
    system_instruction = f"""
You are an expert learning assistant for LectureAI. Your job is to answer questions about the video lecture provided.
You are given the full transcript of the video with timestamps. 

When the user asks where a topic is discussed, or when you refer to specific parts of the video, you MUST provide the timestamp in brackets, e.g. [02:15] or [01:10:45].
In addition, make these timestamps clickable links that open the video at that exact second.
The format of the link MUST be: [MM:SS](https://youtu.be/{video_id}?t=SECONDS) or [HH:MM:SS](https://youtu.be/{video_id}?t=SECONDS).
For example: [02:15](https://youtu.be/{video_id}?t=135) or [01:10:45](https://youtu.be/{video_id}?t=4245).
Calculate the seconds accurately from the timestamp (e.g., 2 minutes and 15 seconds is 135 seconds).

Be helpful, concise, and educational. Keep your tone encouraging and professional.

Timestamped Transcript:
{timestamped_transcript[:120000]}
"""

    contents = []
    for msg in chat_history:
        contents.append({
            "role": "user" if msg["role"] == "user" else "model",
            "parts": [{"text": msg["content"]}]
        })
        
    contents.append({
        "role": "user",
        "parts": [{"text": prompt}]
    })
    
    response = client.models.generate_content(
        model=MODEL,
        contents=contents,
        config={
            "system_instruction": system_instruction
        }
    )
    return response.text