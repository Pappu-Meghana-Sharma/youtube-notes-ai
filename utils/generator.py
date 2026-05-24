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

def generate_notes(transcript: str, video_id: str) -> str:
    prompt = f"""
You are an expert at converting lecture transcripts into clean, structured, and highly detailed study notes for LectureLens.

Given the transcript below:
1. Generate topic-wise notes with clear, informative headings.
2. Under each topic, provide detailed explanations of the techniques, concepts, or advice discussed.
3. Do NOT include any timestamps, bracketed times, or YouTube links. Keep the notes clean, clean-formatted, and easy to read or download.

Strict Grounding Rules:
- Rely strictly and only on the information explicitly stated by the speaker in the provided video transcript.
- Do not invent outside facts, bring in outside knowledge, or assume facts not mentioned in the transcript.
- Focus heavily on delivering important educational insights, core conceptual takeaways, and actionable techniques that are highly valuable to students and self-learners.

Transcript:
{transcript}
"""
    return _generate(prompt)

def generate_flashcards(transcript: str, video_id: str) -> str:
    prompt = f"""
You are a study assistant for LectureLens. From the timestamped transcript below, create exactly 8 flashcards.

Format each flashcard exactly like this:
**Q:** [question]
**A:** [detailed answer] (Reference: You MUST provide the exact timestamp formatted as a clickable link using the format [MM:SS](https://youtu.be/{video_id}?t=SECONDS) or [HH:MM:SS](https://youtu.be/{video_id}?t=SECONDS). Do NOT output plain text timestamps. Example: [09:43](https://youtu.be/{video_id}?t=583))

Focus on concrete facts, definitions, and specific techniques. Calculate the total seconds accurately from the timestamp.

Strict Grounding Rules:
- Rely strictly and only on the information explicitly stated by the speaker in the provided video transcript.
- Do not invent outside facts, bring in outside knowledge, or assume facts not mentioned in the transcript.
- Focus heavily on delivering important educational insights, core conceptual takeaways, and actionable techniques that are highly valuable to students and self-learners.

Transcript:
{transcript}
"""
    return _generate(prompt)

def generate_quiz(transcript: str, video_id: str) -> str:
    prompt = f"""
You are a professor creating a quiz for LectureLens. From the timestamped transcript below, create exactly 5 multiple choice questions.

Format each question exactly like this:
**Q1.** [question]
- A) [option]
- B) [option]
- C) [option]
- D) [option]
**Answer:** [correct option] (Reference: You MUST provide the exact timestamp formatted as a clickable link using the format [MM:SS](https://youtu.be/{video_id}?t=SECONDS) or [HH:MM:SS](https://youtu.be/{video_id}?t=SECONDS). Do NOT output plain text timestamps. Example: [09:43](https://youtu.be/{video_id}?t=583))

Focus on testing concrete knowledge, techniques, or facts. Calculate the total seconds accurately from the timestamp.

Strict Grounding Rules:
- Rely strictly and only on the information explicitly stated by the speaker in the provided video transcript.
- Do not invent outside facts, bring in outside knowledge, or assume facts not mentioned in the transcript.
- Focus heavily on delivering important educational insights, core conceptual takeaways, and actionable techniques that are highly valuable to students and self-learners.

Transcript:
{transcript}
"""
    return _generate(prompt)

def generate_summary(transcript: str, video_id: str) -> str:
    prompt = f"""
Summarize this lecture transcript in exactly 5 key bullet points for LectureLens.
Each bullet point must cover an important technique, key fact, or insight from the video.
Include a clickable timestamp link for each bullet point indicating where it occurs.
The link format must be: You MUST provide the exact timestamp formatted as a clickable link using the format [MM:SS](https://youtu.be/{video_id}?t=SECONDS) or [HH:MM:SS](https://youtu.be/{video_id}?t=SECONDS). Do NOT output plain text timestamps. Example: [09:43](https://youtu.be/{video_id}?t=583).
Calculate the total seconds accurately from the timestamp.

Strict Grounding Rules:
- Rely strictly and only on the information explicitly stated by the speaker in the provided video transcript.
- Do not invent outside facts, bring in outside knowledge, or assume facts not mentioned in the transcript.
- Focus heavily on delivering important educational insights, core conceptual takeaways, and actionable techniques that are highly valuable to students and self-learners.

Transcript:
{transcript}
"""
    return _generate(prompt)

def generate_interview_questions(transcript: str, video_id: str) -> str:
    prompt = f"""
You are a technical interviewer for LectureLens. Based on the timestamped lecture transcript below, generate 5 interview questions a FAANG interviewer might ask a candidate who claims to know this topic.

For each question include:
- The question itself
- What a strong answer should cover (2-3 bullet points)
- Difficulty: Easy / Medium / Hard
- Lecture Reference: You MUST provide the exact timestamp formatted as a clickable link using the format [MM:SS](https://youtu.be/{video_id}?t=SECONDS) or [HH:MM:SS](https://youtu.be/{video_id}?t=SECONDS). Do NOT output plain text timestamps. Every reference must be a link. Example: [09:43](https://youtu.be/{video_id}?t=583)

Format cleanly with markdown. Ensure questions are technically deep and directly tied to the specific facts discussed. Calculate the total seconds accurately from the timestamp.

Strict Grounding Rules:
- Rely strictly and only on the information explicitly stated by the speaker in the provided video transcript.
- Do not invent outside facts, bring in outside knowledge, or assume facts not mentioned in the transcript.
- Focus heavily on delivering important educational insights, core conceptual takeaways, and actionable techniques that are highly valuable to students and self-learners.

Transcript:
{transcript}
"""
    return _generate(prompt)

def generate_chat_response(prompt: str, chat_history: list, timestamped_transcript: str, video_id: str) -> str:
    system_instruction = f"""
You are an expert learning assistant for LectureLens. Your job is to answer questions about the video lecture provided.
You are given the full transcript of the video with timestamps. 

When the user asks where a topic is discussed, or when you refer to specific parts of the video, you MUST provide the timestamp in brackets, e.g. [02:15] or [01:10:45].
In addition, make these timestamps clickable links that open the video at that exact second.
The format of the link MUST be: [MM:SS](https://youtu.be/{video_id}?t=SECONDS) or [HH:MM:SS](https://youtu.be/{video_id}?t=SECONDS).
For example: [02:15](https://youtu.be/{video_id}?t=135) or [01:10:45](https://youtu.be/{video_id}?t=4245).
Calculate the seconds accurately from the timestamp (e.g., 2 minutes and 15 seconds is 135 seconds).

Strict Grounding Rules:
- Rely strictly and only on the information explicitly stated by the speaker in the provided video transcript.
- Do not invent outside facts, bring in outside knowledge, or assume facts not mentioned in the transcript.
- Focus heavily on delivering important educational insights, core conceptual takeaways, and actionable techniques that are highly valuable to students and self-learners.

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