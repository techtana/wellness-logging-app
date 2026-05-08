"""PDF report generator for clinical sessions using fpdf2."""
from datetime import datetime
import re


def _s(text) -> str:
    """Encode text to latin-1, substituting unsupported characters."""
    if not isinstance(text, str):
        text = str(text) if text is not None else ""
    subs = {
        "–": "-", "—": "--", "‘": "'", "’": "'",
        "“": '"', "”": '"', "•": "*", "…": "...",
        "·": ".", "’": "'",
    }
    for k, v in subs.items():
        text = text.replace(k, v)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def generate_pdf(session: dict) -> bytes:
    try:
        from fpdf import FPDF
    except ImportError:
        raise ImportError("fpdf2 is not installed. Run: pip install fpdf2")

    class Report(FPDF):
        def header(self):
            if self.page_no() == 1:
                return
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(160, 160, 160)
            sid = _s(session.get("session_id", ""))
            self.cell(0, 6, f"Clinical Session Report  ·  {sid}", align="L")
            self.ln(2)
            self.set_draw_color(220, 220, 220)
            self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
            self.ln(4)
            self.set_text_color(0, 0, 0)
            self.set_draw_color(0, 0, 0)

        def footer(self):
            self.set_y(-15)
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(160, 160, 160)
            self.cell(0, 6, f"Page {self.page_no()}", align="C")
            self.set_text_color(0, 0, 0)

    pdf = Report()
    pdf.set_margins(22, 22, 22)
    pdf.set_auto_page_break(True, margin=22)
    pdf.add_page()

    def divider(r=200, g=210, b=230):
        pdf.set_draw_color(r, g, b)
        pdf.set_line_width(0.3)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
        pdf.set_draw_color(0, 0, 0)
        pdf.set_line_width(0.2)
        pdf.ln(4)

    def section(title: str):
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(240, 244, 250)
        pdf.set_text_color(50, 80, 130)
        pdf.cell(0, 8, f"  {_s(title.upper())}", fill=True, ln=True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)

    def body(text: str, indent: float = 0):
        pdf.set_font("Helvetica", "", 10)
        if indent:
            pdf.set_x(pdf.l_margin + indent)
        pdf.multi_cell(0, 5.5, _s(text))
        pdf.ln(1)

    def kv(label: str, value: str):
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(46, 6, _s(label.upper()), ln=False)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(26, 35, 50)
        pdf.multi_cell(0, 6, _s(str(value)))
        pdf.set_x(pdf.l_margin)  # fpdf2 2.8.x leaves x at right edge after multi_cell
        pdf.set_text_color(0, 0, 0)

    def bullet(text: str):
        pdf.set_font("Helvetica", "", 10)
        pdf.set_x(pdf.l_margin + 4)
        pdf.cell(5, 5.5, "-")
        pdf.multi_cell(0, 5.5, _s(text))
        pdf.ln(0.5)

    # ── Cover ──────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(26, 35, 50)
    pdf.cell(0, 13, "Clinical Session Report", ln=True, align="C")
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 7, _s("ClinicalAI  —  Therapeutic Communication Analysis"), ln=True, align="C")
    pdf.ln(3)
    pdf.set_draw_color(59, 111, 212)
    pdf.set_line_width(0.6)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.set_line_width(0.2)
    pdf.set_draw_color(0, 0, 0)
    pdf.ln(6)
    pdf.set_text_color(0, 0, 0)

    sid = session.get("session_id", "unknown")
    created = session.get("created_at", "")
    if created:
        try:
            created = datetime.fromisoformat(created).strftime("%B %d, %Y  %H:%M")
        except Exception:
            pass
    analysis = session.get("analysis") or {}
    ai_enhanced = analysis.get("ai_enhanced", False)

    kv("Session ID", sid)
    kv("Date", created)
    kv("Status", session.get("status", "unknown").replace("_", " ").title())
    kv("AI Enhanced", "Yes" if ai_enhanced else "No (keyword-based)")
    pdf.ln(4)
    divider()

    # ── Session transcript ──────────────────────────────────
    turns = session.get("turns", [])
    if turns:
        section("Session Transcript")
        prompt_n = 1
        for turn in turns:
            speaker = turn.get("speaker", "")
            text = turn.get("text", "")
            skipped = turn.get("skipped", False)
            if speaker == "therapist":
                pdf.set_font("Helvetica", "B", 8)
                pdf.set_text_color(59, 111, 212)
                pdf.cell(0, 5, f"PROMPT {prompt_n}", ln=True)
                pdf.set_text_color(0, 0, 0)
                body(text)
            else:
                pdf.set_font("Helvetica", "B", 8)
                pdf.set_text_color(13, 148, 136)
                pdf.cell(0, 5, "RESPONSE", ln=True)
                pdf.set_text_color(0, 0, 0)
                if skipped:
                    pdf.set_font("Helvetica", "I", 10)
                    pdf.set_text_color(160, 160, 160)
                    pdf.multi_cell(0, 5.5, "(Skipped)")
                    pdf.set_text_color(0, 0, 0)
                else:
                    body(text)
                pdf.ln(2)
                prompt_n += 1

    # ── Analysis sections ──────────────────────────────────
    sections_data = analysis.get("insight_report", {}).get("sections", {})
    raw = analysis.get("analysis", {})

    # Executive summary
    exec_s = sections_data.get("executive_summary", {})
    if exec_s:
        section("Executive Summary")
        if exec_s.get("overall_tone_trajectory"):
            body(exec_s["overall_tone_trajectory"])
        for tk in exec_s.get("key_takeaways", []):
            bullet(tk)
        if exec_s.get("priority_focus_area"):
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(180, 100, 10)
            pdf.cell(0, 6, "Priority Focus: ", ln=True)
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(0, 0, 0)
            pdf.multi_cell(0, 6, _s(exec_s["priority_focus_area"]))
            pdf.set_x(pdf.l_margin)

    # Emotional analysis
    sentiment = raw.get("sentiment_analysis", {})
    sent_sum = sentiment.get("summary", {})
    if sent_sum:
        section("Emotional Analysis")
        if sent_sum.get("overall_sentiment"):
            kv("Dominant Emotion", sent_sum["overall_sentiment"])
        if sent_sum.get("emotional_stability"):
            kv("Stability", sent_sum["emotional_stability"])
        dist = sent_sum.get("emotion_distribution", {})
        if dist:
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(100, 116, 139)
            pdf.cell(0, 5, "DISTRIBUTION", ln=True)
            pdf.set_text_color(0, 0, 0)
            for emo, count in sorted(dist.items(), key=lambda x: -x[1]):
                bullet(f"{emo}: {count} occurrence(s)")

    # Thematic analysis
    theme_s = sections_data.get("thematic_analysis", {})
    thematic_raw = raw.get("thematic_analysis", {})
    if theme_s or thematic_raw:
        section("Thematic Analysis")
        dominant = theme_s.get("dominant_themes", [])
        if dominant:
            kv("Dominant Themes", ", ".join(dominant))
        underlying = theme_s.get("underlying_themes", [])
        if underlying:
            kv("Underlying Themes", ", ".join(underlying))
        distortions = thematic_raw.get("cognitive_distortions", [])
        if distortions:
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(100, 116, 139)
            pdf.cell(0, 5, "COGNITIVE DISTORTIONS", ln=True)
            pdf.set_text_color(0, 0, 0)
            for d in distortions[:8]:
                bullet(f"{d.get('distortion_type', '')}  [{d.get('severity', 'Moderate')}]")

    # Relational dynamics
    relational = raw.get("relational_dynamics", {})
    alliance = relational.get("therapeutic_alliance", {})
    if alliance:
        section("Relational Dynamics")
        if alliance.get("rating"):
            kv("Alliance Rating", alliance["rating"])
        if relational.get("dominant_dynamic"):
            kv("Dominant Dynamic", relational["dominant_dynamic"])
        for e in relational.get("relational_events", [])[:5]:
            ctx = e.get("context", "")[:100]
            bullet(f"{e.get('event_type', '')}: {ctx}")

    # Clinical recommendations
    recs = sections_data.get("recommendations", {})
    hyp = sections_data.get("clinical_hypothesis", {})
    if recs or hyp:
        section("Clinical Recommendations")
        for action in recs.get("immediate_actions", []):
            bullet(action)
        if recs.get("next_session_focus"):
            kv("Next Session Focus", recs["next_session_focus"])
        red_flags = recs.get("red_flags", [])
        if red_flags:
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(200, 30, 30)
            pdf.cell(0, 5, "RED FLAGS", ln=True)
            pdf.set_text_color(0, 0, 0)
            for rf in red_flags:
                bullet(rf)
        interventions = hyp.get("potential_interventions", [])
        if interventions:
            kv("Suggested Interventions", ", ".join(interventions))

    # Bridge note
    bridge = session.get("bridge_note")
    if bridge:
        section("Client Bridge Note")
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(60, 80, 110)
        pdf.multi_cell(0, 6, _s(bridge))
        pdf.set_text_color(0, 0, 0)

    # Footer
    pdf.ln(6)
    divider(200, 200, 200)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(160, 160, 160)
    pdf.cell(0, 5, f"Generated by ClinicalAI  ·  {datetime.now().strftime('%Y-%m-%d %H:%M')}", align="C")

    return bytes(pdf.output())
