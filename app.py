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
        if hasattr(entry, 'get'):
            start_seconds = int(entry.get('start', 0))
            text = entry.get('text', '')
        elif hasattr(entry, 'start') and hasattr(entry, 'text'):
            start_seconds = int(entry.start)
            text = entry.text
        else:
            continue
            
        hours = start_seconds // 3600
        minutes = (start_seconds % 3600) // 60
        seconds = start_seconds % 60
        
        if hours > 0:
            timestamp_str = f"[{hours:02d}:{minutes:02d}:{seconds:02d}]"
        else:
            timestamp_str = f"[{minutes:02d}:{seconds:02d}]"
            
        formatted_lines.append(f"{timestamp_str} {text}")
    return "\n".join(formatted_lines)

# --- Page Config ---
st.set_page_config(
    page_title="LectureLens",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Custom CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }

    .stApp {
        background: radial-gradient(circle at 50% 30%, #080c14 0%, #030407 100%) !important;
        color: #e2e8f0;
    }

    .hero-title {
        font-size: 3.6rem;
        font-weight: 700;
        background: linear-gradient(135deg, #ffffff, #94a3b8, #10b981);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        text-align: center;
        margin-bottom: 0.2rem;
        line-height: 1.2;
        letter-spacing: -0.02em;
    }

    .hero-sub {
        text-align: center;
        color: #94a3b8;
        font-size: 1.1rem;
        margin-bottom: 2.5rem;
        font-weight: 300;
    }

    .card {
        background: rgba(22, 22, 35, 0.55) !important;
        backdrop-filter: blur(14px) !important;
        -webkit-backdrop-filter: blur(14px) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 24px !important;
        padding: 1.8rem !important;
        margin-bottom: 1.2rem !important;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3) !important;
    }

    .tab-content {
        background: rgba(22, 22, 35, 0.55) !important;
        backdrop-filter: blur(14px) !important;
        -webkit-backdrop-filter: blur(14px) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 24px !important;
        padding: 2rem !important;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3) !important;
    }

    .metric-card {
        background: rgba(22, 22, 35, 0.45) !important;
        backdrop-filter: blur(10px) !important;
        -webkit-backdrop-filter: blur(10px) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 20px !important;
        padding: 1.2rem 1.5rem !important;
        text-align: center;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2) !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    .metric-card:hover {
        transform: translateY(-4px);
        border-color: rgba(16, 185, 129, 0.3) !important;
        box-shadow: 0 12px 30px rgba(16, 185, 129, 0.18) !important;
    }

    .metric-number {
        font-size: 2.2rem;
        font-weight: 700;
        color: #10b981;
    }

    .metric-label {
        font-size: 0.78rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.08em;
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
        border-radius: 20px;
        padding: 1.5rem;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.4);
    }

    .flip-card-front {
        background: linear-gradient(135deg, rgba(22, 22, 35, 0.7), rgba(17, 24, 39, 0.7));
        border: 1px solid rgba(16, 185, 129, 0.3);
        color: #e2e8f0;
    }

    .flip-card-back {
        background: linear-gradient(135deg, rgba(6, 95, 70, 0.7), rgba(17, 24, 39, 0.7));
        border: 1px solid rgba(5, 150, 105, 0.4);
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
        background: rgba(16, 185, 129, 0.15);
        color: #a7f3d0;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }

    .flip-card-back .card-badge {
        background: rgba(52, 211, 153, 0.2);
        color: #a7f3d0;
        border: 1px solid rgba(52, 211, 153, 0.4);
    }

    .card-question {
        font-size: 1.1rem;
        font-weight: 600;
        line-height: 1.4;
        margin: auto 0;
        color: #f1f5f9;
    }

    .card-answer {
        font-size: 1.1rem;
        font-weight: 500;
        line-height: 1.4;
        margin: auto 0;
        color: #34d399;
    }

    .card-hint {
        font-size: 0.7rem;
        color: #94a3b8;
        font-style: italic;
    }

    /* --- Custom Unified Input Bar --- */
    .stTextInput > div > div > input {
        background: rgba(22, 22, 35, 0.65) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        border-radius: 30px !important;
        color: #f1f5f9 !important;
        font-size: 1rem !important;
        padding: 0.85rem 1.5rem !important;
        box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.3) !important;
        transition: all 0.3s ease !important;
    }

    .stTextInput > div > div > input:focus {
        border-color: #10b981 !important;
        box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.25) !important;
    }

    /* --- Custom Button and Segemented Pills --- */
    .stButton > button {
        border-radius: 30px !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        padding: 0.75rem 1.8rem !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        width: 100% !important;
    }

    /* Secondary buttons (unselected pills) in columns */
    div[data-testid="column"] button[kind="secondary"] {
        background: rgba(255, 255, 255, 0.02) !important;
        border: 1px solid rgba(255, 255, 255, 0.06) !important;
        color: #94a3b8 !important;
    }

    div[data-testid="column"] button[kind="secondary"]:hover {
        background: rgba(16, 185, 129, 0.08) !important;
        color: #34d399 !important;
        border-color: rgba(16, 185, 129, 0.3) !important;
        transform: translateY(-1px);
    }

    /* Primary buttons (active pills and main generate button) */
    .stButton button[kind="primary"], div[data-testid="column"] button[kind="primary"] {
        background: linear-gradient(135deg, #059669, #10b981) !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3) !important;
    }

    .stButton button[kind="primary"]:hover, div[data-testid="column"] button[kind="primary"]:hover {
        opacity: 0.92 !important;
        box-shadow: 0 6px 20px rgba(16, 185, 129, 0.45) !important;
        transform: translateY(-1px);
    }

    /* --- Custom Chat Styling --- */
    [data-testid="stChatMessage"] {
        background: rgba(22, 22, 35, 0.3) !important;
        border: 1px solid rgba(255, 255, 255, 0.04) !important;
        border-radius: 20px !important;
        padding: 1rem 1.2rem !important;
        margin-bottom: 0.8rem !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15) !important;
    }
    
    [data-testid="stChatMessage"] [data-testid="stChatMessageAvatar"] {
        background-color: rgba(16, 185, 129, 0.15) !important;
        border: 1px solid rgba(16, 185, 129, 0.3) !important;
    }

    .stSpinner > div {
        border-top-color: #10b981 !important;
    }

    .status-pill {
        display: inline-block;
        background: rgba(52, 211, 153, 0.12);
        color: #34d399;
        border: 1px solid rgba(52, 211, 153, 0.25);
        border-radius: 20px;
        padding: 0.2rem 0.8rem;
        font-size: 0.78rem;
        font-weight: 500;
    }

    hr {
        border-color: rgba(255, 255, 255, 0.05) !important;
        margin: 1.5rem 0 !important;
    }

    .stMarkdown h2, .stMarkdown h3 {
        color: #a7f3d0 !important;
    }

    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: #060511; }
    ::-webkit-scrollbar-thumb {
        background: rgba(255, 255, 255, 0.08);
        border-radius: 3px;
    }
</style>
""", unsafe_allow_html=True)


# --- Hero Section ---
st.markdown('<div class="hero-title">LectureLens</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-sub">Drop a YouTube lecture. Walk away with notes, flashcards, and a quiz.</div>',
    unsafe_allow_html=True
)

# --- Input Section ---
col1, col2, col3 = st.columns([1, 2.2, 1])
with col2:
    search_col1, search_col2 = st.columns([3.5, 1.2])
    with search_col1:
        url = st.text_input(
            "",
            placeholder="Paste YouTube lecture URL here...",
            label_visibility="collapsed",
            key="youtube_url_input"
        )
    with search_col2:
        generate_btn = st.button("✦ Generate", key="generate_btn", type="primary")

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
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "Notes"

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

    ts_transcript = format_transcript_with_timestamps(raw_transcript)
    results = {}
    progress = st.progress(0, text="Generating summary...")
    results["summary"] = generate_summary(ts_transcript, video_id)
    progress.progress(50, text="Writing notes...")
    results["notes"] = generate_notes(ts_transcript, video_id)
    results["flashcards"] = None
    results["quiz"] = None
    results["interview"] = None
    progress.progress(100, text="Done!")
    st.session_state.results = results
    st.session_state.quiz_answers = {}
    st.session_state.quiz_submitted = False
    st.session_state.chat_history = []
    st.session_state.active_tab = "Notes"
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
        # Segmented Control Pill Row using Columns
        tabs_list = [
            ("Notes", "Notes"),
            ("Flashcards", "Flashcards"),
            ("Quiz", "Quiz"),
            ("AskAI", "Ask AI"),
            ("Interview", "Interview Prep")
        ]
        nav_cols = st.columns(len(tabs_list))
        
        for idx, (tab_id, tab_label) in enumerate(tabs_list):
            with nav_cols[idx]:
                is_active = (st.session_state.active_tab == tab_id)
                # Primary styled button for active tab, Secondary for inactive
                if st.button(
                    tab_label, 
                    key=f"nav_btn_{tab_id}", 
                    type="primary" if is_active else "secondary"
                ):
                    st.session_state.active_tab = tab_id
                    st.rerun()
                    
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Render contents conditionally based on active_tab
        if st.session_state.active_tab == "Notes":
            st.markdown('<div class="tab-content">', unsafe_allow_html=True)
            st.markdown(results["notes"])
            st.download_button(
                "⬇ Download Notes",
                data=results["notes"],
                file_name="lecture_notes.md",
                mime="text/markdown",
                key="download_notes_btn"
            )
            st.markdown('</div>', unsafe_allow_html=True)
            
        elif st.session_state.active_tab == "Flashcards":
            st.markdown('<div class="tab-content">', unsafe_allow_html=True)
            if results.get("flashcards") is None:
                st.markdown("""
                <div style="text-align: center; padding: 2rem 0;">
                    <div style="font-size: 3rem; margin-bottom: 1rem;">🃏</div>
                    <h3 style="margin-bottom: 0.5rem; color:#ffffff;">Generate Flashcards</h3>
                    <p style="color: #94a3b8; font-size: 0.95rem; margin-bottom: 1.5rem; max-width: 400px; margin-left: auto; margin-right: auto;">
                        Ready to test your memory? Generate 8 interactive 3D flip cards covering the core concepts of this lecture on-demand.
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns([1.5, 2, 1.5])
                with col2:
                    if st.button("✦ Generate Flashcards", key="trigger_flashcards_btn", type="primary"):
                        with st.spinner("Creating flashcards..."):
                            try:
                                ts_transcript = format_transcript_with_timestamps(st.session_state.raw_transcript)
                                flashcards_res = generate_flashcards(ts_transcript, st.session_state.video_id)
                                st.session_state.results["flashcards"] = flashcards_res
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to generate: {e}")
            else:
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
            
        elif st.session_state.active_tab == "Quiz":
            st.markdown('<div class="tab-content">', unsafe_allow_html=True)
            if results.get("quiz") is None:
                st.markdown("""
                <div style="text-align: center; padding: 2rem 0;">
                    <div style="font-size: 3rem; margin-bottom: 1rem;">📝</div>
                    <h3 style="margin-bottom: 0.5rem; color:#ffffff;">Generate Quiz</h3>
                    <p style="color: #94a3b8; font-size: 0.95rem; margin-bottom: 1.5rem; max-width: 400px; margin-left: auto; margin-right: auto;">
                        Ready to test your knowledge? Generate a 5-question multiple choice professor's quiz covering this lecture on-demand.
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns([1.5, 2, 1.5])
                with col2:
                    if st.button("✦ Generate Quiz", key="trigger_quiz_btn", type="primary"):
                        with st.spinner("Building quiz..."):
                            try:
                                ts_transcript = format_transcript_with_timestamps(st.session_state.raw_transcript)
                                quiz_res = generate_quiz(ts_transcript, st.session_state.video_id)
                                st.session_state.results["quiz"] = quiz_res
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to generate: {e}")
            else:
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
                        <div style="background:rgba(22, 22, 35, 0.4); border:1px solid rgba(16, 185, 129, 0.2); border-radius:16px; padding:1.2rem; margin-bottom:1rem;">
                            <span style="color:#10b981; font-weight:700; font-size:0.8rem; text-transform:uppercase; letter-spacing:0.05em;">Question {idx+1}</span>
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
                        st.markdown("<hr style='margin: 0.8rem 0 !important; border-color: rgba(255,255,255,0.03)'>", unsafe_allow_html=True)
                    
                    c1, c2 = st.columns([1.2, 4])
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
            
        elif st.session_state.active_tab == "AskAI":
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
        
        elif st.session_state.active_tab == "Interview":
            st.markdown('<div class="tab-content">', unsafe_allow_html=True)
            if results.get("interview") is None:
                st.markdown("""
                <div style="text-align: center; padding: 2rem 0;">
                    <div style="font-size: 3rem; margin-bottom: 1rem;">🎯</div>
                    <h3 style="margin-bottom: 0.5rem; color:#ffffff;">Interview Prep</h3>
                    <p style="color: #94a3b8; font-size: 0.95rem; margin-bottom: 1.5rem; 
                    max-width: 400px; margin-left: auto; margin-right: auto;">
                        Generate FAANG-style interview questions based on this lecture's 
                        topics — with what a strong answer should cover.
                    </p>
                </div>
                """, unsafe_allow_html=True)
                col1, col2, col3 = st.columns([1.5, 2, 1.5])
                with col2:
                    if st.button("✦ Generate Questions", 
                                key="trigger_interview_btn", 
                                type="primary"):
                        with st.spinner("Generating interview questions..."):
                            try:
                                from utils.generator import generate_interview_questions
                                ts_transcript = format_transcript_with_timestamps(st.session_state.raw_transcript)
                                interview_res = generate_interview_questions(ts_transcript, st.session_state.video_id)
                                st.session_state.results["interview"] = interview_res
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to generate: {e}")
            else:
                st.markdown(results["interview"])
                st.download_button(
                    "⬇ Download Interview Questions",
                    data=results["interview"],
                    file_name="interview_prep.md",
                    mime="text/markdown",
                    key="download_interview_btn"
                )
            st.markdown('</div>', unsafe_allow_html=True)
        

    # Raw transcript expander
    with st.expander("View raw transcript"):
        st.text_area("", transcript, height=200, label_visibility="collapsed")