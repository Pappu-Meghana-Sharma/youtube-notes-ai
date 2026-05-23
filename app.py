import streamlit as st
import re
from utils.transcript import get_transcript, chunk_transcript
from utils.generator import generate_notes, generate_flashcards, generate_quiz, generate_summary, generate_chat_response

def parse_flashcards(flashcards_text):
    cards = re.split(r'(?=\*\*Q:\*\*)', flashcards_text)
    parsed = []
    for card in cards:
        if card.strip():
            parts = re.split(r'(\*\*A:\*\*)', card, maxsplit=1)
            if len(parts) >= 3:
                question = parts[0].replace("**Q:**", "").strip()
                question = re.sub(r'^[\s\n*#-]+', '', question)
                answer = parts[2].strip()
                answer = re.sub(r'[\s\n*#-]+$', '', answer)
                if question and answer:
                    parsed.append({"question": question, "answer": answer})
    return parsed

def parse_quiz(quiz_text):
    q_blocks = re.split(r'\*\*Q\d+\.?\*\*', quiz_text)
    parsed = []
    for block in q_blocks:
        block = block.strip()
        if not block:
            continue
        lines = [l.strip() for l in block.split("\n") if l.strip()]
        if not lines:
            continue
        
        opt_start_idx = -1
        for idx, line in enumerate(lines):
            if line.startswith(("- A)", "- B)", "- C)", "- D)", "A)", "B)", "C)", "D)")):
                opt_start_idx = idx
                break
        if opt_start_idx == -1:
            continue
            
        question_text = " ".join(lines[:opt_start_idx]).strip()
        options = {}
        correct_answer = ""
        
        for line in lines[opt_start_idx:]:
            opt_match = re.match(r'^[-*\s]*([A-D])\)\s*(.*)', line)
            if opt_match:
                letter, text = opt_match.groups()
                options[letter] = text.strip()
            elif "Answer:" in line:
                ans_match = re.search(r'Answer:\*\*\s*([A-D])', line, re.IGNORECASE)
                if not ans_match:
                    ans_match = re.search(r'Answer:\s*([A-D])', line, re.IGNORECASE)
                if ans_match:
                    correct_answer = ans_match.group(1).upper()
                    
        if question_text and len(options) == 4 and correct_answer:
            parsed.append({
                "question": question_text,
                "options": options,
                "answer": correct_answer
            })
    return parsed

def format_transcript_with_timestamps(raw_transcript):
    if not raw_transcript:
        return ""
    formatted_lines = []
    for entry in raw_transcript:
        if not isinstance(entry, dict):
            continue
        start_seconds = int(entry.get('start', 0))
        hours = start_seconds // 3600
        minutes = (start_seconds % 3600) // 60
        seconds = start_seconds % 60
        
        if hours > 0:
            timestamp_str = f"[{hours:02d}:{minutes:02d}:{seconds:02d}]"
        else:
            timestamp_str = f"[{minutes:02d}:{seconds:02d}]"
            
        formatted_lines.append(f"{timestamp_str} {entry.get('text', '')}")
    return "\n".join(formatted_lines)

# --- Page Config ---
st.set_page_config(
    page_title="LectureAI",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Custom CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .stApp {
        background: #0f0f13;
        color: #e8e8e8;
    }

    .hero-title {
        font-size: 3.2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #a78bfa, #60a5fa, #34d399);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-align: center;
        margin-bottom: 0.2rem;
        line-height: 1.2;
    }

    .hero-sub {
        text-align: center;
        color: #6b7280;
        font-size: 1.05rem;
        margin-bottom: 2.5rem;
        font-weight: 300;
    }

    .card {
        background: #16161f;
        border: 1px solid #2a2a3a;
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }

    .tab-content {
        background: #16161f;
        border: 1px solid #2a2a3a;
        border-radius: 0 16px 16px 16px;
        padding: 1.8rem;
        margin-top: -1px;
    }

    .metric-card {
        background: linear-gradient(135deg, #1e1b4b, #1e1e2e);
        border: 1px solid #3730a3;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        text-align: center;
    }

    .metric-number {
        font-size: 2rem;
        font-weight: 700;
        color: #a78bfa;
    }

    .metric-label {
        font-size: 0.75rem;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* --- 3D Flashcard Flipping --- */
    .flip-card {
        background-color: transparent;
        width: 100%;
        height: 200px;
        perspective: 1000px;
        margin-bottom: 1.2rem;
        cursor: pointer;
    }

    .flip-card-inner {
        position: relative;
        width: 100%;
        height: 100%;
        text-align: center;
        transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1);
        transform-style: preserve-3d;
    }

    .flip-card:hover .flip-card-inner {
        transform: rotateY(180deg);
    }

    .flip-card-front, .flip-card-back {
        position: absolute;
        width: 100%;
        height: 100%;
        -webkit-backface-visibility: hidden;
        backface-visibility: hidden;
        border-radius: 16px;
        padding: 1.5rem;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.35);
    }

    .flip-card-front {
        background: linear-gradient(135deg, #1e1b4b, #111827);
        border: 1px solid #4f46e5;
        color: #e8e8e8;
    }

    .flip-card-back {
        background: linear-gradient(135deg, #065f46, #111827);
        border: 1px solid #059669;
        color: #ffffff;
        transform: rotateY(180deg);
    }

    .card-badge {
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        font-weight: 700;
        padding: 0.2rem 0.6rem;
        border-radius: 20px;
    }

    .flip-card-front .card-badge {
        background: rgba(99, 102, 241, 0.2);
        color: #a5b4fc;
        border: 1px solid rgba(99, 102, 241, 0.4);
    }

    .flip-card-back .card-badge {
        background: rgba(52, 211, 153, 0.2);
        color: #34d399;
        border: 1px solid rgba(52, 211, 153, 0.4);
    }

    .card-question {
        font-size: 1.05rem;
        font-weight: 600;
        line-height: 1.4;
        margin: auto 0;
        color: #e8e8e8;
    }

    .card-answer {
        font-size: 1.05rem;
        font-weight: 500;
        line-height: 1.4;
        margin: auto 0;
        color: #34d399;
    }

    .card-hint {
        font-size: 0.7rem;
        color: #6b7280;
        font-style: italic;
    }

    .stTextInput > div > div > input {
        background: #16161f !important;
        border: 1px solid #2a2a3a !important;
        border-radius: 12px !important;
        color: #e8e8e8 !important;
        font-size: 0.95rem !important;
        padding: 0.75rem 1rem !important;
    }

    .stTextInput > div > div > input:focus {
        border-color: #a78bfa !important;
        box-shadow: 0 0 0 2px rgba(167, 139, 250, 0.15) !important;
    }

    .stButton > button {
        background: linear-gradient(135deg, #7c3aed, #4f46e5) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.6rem 2rem !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        width: 100% !important;
        transition: opacity 0.2s !important;
    }

    .stButton > button:hover {
        opacity: 0.85 !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        background: #16161f;
        border-radius: 12px 12px 0 0;
        border: 1px solid #2a2a3a;
        border-bottom: none;
        gap: 0;
        padding: 0.3rem 0.3rem 0;
    }

    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border-radius: 8px 8px 0 0;
        color: #6b7280;
        font-weight: 500;
        padding: 0.6rem 1.4rem;
    }

    .stTabs [aria-selected="true"] {
        background: #0f0f13 !important;
        color: #a78bfa !important;
        border-bottom: 2px solid #a78bfa !important;
    }

    .stSpinner > div {
        border-top-color: #a78bfa !important;
    }

    .status-pill {
        display: inline-block;
        background: rgba(52, 211, 153, 0.15);
        color: #34d399;
        border: 1px solid rgba(52, 211, 153, 0.3);
        border-radius: 20px;
        padding: 0.2rem 0.8rem;
        font-size: 0.78rem;
        font-weight: 500;
    }

    hr {
        border-color: #2a2a3a !important;
        margin: 1.5rem 0 !important;
    }

    .stMarkdown h2, .stMarkdown h3 {
        color: #c4b5fd !important;
    }

    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #0f0f13; }
    ::-webkit-scrollbar-thumb {
        background: #2a2a3a;
        border-radius: 3px;
    }
</style>
""", unsafe_allow_html=True)


# --- Hero Section ---
st.markdown('<div class="hero-title">LectureAI</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-sub">Drop a YouTube lecture. Walk away with notes, flashcards, and a quiz.</div>',
    unsafe_allow_html=True
)

# --- Input Section ---
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    url = st.text_input(
        "",
        placeholder="https://www.youtube.com/watch?v=...",
        label_visibility="collapsed"
    )
    generate_btn = st.button("✦ Generate Notes")

st.markdown("---")

# --- State ---
if "results" not in st.session_state:
    st.session_state.results = None
if "transcript" not in st.session_state:
    st.session_state.transcript = None
if "video_id" not in st.session_state:
    st.session_state.video_id = None
if "raw_transcript" not in st.session_state:
    st.session_state.raw_transcript = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- Generation Logic ---
if generate_btn and url:
    with st.spinner("Fetching transcript..."):
        try:
            transcript, video_id, raw_transcript = get_transcript(url)
            st.session_state.transcript = transcript
            st.session_state.video_id = video_id
            st.session_state.raw_transcript = raw_transcript
        except ValueError as e:
            st.error(str(e))
            st.stop()

    results = {}
    progress = st.progress(0, text="Generating summary...")
    results["summary"] = generate_summary(transcript)
    progress.progress(25, text="Writing notes...")
    results["notes"] = generate_notes(transcript)
    progress.progress(55, text="Creating flashcards...")
    results["flashcards"] = generate_flashcards(transcript)
    progress.progress(80, text="Building quiz...")
    results["quiz"] = generate_quiz(transcript)
    progress.progress(100, text="Done!")
    st.session_state.results = results
    st.session_state.quiz_answers = {}
    st.session_state.quiz_submitted = False
    st.session_state.chat_history = []
    st.rerun()

elif generate_btn and not url:
    st.warning("Please paste a YouTube URL first.")

# --- Results ---
if st.session_state.results:
    results = st.session_state.results
    transcript = st.session_state.transcript
    video_id = st.session_state.video_id

    # Metrics row
    word_count = len(transcript.split())
    read_time = round(word_count / 200)
    note_words = len(results["notes"].split())

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-number">{word_count:,}</div>
            <div class="metric-label">Transcript Words</div>
        </div>""", unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-number">~{read_time}m</div>
            <div class="metric-label">Lecture Length</div>
        </div>""", unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-number">{note_words}</div>
            <div class="metric-label">Note Words</div>
        </div>""", unsafe_allow_html=True)
    with m4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-number">8 + 5</div>
            <div class="metric-label">Cards + Questions</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Embedded video + tabs side by side
    left, right = st.columns([1, 1.8])

    with left:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.video(f"https://www.youtube.com/watch?v={video_id}")
        st.markdown('<span class="status-pill">✓ Transcript extracted</span>',
                    unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**Quick Summary**")
        st.markdown(results["summary"])
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        tab1, tab2, tab3, tab4 = st.tabs(["📋  Notes", "🃏  Flashcards", "📝  Quiz", "💬  Ask AI"])

        with tab1:
            st.markdown('<div class="tab-content">', unsafe_allow_html=True)
            st.markdown(results["notes"])
            st.download_button(
                "⬇ Download Notes",
                data=results["notes"],
                file_name="lecture_notes.md",
                mime="text/markdown"
            )
            st.markdown('</div>', unsafe_allow_html=True)

        with tab2:
            st.markdown('<div class="tab-content">', unsafe_allow_html=True)
            parsed_cards = parse_flashcards(results["flashcards"])
            if not parsed_cards:
                st.warning("Could not parse flashcards. Showing raw output instead:")
                st.markdown(results["flashcards"])
            else:
                cols = st.columns(2)
                for idx, card in enumerate(parsed_cards):
                    col = cols[idx % 2]
                    with col:
                        q_escaped = card["question"].replace('"', '&quot;').replace("'", "&#39;")
                        a_escaped = card["answer"].replace('"', '&quot;').replace("'", "&#39;")
                        st.markdown(f"""
                        <div class="flip-card">
                            <div class="flip-card-inner">
                                <div class="flip-card-front">
                                    <span class="card-badge">Question</span>
                                    <div class="card-question">{q_escaped}</div>
                                    <span class="card-hint">Hover to reveal answer</span>
                                </div>
                                <div class="flip-card-back">
                                    <span class="card-badge">Answer</span>
                                    <div class="card-answer">{a_escaped}</div>
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with tab3:
            st.markdown('<div class="tab-content">', unsafe_allow_html=True)
            if "quiz_answers" not in st.session_state:
                st.session_state.quiz_answers = {}
            if "quiz_submitted" not in st.session_state:
                st.session_state.quiz_submitted = False
                
            quiz_data = parse_quiz(results["quiz"])
            if not quiz_data:
                st.warning("Could not parse quiz questions. Showing raw quiz output:")
                st.markdown(results["quiz"])
            else:
                if st.session_state.quiz_submitted:
                    correct_count = sum(
                        1 for idx, q in enumerate(quiz_data)
                        if st.session_state.quiz_answers.get(idx) == q["answer"]
                    )
                    total_count = len(quiz_data)
                    percentage = (correct_count / total_count) * 100
                    
                    if percentage >= 80:
                        st.success(f"### 🎉 Score: {correct_count} / {total_count} ({percentage:.0f}%) — Excellent Job!")
                    elif percentage >= 50:
                        st.info(f"### 👍 Score: {correct_count} / {total_count} ({percentage:.0f}%) — Good Effort!")
                    else:
                        st.error(f"### 📚 Score: {correct_count} / {total_count} ({percentage:.0f}%) — Keep Studying!")
                
                for idx, q in enumerate(quiz_data):
                    st.markdown(f"""
                    <div style="background:#1e1b4b; border:1px solid #3730a3; border-radius:12px; padding:1.2rem; margin-bottom:1rem;">
                        <span style="color:#a78bfa; font-weight:700; font-size:0.8rem; text-transform:uppercase; letter-spacing:0.05em;">Question {idx+1}</span>
                        <div style="font-size:1.05rem; font-weight:600; margin-top:0.4rem; color:#ffffff;">{q["question"]}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    options_list = ["A", "B", "C", "D"]
                    formatted_options = [f"{letter}) {q['options'][letter]}" for letter in options_list]
                    
                    saved_sel = st.session_state.quiz_answers.get(idx)
                    default_idx = options_list.index(saved_sel) if saved_sel in options_list else None
                    
                    selected_val = st.radio(
                        label=f"Choose option for question {idx+1}",
                        options=formatted_options,
                        index=default_idx,
                        key=f"q_radio_{idx}",
                        disabled=st.session_state.quiz_submitted,
                        label_visibility="collapsed"
                    )
                    
                    if selected_val:
                        selected_letter = selected_val[0]
                        st.session_state.quiz_answers[idx] = selected_letter
                        
                    if st.session_state.quiz_submitted:
                        user_ans = st.session_state.quiz_answers.get(idx)
                        correct_ans = q["answer"]
                        
                        if user_ans == correct_ans:
                            st.markdown(f'<p style="color:#34d399; font-weight:600; margin-top:-0.5rem; margin-bottom:1rem;">✓ Correct! Selected: {user_ans}) {q["options"][correct_ans]}</p>', unsafe_allow_html=True)
                        else:
                            selected_str = f"{user_ans}) {q['options'].get(user_ans, '')}" if user_ans else "None"
                            st.markdown(f"""
                            <p style="color:#f87171; font-weight:600; margin-top:-0.5rem; margin-bottom:0.2rem;">✗ Incorrect! Selected: {selected_str}</p>
                            <p style="color:#34d399; font-weight:600; margin-bottom:1rem;">✓ Correct Answer: {correct_ans}) {q["options"][correct_ans]}</p>
                            """, unsafe_allow_html=True)
                    st.markdown("<hr style='margin: 0.8rem 0 !important;'>", unsafe_allow_html=True)
                
                c1, c2 = st.columns([1, 4])
                with c1:
                    if not st.session_state.quiz_submitted:
                        if st.button("Submit Answers", key="submit_quiz_btn"):
                            if len(st.session_state.quiz_answers) < len(quiz_data):
                                st.warning("Please answer all questions before submitting.")
                            else:
                                st.session_state.quiz_submitted = True
                                st.rerun()
                    else:
                        if st.button("Retake Quiz", key="retake_quiz_btn"):
                            st.session_state.quiz_answers = {}
                            st.session_state.quiz_submitted = False
                            st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with tab4:
            st.markdown('<div class="tab-content">', unsafe_allow_html=True)
            st.markdown("### 💬 Ask Questions About the Video")
            st.markdown("Ask anything about this lecture. The AI will answer and point you to relevant sections of the video with clickable timestamps.")
            
            chat_container = st.container()
            with chat_container:
                for msg in st.session_state.chat_history:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])
            
            if user_query := st.chat_input("Ask a question about the video..."):
                with chat_container:
                    with st.chat_message("user"):
                        st.markdown(user_query)
                
                st.session_state.chat_history.append({"role": "user", "content": user_query})
                
                with chat_container:
                    with st.chat_message("assistant"):
                        with st.spinner("Analyzing transcript..."):
                            try:
                                ts_transcript = format_transcript_with_timestamps(st.session_state.raw_transcript)
                                response = generate_chat_response(
                                    prompt=user_query,
                                    chat_history=st.session_state.chat_history[:-1],
                                    timestamped_transcript=ts_transcript,
                                    video_id=st.session_state.video_id
                                )
                                st.markdown(response)
                                st.session_state.chat_history.append({"role": "assistant", "content": response})
                            except Exception as e:
                                st.error(f"Error generating response: {str(e)}")
                
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    # Raw transcript expander
    with st.expander("View raw transcript"):
        st.text_area("", transcript, height=200, label_visibility="collapsed")