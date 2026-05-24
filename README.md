# LectureLens

Turn any YouTube lecture into structured notes, flashcards, a quiz, 
and interview prep — in under a minute.

**Live:** https://lecturelens-ai.streamlit.app

---

## What it does

Paste a YouTube URL. LectureLens extracts the transcript and runs 
it through an LLM pipeline to generate five things:

- **Notes** — topic-wise structured notes with key takeaways, downloadable as markdown
- **Flashcards** — 8 interactive 3D flip cards (hover to reveal answer)
- **Quiz** — 5 multiple choice questions with scoring and answer feedback
- **Ask AI** — chat with the lecture; answers include clickable timestamps that jump to the exact moment in the video
- **Interview Prep** — FAANG-style conceptual questions for technical lectures (detailing what a strong answer must cover) or career application questions for advice videos, formatted in a clean Q&A layout

Flashcards, quiz, and interview prep are generated on-demand to avoid unnecessary API calls.

---

## Why I built this

I kept rewatching hour-long ML lectures before exams. This solves that.

---

## Tech

- Python, Streamlit
- Gemini 2.5 Flash (google-genai SDK)
- youtube-transcript-api
- Custom CSS (3D flip cards, dark UI)
- Regex-based parser to convert raw LLM output into structured interactive components
- `st.session_state` for multi-tab state management and lazy loading

---

## Run locally

```bash
git clone https://github.com/Pappu-Meghana-Sharma/youtube-notes-ai
cd youtube-notes-ai
python -m venv venv
venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

Create a `.env` file:
```
GEMINI_API_KEY=your_key_here
```

Run:
```bash
streamlit run app.py
```

---

## Roadmap

- [ ] SQLite caching — save notes per video, instant load for repeated URLs
- [ ] User auth — login, personal history, revisit old notes
- [ ] Docker
- [ ] Anki export for flashcards
