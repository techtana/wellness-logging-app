/* ── App state ─────────────────────────────────────────── */
let appMode = 'client';

// Client session state
let sessionPrompts = [];
let sessionTurns = [];
let clientPromptIndex = 0;
let clientIsRecording = false;
let clientMediaRecorder = null;
let clientRecordingChunks = [];
let clientResponseRecorded = false;
let currentSessionId = null;

// Therapist / analysis state
let lastAnalysisData = null;
let currentKBId = null;
let kbLoaded = false;
let promptsData = [];
let promptsLoaded = false;
let editingPromptId = null;

const CATEGORY_LABELS = {
  opening:     'Opening',
  exploration: 'Exploration',
  coping:      'Coping',
  reflection:  'Reflection',
  closing:     'Closing',
  custom:      'Custom',
};

const EMOTION_ICONS = {
  Anxious: '😰', Depressed: '😔', Frustrated: '😤', Hopeful: '🌱',
  Happy: '😊', Angry: '😠', Worried: '😟', Confused: '😕',
  Calm: '😌', Embarrassed: '😳',
};

const KB_SECTION_CATEGORIES = {
  summary:  'clinical_report',
  emotions: 'sentiment',
  themes:   'themes',
  dynamics: 'dynamics',
  plan:     'clinical_report',
};

/* ── Init ──────────────────────────────────────────────── */
async function init() {
  await Promise.all([loadAISettings(), loadTranscriptionSettings()]);
  loadPromptsInBackground();
}

async function loadPromptsInBackground() {
  try {
    const res = await fetch('/api/v1/prompts');
    const data = await res.json();
    promptsData = data.prompts || [];
    promptsLoaded = true;
    renderPromptList();
    updateSessionTurnCount();
  } catch (e) {}
}

/* ── Mode toggle ───────────────────────────────────────── */
function setMode(newMode) {
  appMode = newMode;
  document.getElementById('clientView').classList.toggle('hidden', newMode !== 'client');
  document.getElementById('therapistView').classList.toggle('hidden', newMode !== 'therapist');
  document.getElementById('manageView').classList.toggle('hidden', newMode !== 'manage');
  document.getElementById('modeBtnClient').classList.toggle('active', newMode === 'client');
  document.getElementById('modeBtnTherapist').classList.toggle('active', newMode === 'therapist');
  document.getElementById('modeBtnManage').classList.toggle('active', newMode === 'manage');

  if (newMode === 'therapist') {
    loadSessionDropdown();
    updateSessionTurnsPreview();
    updateSessionTurnCount();
    ensureKBLoaded().then(() => loadKBSelectorsForTabs());
  }
  if (newMode === 'manage') {
    renderPromptList();
    ensureKBLoaded();
    if (!promptsLoaded) loadPromptsInBackground();
  }
}

/* ── Client session screens ────────────────────────────── */
function showClientScreen(name) {
  document.querySelectorAll('.client-screen').forEach(s => s.classList.remove('active'));
  const id = 'screen' + name.charAt(0).toUpperCase() + name.slice(1);
  document.getElementById(id).classList.add('active');
}

/* ── Start session ─────────────────────────────────────── */
async function startClientSession() {
  try {
    const res = await fetch('/api/v1/prompts/session');
    const data = await res.json();
    sessionPrompts = data.prompts || [];
  } catch (e) {
    sessionPrompts = [];
  }

  if (sessionPrompts.length === 0) {
    alert('No prompts available. Add prompts in the Manage view first.');
    return;
  }

  const sid = `session_${new Date().toISOString().replace(/[-:T.]/g, '').slice(0, 15)}`;
  currentSessionId = sid;
  fetch('/api/v1/sessions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sid }),
  }).catch(() => {});

  sessionTurns = [];
  clientPromptIndex = 0;
  showClientScreen('session');
  displayPrompt(sessionPrompts[0]);
}

function displayPrompt(prompt) {
  document.getElementById('promptCategory').textContent = CATEGORY_LABELS[prompt.category] || prompt.category;
  document.getElementById('promptText').textContent = prompt.rephrased_text || prompt.clinical_text;
  updateSessionDots();
  resetRecordState();
  clientResponseRecorded = false;
  document.getElementById('sessionNextBtn').disabled = true;
  setClientResponseOk(false);
  hideClientProcessing();
}

function updateSessionDots() {
  const dots = document.getElementById('sessionDots');
  dots.innerHTML = sessionPrompts.map((_, i) => {
    let cls = 'session-dot';
    if (i < clientPromptIndex) cls += ' done';
    else if (i === clientPromptIndex) cls += ' active';
    return `<div class="${cls}"></div>`;
  }).join('');
}

function resetRecordState() {
  if (clientIsRecording && clientMediaRecorder) {
    clientMediaRecorder.stop();
    clientIsRecording = false;
  }
  const btn = document.getElementById('clientRecordBtn');
  btn.classList.remove('recording');
  document.getElementById('iconMic').classList.remove('hidden');
  document.getElementById('iconStop').classList.add('hidden');
  document.getElementById('recordPulse').classList.remove('active');
  document.getElementById('clientRecordLabel').textContent = 'Tap to speak';
}

/* ── Client recording ──────────────────────────────────── */
async function toggleClientRecording() {
  if (clientIsRecording) {
    stopClientRecording();
  } else {
    await startClientRecording();
  }
}

async function startClientRecording() {
  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (err) {
    document.getElementById('clientRecordLabel').textContent = 'Microphone access denied';
    return;
  }
  clientRecordingChunks = [];
  clientMediaRecorder = new MediaRecorder(stream);
  clientMediaRecorder.ondataavailable = e => { if (e.data.size > 0) clientRecordingChunks.push(e.data); };
  clientMediaRecorder.onstop = async () => {
    stream.getTracks().forEach(t => t.stop());
    const blob = new Blob(clientRecordingChunks, { type: 'audio/webm' });
    await processClientRecording(blob);
  };
  clientMediaRecorder.start();
  clientIsRecording = true;

  document.getElementById('clientRecordBtn').classList.add('recording');
  document.getElementById('iconMic').classList.add('hidden');
  document.getElementById('iconStop').classList.remove('hidden');
  document.getElementById('recordPulse').classList.add('active');
  document.getElementById('clientRecordLabel').textContent = 'Recording… tap to stop';
}

function stopClientRecording() {
  if (clientMediaRecorder && clientIsRecording) {
    clientMediaRecorder.stop();
    clientIsRecording = false;
    document.getElementById('clientRecordBtn').classList.remove('recording');
    document.getElementById('iconMic').classList.remove('hidden');
    document.getElementById('iconStop').classList.add('hidden');
    document.getElementById('recordPulse').classList.remove('active');
    document.getElementById('clientRecordLabel').textContent = 'Tap to speak';
    showClientProcessing();
  }
}

async function processClientRecording(blob) {
  const prompt = sessionPrompts[clientPromptIndex];
  const audioFilename = `${prompt.id}.webm`;

  sessionTurns.push({
    timestamp: sessionTurns.length,
    speaker: 'therapist',
    text: prompt.rephrased_text || prompt.clinical_text,
    prompt_id: prompt.id,
  });

  let transcribedText = null;
  try {
    const form = new FormData();
    form.append('audio', blob, audioFilename);
    const res = await fetch('/api/v1/transcribe', { method: 'POST', body: form });
    if (res.ok) {
      const data = await res.json();
      transcribedText = data.text?.trim() || null;
    }
  } catch (err) {}

  if (transcribedText) {
    sessionTurns.push({
      timestamp: sessionTurns.length,
      speaker: 'client',
      text: transcribedText,
      prompt_id: prompt.id,
      audio_file: audioFilename,
    });
  }

  if (currentSessionId) {
    const audioForm = new FormData();
    audioForm.append('audio', blob, audioFilename);
    fetch(`/api/v1/sessions/${currentSessionId}/audio/${audioFilename}`, {
      method: 'POST',
      body: audioForm,
    }).catch(() => {});

    fetch(`/api/v1/sessions/${currentSessionId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ turns: sessionTurns }),
    }).catch(() => {});
  }

  hideClientProcessing();
  setClientResponseOk(true);
  clientResponseRecorded = true;
  document.getElementById('sessionNextBtn').disabled = false;
}

function showClientProcessing() {
  document.getElementById('clientProcessing').classList.remove('hidden');
  document.getElementById('clientRecordBtn').disabled = true;
}

function hideClientProcessing() {
  document.getElementById('clientProcessing').classList.add('hidden');
  document.getElementById('clientRecordBtn').disabled = false;
}

function setClientResponseOk(visible) {
  document.getElementById('clientResponseOk').classList.toggle('hidden', !visible);
}

function skipCurrentPrompt() {
  const prompt = sessionPrompts[clientPromptIndex];
  sessionTurns.push({
    timestamp: sessionTurns.length,
    speaker: 'therapist',
    text: prompt.rephrased_text || prompt.clinical_text,
    prompt_id: prompt.id,
    skipped: true,
  });
  goNextPrompt();
}

async function goNextPrompt() {
  clientPromptIndex++;
  if (clientPromptIndex >= sessionPrompts.length) {
    await endClientSession();
  } else {
    displayPrompt(sessionPrompts[clientPromptIndex]);
  }
}

async function endClientSession() {
  showClientScreen('bridge');
  document.getElementById('bridgeNoteText').innerHTML = '<div class="mini-spinner"></div>';
  updateSessionTurnsPreview();
  updateSessionTurnCount();

  let bridgeNote = 'Thank you for taking the time to reflect today. Each session is a step forward.';
  try {
    const res = await fetch('/api/v1/session/bridge', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ transcript: sessionTurns }),
    });
    if (res.ok) {
      const data = await res.json();
      bridgeNote = data.bridge_note || bridgeNote;
    }
  } catch (err) {}

  document.getElementById('bridgeNoteText').textContent = bridgeNote;

  if (currentSessionId) {
    try {
      await fetch(`/api/v1/sessions/${currentSessionId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          turns: sessionTurns,
          bridge_note: bridgeNote,
          status: 'complete',
        }),
      });
    } catch (e) {}
  }
  loadSessionDropdown();
}

function resetClientSession() {
  showClientScreen('welcome');
}

/* ── Therapist session dropdown ────────────────────────── */
async function loadSessionDropdown() {
  const sel = document.getElementById('sessionDropdown');
  if (!sel) return;
  try {
    const res = await fetch('/api/v1/sessions');
    const data = await res.json();
    const sessions = (data.sessions || []).filter(s => s.client_turns > 0 || s.status === 'complete');
    sel.innerHTML = '<option value="">Select a past session…</option>' +
      sessions.map(s => {
        const d = s.created_at ? new Date(s.created_at) : null;
        const dateStr = d ? d.toLocaleDateString('en', { month: 'short', day: 'numeric' }) +
          '  ' + d.toLocaleTimeString('en', { hour: '2-digit', minute: '2-digit' }) : '—';
        const turns = `${s.client_turns} response${s.client_turns !== 1 ? 's' : ''}`;
        const analyzed = s.has_analysis ? ' · analyzed' : '';
        const selected = s.session_id === currentSessionId ? ' selected' : '';
        return `<option value="${escHtml(s.session_id)}"${selected}>${dateStr} — ${turns}${analyzed}</option>`;
      }).join('');
    if (currentSessionId && sessionTurns.length === 0) {
      const found = sessions.find(s => s.session_id === currentSessionId);
      if (found) await _loadSessionTurns(currentSessionId);
    }
  } catch (e) {}
}

async function selectSessionFromDropdown(sessionId) {
  if (!sessionId) {
    sessionTurns = [];
    currentSessionId = null;
    lastAnalysisData = null;
    updateSessionTurnsPreview();
    updateSessionTurnCount();
    hideResults();
    document.getElementById('exportPdfBtn').classList.add('hidden');
    return;
  }
  await _loadSessionTurns(sessionId);
  lastAnalysisData = null;
  hideResults();
  document.getElementById('exportPdfBtn').classList.add('hidden');
}

async function _loadSessionTurns(sessionId) {
  try {
    const res = await fetch(`/api/v1/sessions/${sessionId}`);
    const session = await res.json();
    sessionTurns = session.turns || [];
    currentSessionId = sessionId;
    updateSessionTurnsPreview();
    updateSessionTurnCount();
  } catch (e) {}
}

/* ── Client history browser ────────────────────────────── */
async function openHistory() {
  showClientScreen('history');
  document.getElementById('historyList').innerHTML =
    '<div style="display:flex;justify-content:center;padding:40px"><div class="mini-spinner" style="width:24px;height:24px;border-width:3px"></div></div>';
  try {
    const res = await fetch('/api/v1/sessions');
    const data = await res.json();
    renderHistory(data.sessions || []);
  } catch (e) {
    document.getElementById('historyList').innerHTML =
      '<p class="muted-hint" style="text-align:center;padding:32px">Could not load sessions.</p>';
  }
}

function renderHistory(sessions) {
  const list = document.getElementById('historyList');
  if (sessions.length === 0) {
    list.innerHTML = '<p class="muted-hint" style="text-align:center;padding:40px">No sessions recorded yet.</p>';
    return;
  }

  list.innerHTML = sessions.map(s => {
    const date = s.created_at ? new Date(s.created_at).toLocaleString() : 'Unknown date';
    const statusBadge = s.status === 'complete'
      ? '<span class="hist-badge complete">Complete</span>'
      : '<span class="hist-badge in-progress">In progress</span>';
    const analysisBadge = s.has_analysis
      ? '<span class="hist-badge analyzed">Analyzed</span>' : '';

    return `
      <div class="hist-session" id="hist-${s.session_id}">
        <div class="hist-session-header" onclick="toggleHistorySession('${s.session_id}')">
          <div class="hist-session-meta">
            <div class="hist-session-id">${escHtml(s.session_id)}</div>
            <div class="hist-session-date">${date} · ${s.client_turns} response${s.client_turns !== 1 ? 's' : ''}</div>
            <div class="hist-badges">${statusBadge}${analysisBadge}</div>
          </div>
          <div class="hist-session-actions" onclick="event.stopPropagation()">
            <a class="btn-hist-action" href="/api/v1/sessions/${s.session_id}/transcript.txt" download>
              ↓ Transcript
            </a>
            ${s.has_analysis ? `<a class="btn-hist-action pdf" href="/api/v1/sessions/${s.session_id}/report.pdf" download>↓ PDF</a>` : ''}
            <button class="btn-hist-delete" onclick="deleteHistorySession('${s.session_id}')" title="Delete session">✕</button>
          </div>
        </div>
        <div class="hist-session-body hidden" id="hist-body-${s.session_id}">
          <div class="hist-loading">
            <div class="mini-spinner"></div>
          </div>
        </div>
      </div>`;
  }).join('');
}

async function toggleHistorySession(sessionId) {
  const body = document.getElementById(`hist-body-${sessionId}`);
  const isHidden = body.classList.contains('hidden');
  body.classList.toggle('hidden', !isHidden);
  if (isHidden && body.querySelector('.hist-loading')) {
    await loadHistorySession(sessionId, body);
  }
}

async function loadHistorySession(sessionId, bodyEl) {
  try {
    const res = await fetch(`/api/v1/sessions/${sessionId}`);
    const session = await res.json();
    const turns = session.turns || [];

    const items = turns.map((t, i) => {
      const cls = t.speaker === 'therapist' ? 'hist-turn-therapist' : 'hist-turn-client';
      const label = t.speaker === 'therapist' ? 'Prompt' : 'Response';
      const text = t.skipped ? '<em style="color:#9c7d65">(Skipped)</em>' : escHtml(t.text);
      const audioBtn = (t.speaker === 'client' && t.audio_file && !t.skipped)
        ? `<div class="hist-audio" id="audio-zone-${sessionId}-${i}">
             <button class="btn-hist-play" onclick="toggleAudio('${sessionId}', '${t.audio_file}', ${i})">▶ Play</button>
             <a class="btn-hist-action" href="/api/v1/sessions/${sessionId}/audio/${t.audio_file}" download>↓ Audio</a>
           </div>`
        : '';
      return `
        <div class="hist-turn ${cls}">
          <div class="hist-turn-label">${label}</div>
          <div class="hist-turn-text">${text}</div>
          ${audioBtn}
        </div>`;
    }).join('');

    const bridge = session.bridge_note
      ? `<div class="hist-bridge"><div class="hist-bridge-label">Closing Note</div>${escHtml(session.bridge_note)}</div>` : '';

    bodyEl.innerHTML = (items || '<p class="muted-hint">No turns recorded.</p>') + bridge;
  } catch (e) {
    bodyEl.innerHTML = '<p class="muted-hint" style="padding:12px">Failed to load session.</p>';
  }
}

function toggleAudio(sessionId, filename, turnIndex) {
  const zone = document.getElementById(`audio-zone-${sessionId}-${turnIndex}`);
  const existing = zone.querySelector('audio');
  if (existing) {
    existing.remove();
    zone.querySelector('.btn-hist-play').textContent = '▶ Play';
    return;
  }
  const audio = document.createElement('audio');
  audio.src = `/api/v1/sessions/${sessionId}/audio/${filename}`;
  audio.controls = true;
  audio.style.cssText = 'height:32px;margin-top:6px;width:100%;max-width:280px';
  zone.appendChild(audio);
  audio.play().catch(() => {});
  zone.querySelector('.btn-hist-play').textContent = '■ Close';
}

async function deleteHistorySession(sessionId) {
  if (!confirm(`Delete session "${sessionId}"? This cannot be undone.`)) return;
  try {
    await fetch(`/api/v1/sessions/${sessionId}`, { method: 'DELETE' });
    const el = document.getElementById(`hist-${sessionId}`);
    if (el) el.remove();
  } catch (e) {
    alert('Delete failed.');
  }
}

/* ── Analysis (therapist) ──────────────────────────────── */
async function analyze() {
  if (sessionTurns.length === 0) {
    showError('No session data. Switch to Client view and record a session first.');
    return;
  }
  const validTurns = sessionTurns.filter(t => t.text && !t.skipped);
  if (validTurns.length < 2) {
    showError('Not enough session content to analyze. Record at least two responses.');
    return;
  }

  const sessionId = currentSessionId || `session_${Date.now()}`;
  setLoading(true);
  hideResults();
  dismissError();

  try {
    const res = await fetch('/api/v1/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ transcript: validTurns, session_id: sessionId }),
    });
    const data = await res.json();
    if (!res.ok || data.status === 'error') {
      showError(data.message || data.error || 'Analysis failed.');
      return;
    }
    lastAnalysisData = data;
    renderResults(data);

    if (currentSessionId) {
      fetch(`/api/v1/sessions/${currentSessionId}/analysis`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      }).catch(() => {});
    }
  } catch (err) {
    showError('Could not reach the server. Make sure the API is running.');
  } finally {
    setLoading(false);
  }
}

/* ── Per-section re-analysis ───────────────────────────── */
async function reanalyzeSection(section, tabName) {
  if (!lastAnalysisData) {
    showError('Run a full analysis first before re-analyzing a section.');
    return;
  }
  const validTurns = sessionTurns.filter(t => t.text && !t.skipped);
  if (validTurns.length < 2) {
    showError('Not enough session content to analyze.');
    return;
  }

  const selectId = `kb-select-${tabName}`;
  const kbId = document.getElementById(selectId)?.value || '';

  const btn = document.querySelector(`#tab-${tabName} .btn-reanalyze`);
  if (btn) { btn.disabled = true; btn.textContent = '↻ Analyzing…'; }

  try {
    const body = {
      section,
      transcript: validTurns,
      kb_id: kbId || undefined,
      session_id: currentSessionId || 'unknown',
      patient_id: 'anonymous',
    };

    // For clinical_report, pass prior analysis context
    if (section === 'clinical_report' && lastAnalysisData) {
      const analysis = lastAnalysisData.analysis || {};
      body.sentiment  = analysis.sentiment_analysis || {};
      body.thematic   = analysis.thematic_analysis || {};
      body.relational = analysis.relational_dynamics || {};
    }

    const res = await fetch('/api/v1/analyze/section', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) {
      showError(data.error || 'Re-analysis failed.');
      return;
    }

    const result = data.result || {};

    // Patch lastAnalysisData and re-render the affected tab(s)
    if (section === 'sentiment') {
      lastAnalysisData.analysis = lastAnalysisData.analysis || {};
      lastAnalysisData.analysis.sentiment_analysis = result;
      renderEmotionsTab(result, lastAnalysisData.insight_report?.sections?.emotional_mapping || {});
    } else if (section === 'themes') {
      lastAnalysisData.analysis = lastAnalysisData.analysis || {};
      lastAnalysisData.analysis.thematic_analysis = result;
      renderThemesTab(lastAnalysisData.insight_report?.sections?.thematic_analysis || {}, result);
    } else if (section === 'dynamics') {
      lastAnalysisData.analysis = lastAnalysisData.analysis || {};
      lastAnalysisData.analysis.relational_dynamics = result;
      renderDynamicsTab(result, lastAnalysisData.insight_report?.sections?.relational_dynamics || {});
    } else if (section === 'clinical_report') {
      lastAnalysisData.insight_report = lastAnalysisData.insight_report || {};
      lastAnalysisData.insight_report.sections = result;
      const sentiment  = lastAnalysisData.analysis?.sentiment_analysis || {};
      const relational = lastAnalysisData.analysis?.relational_dynamics || {};
      renderSummaryTab(result, sentiment, relational);
      renderPlanTab(result.clinical_hypothesis || {}, result.recommendations || {});
    }
  } catch (err) {
    showError('Re-analysis failed. Check server connection.');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '↻ Re-analyze'; }
  }
}

/* ── KB selectors for analysis tabs ───────────────────── */
async function ensureKBLoaded() {
  if (kbLoaded && window._kbInstructions) return;
  try {
    const res = await fetch('/api/v1/kb/instructions');
    const data = await res.json();
    window._kbInstructions = data.instructions || [];
    renderKBList(window._kbInstructions);
    kbLoaded = true;
  } catch (e) {
    document.getElementById('kbList').innerHTML =
      '<p class="muted" style="padding:8px">Could not load instructions.</p>';
  }
}

function loadKBSelectorsForTabs() {
  const instructions = window._kbInstructions || [];
  const LABELS = {
    sentiment: 'Emotion Analysis', themes: 'Thematic Analysis',
    dynamics: 'Relational Dynamics', clinical_report: 'Clinical Report', custom: 'Custom',
  };

  Object.entries(KB_SECTION_CATEGORIES).forEach(([tabName, defaultCat]) => {
    const sel = document.getElementById(`kb-select-${tabName}`);
    if (!sel) return;
    const currentVal = sel.value;
    sel.innerHTML = '<option value="">Default</option>' +
      instructions.map(inst =>
        `<option value="${escHtml(inst.id)}" ${inst.id === currentVal ? 'selected' : ''}>` +
        `${escHtml(inst.name)} (${LABELS[inst.category] || inst.category})</option>`
      ).join('');
    // Pre-select the matching category instruction if no selection yet
    if (!currentVal) {
      const match = instructions.find(i => i.category === defaultCat && i.enabled);
      if (match) sel.value = match.id;
    }
  });
}

/* ── Report download ───────────────────────────────────── */
function downloadReport() {
  if (!currentSessionId) return;
  const a = document.createElement('a');
  a.href = `/api/v1/sessions/${currentSessionId}/report.pdf`;
  a.download = `report_${currentSessionId}.pdf`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

/* ── Render results ────────────────────────────────────── */
function renderResults(data) {
  const sections = data.insight_report?.sections || {};
  const analysis = data.analysis || {};
  const sentiment = analysis.sentiment_analysis || {};
  const relational = analysis.relational_dynamics || {};
  const thematic = analysis.thematic_analysis || {};

  renderSessionArc();
  renderSummaryTab(sections, sentiment, relational);
  renderEmotionsTab(sentiment, sections.emotional_mapping || {});
  renderThemesTab(sections.thematic_analysis || {}, thematic);
  renderDynamicsTab(relational, sections.relational_dynamics || {});
  renderPlanTab(sections.clinical_hypothesis || {}, sections.recommendations || {});

  document.getElementById('aiEnhancedTag').classList.toggle('hidden', !data.ai_enhanced);
  const pdfBtn = document.getElementById('exportPdfBtn');
  pdfBtn.classList.toggle('hidden', !currentSessionId);

  showResults();
  switchTabById('summary');

  // Populate KB selectors in case they changed
  ensureKBLoaded().then(() => loadKBSelectorsForTabs());
}

function renderSessionArc() {
  const card = document.getElementById('sessionArcCard');
  if (sessionTurns.length === 0) { card.style.display = 'none'; return; }

  const items = sessionTurns.map(t => {
    const cls = t.speaker === 'therapist' ? 'arc-therapist' : 'arc-client';
    const label = t.speaker === 'therapist' ? 'Prompt' : 'Response';
    const text = t.skipped ? '<em style="color:var(--text-muted)">Skipped</em>' : escHtml(t.text);
    return `
      <div class="arc-item ${cls}">
        <div class="arc-label">${label}</div>
        <div class="arc-text">${text}</div>
      </div>`;
  }).join('');

  card.style.display = '';
  card.innerHTML = `<div class="card-title">Session Arc</div><div class="arc-list">${items}</div>`;
}

function escHtml(s) {
  return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

/* ── Summary tab ───────────────────────────────────────── */
function renderSummaryTab(sections, sentiment, relational) {
  const exec = sections.executive_summary || {};
  const summary = sentiment.summary || {};
  const alliance = relational.therapeutic_alliance || {};

  const statRow = document.getElementById('statRow');
  statRow.innerHTML = '';
  statRow.appendChild(makeStat('Dominant Emotion', summary.overall_sentiment || '—', `avg intensity ${Number(summary.average_intensity || 0).toFixed(0)}`));
  statRow.appendChild(makeStat('Stability', summary.emotional_stability || '—'));
  statRow.appendChild(makeStat('Alliance', alliance.rating || '—'));
  statRow.appendChild(makeStat('Emotional Shifts', (sentiment.significant_shifts || []).length, 'detected'));

  document.getElementById('toneCard').innerHTML = `
    <div class="card-title">Tone Trajectory</div>
    <p style="font-size:14px;line-height:1.6;color:var(--text)">${exec.overall_tone_trajectory || '—'}</p>
  `;

  const takeaways = exec.key_takeaways || [];
  const focus = exec.priority_focus_area;
  document.getElementById('takeawaysCard').innerHTML = `
    <div class="card-title">Key Takeaways</div>
    <div class="insight-list">
      ${takeaways.map(t => `<div class="insight-item"><div class="insight-dot"></div><span>${escHtml(t)}</span></div>`).join('')}
      ${focus ? `<div class="insight-item" style="margin-top:8px;padding-top:8px;border-top:1px solid var(--border)">
        <div class="insight-dot" style="background:var(--warn)"></div>
        <span><strong>Priority:</strong> ${escHtml(focus)}</span>
      </div>` : ''}
    </div>
  `;
}

/* ── Emotions tab ──────────────────────────────────────── */
function renderEmotionsTab(sentiment, emotionMapping) {
  const summary = sentiment.summary || {};
  const points = sentiment.emotion_points || [];
  const shifts = sentiment.significant_shifts || [];

  const dist = summary.emotion_distribution || {};
  const total = Object.values(dist).reduce((a, b) => a + b, 0) || 1;
  const distItems = Object.entries(dist)
    .sort((a, b) => b[1] - a[1])
    .map(([emotion, count]) => {
      const pct = Math.round((count / total) * 100);
      return `
        <div style="margin-bottom:10px">
          <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:4px">
            <span>${EMOTION_ICONS[emotion] || ''} ${emotion}</span>
            <span style="color:var(--text-muted)">${pct}%</span>
          </div>
          <div style="height:6px;background:var(--border);border-radius:3px;overflow:hidden">
            <div style="height:100%;width:${pct}%;background:var(--primary);border-radius:3px;transition:width .5s ease"></div>
          </div>
        </div>`;
    }).join('');

  document.getElementById('emotionSummaryCard').innerHTML = `
    <div class="card-title">Emotion Distribution</div>
    ${distItems || '<p class="muted">No emotions detected.</p>'}
  `;

  // Explanation card
  const explanation = summary.explanation;
  const explCard = document.getElementById('emotionExplanationCard');
  if (explanation) {
    explCard.innerHTML = `
      <div class="card-title">Clinical Interpretation</div>
      <div class="analysis-explanation">${escHtml(explanation)}</div>
    `;
  } else {
    explCard.innerHTML = '';
  }

  const trajItems = points.slice(0, 20).map((p, i) => `
    <div class="traj-item">
      <div class="traj-dot">${EMOTION_ICONS[p.emotion] || '●'}</div>
      <span>${i + 1}</span>
    </div>`).join('');

  document.getElementById('emotionTrajectoryCard').innerHTML = `
    <div class="card-title">Emotional Trajectory</div>
    ${points.length ? `<div class="trajectory">${trajItems}</div>
      <p style="margin-top:10px;font-size:12px;color:var(--text-muted)">Showing first ${Math.min(20,points.length)} of ${points.length} turns</p>`
    : '<p class="muted">Not enough data.</p>'}
  `;

  const shiftItems = shifts.slice(0, 5).map(s => `
    <div class="distortion-row">
      <span>${EMOTION_ICONS[s.from_emotion] || ''} ${s.from_emotion} → ${EMOTION_ICONS[s.to_emotion] || ''} ${s.to_emotion}</span>
      <span class="muted" style="font-size:12px">±${s.magnitude} pts</span>
    </div>`).join('');

  document.getElementById('emotionShiftsCard').innerHTML = `
    <div class="card-title">Significant Shifts</div>
    ${shiftItems || '<p class="muted">No significant shifts detected.</p>'}
  `;
}

/* ── Themes tab ────────────────────────────────────────── */
function renderThemesTab(reportThematic, rawThematic) {
  const dominant = reportThematic.dominant_themes || [];
  const underlying = reportThematic.underlying_themes || [];
  const distortions = rawThematic.cognitive_distortions || [];

  const themeItems = [
    ...dominant.map(t => `<span class="tag">${escHtml(t)}</span>`),
    ...underlying.map(t => `<span class="tag" style="opacity:.7">${escHtml(t)}</span>`),
  ].join('');

  document.getElementById('themesCard').innerHTML = `
    <div class="card-title">Identified Themes</div>
    ${themeItems ? `<div class="tag-group">${themeItems}</div>` : '<p class="muted">No themes identified.</p>'}
  `;

  const distItems = distortions.slice(0, 8).map(d => `
    <div class="distortion-row">
      <span style="font-size:13px">${escHtml(d.distortion_type)}</span>
      <span class="severity-badge severity-${(d.severity || 'moderate').toLowerCase()}">${d.severity || 'Moderate'}</span>
    </div>`).join('');

  document.getElementById('distortionsCard').innerHTML = `
    <div class="card-title">Cognitive Distortions</div>
    ${distItems || '<p class="muted">No cognitive distortions detected.</p>'}
  `;

  // Clinical significance card
  const sig = rawThematic.clinical_significance;
  const sigCard = document.getElementById('clinicalSignificanceCard');
  if (sig) {
    sigCard.innerHTML = `
      <div class="card-title">Clinical Significance</div>
      <div class="analysis-explanation">${escHtml(sig)}</div>
    `;
  } else {
    sigCard.innerHTML = '';
  }
}

/* ── Dynamics tab ──────────────────────────────────────── */
function renderDynamicsTab(relational, reportDynamics) {
  const alliance = relational.therapeutic_alliance || {};
  const components = alliance.components || {};
  const profiles = relational.speaker_profiles || {};
  const events = relational.relational_events || [];

  const score = Object.values(components).reduce((a, b) => a + b, 0) / Math.max(Object.keys(components).length, 1);
  const compBars = Object.entries(components).map(([name, val]) => `
    <div style="margin-bottom:8px">
      <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:3px">
        <span style="text-transform:capitalize">${name}</span>
        <span style="color:var(--text-muted)">${Math.round(val)}%</span>
      </div>
      <div style="height:5px;background:var(--border);border-radius:3px;overflow:hidden">
        <div style="height:100%;width:${Math.round(val)}%;background:var(--primary);border-radius:3px"></div>
      </div>
    </div>`).join('');

  document.getElementById('allianceCard').innerHTML = `
    <div class="card-title">Therapeutic Alliance — <span style="color:var(--primary)">${alliance.rating || '—'}</span></div>
    <div class="alliance-meter">
      <div class="alliance-bar-wrap"><div class="alliance-bar" style="width:${Math.round(score)}%"></div></div>
      <div class="alliance-labels"><span>Weak</span><span>Strong</span></div>
    </div>
    <div style="margin-top:14px">${compBars}</div>
  `;

  // Alliance interpretation card
  const interp = alliance.interpretation;
  const interpCard = document.getElementById('allianceInterpCard');
  if (interp) {
    interpCard.innerHTML = `
      <div class="card-title">Alliance Interpretation</div>
      <div class="analysis-explanation">${escHtml(interp)}</div>
    `;
  } else {
    interpCard.innerHTML = '';
  }

  const speakerRows = Object.entries(profiles).map(([name, info]) => {
    const cls = name.toLowerCase().includes('therapist') ? 'therapist' : 'client';
    return `
      <div class="speaker-row">
        <div class="speaker-avatar ${cls}">${name.slice(0, 2).toUpperCase()}</div>
        <div class="speaker-info">
          <div class="speaker-name" style="text-transform:capitalize">${name}</div>
          <div class="speaker-meta">${info.word_count || 0} words${info.style ? ` · <span class="speaker-style">${info.style}</span>` : ''}</div>
        </div>
      </div>`;
  }).join('');

  document.getElementById('speakerCard').innerHTML = `
    <div class="card-title">Speaker Profiles</div>
    ${speakerRows || '<p class="muted">No speaker data.</p>'}
  `;

  const dominantDynamic = relational.dominant_dynamic;
  const eventItems = events.slice(0, 5).map(e => `
    <div class="insight-item">
      <div class="insight-dot" style="background:var(--client)"></div>
      <span><strong>${escHtml(e.event_type)}</strong>${e.context ? ` — ${escHtml(e.context.slice(0, 80))}${e.context.length > 80 ? '…' : ''}` : ''}</span>
    </div>`).join('');

  document.getElementById('eventsCard').innerHTML = `
    <div class="card-title">Relational Events${dominantDynamic ? ` — <span style="color:var(--primary)">${escHtml(dominantDynamic)}</span>` : ''}</div>
    <div class="insight-list">${eventItems || '<p class="muted">No significant relational events detected.</p>'}</div>
  `;
}

/* ── Plan tab ──────────────────────────────────────────── */
function renderPlanTab(hypothesis, recommendations) {
  const immediate = recommendations.immediate_actions || [];
  const nextSession = recommendations.next_session_focus;
  const monitoring = recommendations.monitoring_points || [];
  const redFlags = recommendations.red_flags || [];

  const recItems = [
    ...immediate.map(a => `<div class="insight-item"><div class="insight-dot"></div><span>${escHtml(a)}</span></div>`),
    nextSession ? `<div class="insight-item"><div class="insight-dot" style="background:var(--warn)"></div><span><strong>Next session:</strong> ${escHtml(nextSession)}</span></div>` : '',
    ...monitoring.map(m => `<div class="insight-item"><div class="insight-dot" style="background:var(--client)"></div><span>${escHtml(m)}</span></div>`),
    ...redFlags.map(r => `<div class="insight-item"><div class="insight-dot" style="background:var(--danger)"></div><span style="color:var(--danger)">${escHtml(r)}</span></div>`),
  ].join('');

  document.getElementById('recommendCard').innerHTML = `
    <div class="card-title">Clinical Recommendations</div>
    <div class="insight-list">${recItems || '<p class="muted">No recommendations.</p>'}</div>
  `;

  const interventions = hypothesis.potential_interventions || [];
  const approaches = hypothesis.therapeutic_approaches || [];
  const allInterv = [
    ...interventions.map(i => `<span class="tag">${escHtml(i)}</span>`),
    ...approaches.map(a => `<span class="tag green">${escHtml(a)}</span>`),
  ].join('');

  document.getElementById('interventionsCard').innerHTML = `
    <div class="card-title">Suggested Interventions</div>
    ${allInterv ? `<div class="tag-group">${allInterv}</div>` : '<p class="muted">No specific interventions suggested.</p>'}
  `;

  const prompts = hypothesis.journaling_prompts || [];
  const promptItems = prompts.map((p, i) => `
    <div style="padding:10px 12px;background:#f8fafc;border-radius:7px;border-left:3px solid var(--primary);font-size:13px;line-height:1.5">
      <span style="font-size:11px;font-weight:700;color:var(--text-muted);display:block;margin-bottom:3px">PROMPT ${i + 1}</span>
      ${escHtml(p)}
    </div>`).join('');

  document.getElementById('journalingCard').innerHTML = `
    <div class="card-title">Journaling Prompts</div>
    <div style="display:flex;flex-direction:column;gap:8px">${promptItems || '<p class="muted">No prompts generated.</p>'}</div>
  `;
}

/* ── Manage view ───────────────────────────────────────── */
function switchManagePanel(panel) {
  document.querySelectorAll('.manage-nav-item').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.manage-panel').forEach(el => el.classList.remove('active'));
  document.getElementById(`manageNav${panel.charAt(0).toUpperCase() + panel.slice(1)}`).classList.add('active');
  document.getElementById(`manage-panel-${panel}`).classList.add('active');
  if (panel === 'kb') {
    ensureKBLoaded();
  }
}

/* ── Prompt library ────────────────────────────────────── */
function renderPromptList() {
  const list = document.getElementById('promptList');
  if (!list) return;
  if (!promptsData.length) {
    list.innerHTML = '<p class="muted-hint">No prompts. Click + New Prompt.</p>';
    return;
  }
  const sorted = [...promptsData].sort((a, b) => (a.order || 999) - (b.order || 999));
  list.innerHTML = sorted.map(p => `
    <div class="prompt-item" onclick="editPrompt('${p.id}')">
      <div class="prompt-item-dot ${p.enabled ? 'enabled' : 'disabled'}"></div>
      <div class="prompt-item-info">
        <div class="prompt-item-text">${escHtml(p.rephrased_text.length > 55 ? p.rephrased_text.slice(0, 55) + '…' : p.rephrased_text)}</div>
        <div class="prompt-item-cat">${CATEGORY_LABELS[p.category] || p.category}</div>
      </div>
      <button class="prompt-item-edit" title="Edit">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
        </svg>
      </button>
    </div>`).join('');
}

function newPrompt() {
  editingPromptId = null;
  document.getElementById('promptEditTitle').textContent = 'New Prompt';
  document.getElementById('peCategory').value = 'opening';
  document.getElementById('peClinical').value = '';
  document.getElementById('peRephrased').value = '';
  document.getElementById('peOrder').value = (promptsData.length + 1).toString();
  document.getElementById('peEnabled').checked = true;
  document.getElementById('peDeleteBtn').style.display = 'none';
  document.getElementById('promptEditModal').classList.remove('hidden');
}

function editPrompt(id) {
  const p = promptsData.find(x => x.id === id);
  if (!p) return;
  editingPromptId = id;
  document.getElementById('promptEditTitle').textContent = 'Edit Prompt';
  document.getElementById('peCategory').value = p.category;
  document.getElementById('peClinical').value = p.clinical_text;
  document.getElementById('peRephrased').value = p.rephrased_text;
  document.getElementById('peOrder').value = (p.order || 1).toString();
  document.getElementById('peEnabled').checked = p.enabled !== false;
  document.getElementById('peDeleteBtn').style.display = '';
  document.getElementById('promptEditModal').classList.remove('hidden');
}

function closePromptEdit() {
  document.getElementById('promptEditModal').classList.add('hidden');
  editingPromptId = null;
}

function handlePromptModalClick(e) {
  if (e.target === document.getElementById('promptEditModal')) closePromptEdit();
}

async function savePrompt() {
  const clinical_text = document.getElementById('peClinical').value.trim();
  const rephrased_text = document.getElementById('peRephrased').value.trim();
  if (!clinical_text) { alert('Clinical question is required.'); return; }
  if (!rephrased_text) { alert('Client-facing text is required.'); return; }

  const payload = {
    category: document.getElementById('peCategory').value,
    clinical_text,
    rephrased_text,
    order: parseInt(document.getElementById('peOrder').value) || 1,
    enabled: document.getElementById('peEnabled').checked,
  };

  try {
    let res;
    if (editingPromptId) {
      res = await fetch(`/api/v1/prompts/${editingPromptId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
    } else {
      res = await fetch('/api/v1/prompts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
    }
    const data = await res.json();
    if (!res.ok) { alert(data.error || 'Save failed.'); return; }
    promptsLoaded = false;
    await loadPromptsInBackground();
    closePromptEdit();
  } catch (e) {
    alert('Save failed. Is the server running?');
  }
}

async function deleteCurrentPrompt() {
  if (!editingPromptId || !confirm('Delete this prompt?')) return;
  try {
    const res = await fetch(`/api/v1/prompts/${editingPromptId}`, { method: 'DELETE' });
    if (res.ok) {
      promptsLoaded = false;
      await loadPromptsInBackground();
      closePromptEdit();
    }
  } catch (e) {
    alert('Delete failed.');
  }
}

async function resetPrompts() {
  if (!confirm('Reset all prompts to defaults? Custom prompts will be removed.')) return;
  try {
    const res = await fetch('/api/v1/prompts/reset', { method: 'POST' });
    const data = await res.json();
    promptsData = data.prompts || [];
    promptsLoaded = true;
    renderPromptList();
  } catch (e) {
    alert('Reset failed.');
  }
}

async function rephraseCurrentPrompt() {
  const clinical_text = document.getElementById('peClinical').value.trim();
  if (!clinical_text) { alert('Enter the clinical question first.'); return; }
  const btn = document.getElementById('rephraseBtn');
  btn.disabled = true;
  btn.textContent = 'Rephrasing…';
  try {
    const res = await fetch('/api/v1/prompts/rephrase', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ clinical_text }),
    });
    if (res.ok) {
      const data = await res.json();
      document.getElementById('peRephrased').value = data.rephrased_text || '';
    } else {
      const data = await res.json();
      alert(data.error || 'Rephrase failed.');
    }
  } catch (e) {
    alert('Rephrase failed. Check AI provider settings.');
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:13px;height:13px"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg> AI rephrase`;
  }
}

/* ── Session turns preview ─────────────────────────────── */
function updateSessionTurnsPreview() {
  const preview = document.getElementById('sessionTurnsPreview');
  if (!preview) return;
  if (sessionTurns.length === 0) {
    preview.innerHTML = '<p class="muted-hint">Switch to Client view to record a session.</p>';
    return;
  }
  const items = sessionTurns.map(t => {
    const cls = t.speaker === 'therapist' ? 'preview-therapist' : 'preview-client';
    const short = t.skipped ? 'Skipped' : (t.text.length > 60 ? t.text.slice(0, 60) + '…' : t.text);
    return `<div class="preview-turn ${cls}">${escHtml(short)}</div>`;
  }).join('');
  preview.innerHTML = items;
}

function updateSessionTurnCount() {
  const el = document.getElementById('sessionTurnCount');
  if (!el) return;
  const count = sessionTurns.filter(t => !t.skipped).length;
  el.textContent = `${count} turn${count !== 1 ? 's' : ''}`;
}

function clearAll() {
  sessionTurns = [];
  sessionPrompts = [];
  currentSessionId = null;
  lastAnalysisData = null;
  const dd = document.getElementById('sessionDropdown');
  if (dd) dd.value = '';
  updateSessionTurnsPreview();
  updateSessionTurnCount();
  hideResults();
  document.getElementById('exportPdfBtn').classList.add('hidden');
}

/* ── Knowledge Base ────────────────────────────────────── */
async function loadKBInstructions() {
  await ensureKBLoaded();
}

function renderKBList(instructions) {
  const list = document.getElementById('kbList');
  if (!list) return;
  const LABELS = {
    sentiment: 'Emotion Analysis', themes: 'Thematic Analysis',
    dynamics: 'Relational Dynamics', clinical_report: 'Clinical Report', custom: 'Custom'
  };
  list.innerHTML = instructions.map(inst => `
    <div class="kb-item ${inst.id === currentKBId ? 'selected' : ''}" onclick="selectInstruction('${inst.id}')">
      <div class="kb-item-dot ${inst.enabled ? 'enabled' : 'disabled'}"></div>
      <div class="kb-item-info">
        <div class="kb-item-name">${escHtml(inst.name)}</div>
        <div class="kb-item-cat">${LABELS[inst.category] || inst.category}</div>
      </div>
    </div>`).join('');
  window._kbInstructions = instructions;
}

async function selectInstruction(id) {
  currentKBId = id;
  const inst = (window._kbInstructions || []).find(i => i.id === id);
  if (!inst) return;
  document.getElementById('kbEditorPlaceholder').classList.add('hidden');
  document.getElementById('kbEditorForm').classList.remove('hidden');
  setEl('kbName', inst.name);
  setEl('kbCategory', inst.category);
  document.getElementById('kbPrompt').value = inst.prompt;
  document.getElementById('kbEnabled').checked = inst.enabled;
  renderKBList(window._kbInstructions || []);
  await loadKBFiles(id);
}

function newInstruction() {
  currentKBId = null;
  document.getElementById('kbEditorPlaceholder').classList.add('hidden');
  document.getElementById('kbEditorForm').classList.remove('hidden');
  setEl('kbName', '');
  setEl('kbCategory', 'custom');
  document.getElementById('kbPrompt').value = '';
  document.getElementById('kbEnabled').checked = true;
  document.querySelectorAll('.kb-item').forEach(el => el.classList.remove('selected'));
  document.getElementById('kbFileList').innerHTML = '<p class="muted-hint" id="kbFilesEmpty">No files attached.</p>';
}

async function saveInstruction() {
  const name = getEl('kbName').trim();
  const category = getEl('kbCategory');
  const prompt = document.getElementById('kbPrompt').value.trim();
  const enabled = document.getElementById('kbEnabled').checked;
  if (!name || !prompt) { alert('Name and instructions are required.'); return; }
  try {
    let res;
    if (currentKBId) {
      res = await fetch(`/api/v1/kb/instructions/${currentKBId}`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, category, prompt, enabled }),
      });
    } else {
      res = await fetch('/api/v1/kb/instructions', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, category, prompt }),
      });
    }
    const data = await res.json();
    if (!res.ok) { alert(data.error || 'Save failed.'); return; }
    currentKBId = data.id;
    kbLoaded = false;
    await ensureKBLoaded();
    await selectInstruction(data.id);
  } catch (e) { alert('Save failed.'); }
}

async function deleteInstruction() {
  if (!currentKBId || !confirm('Delete this instruction?')) return;
  try {
    const res = await fetch(`/api/v1/kb/instructions/${currentKBId}`, { method: 'DELETE' });
    if (res.ok) {
      currentKBId = null;
      document.getElementById('kbEditorPlaceholder').classList.remove('hidden');
      document.getElementById('kbEditorForm').classList.add('hidden');
      kbLoaded = false;
      await ensureKBLoaded();
    }
  } catch (e) { alert('Delete failed.'); }
}

async function resetKB() {
  if (!confirm('Reset all knowledge base instructions to defaults?')) return;
  try {
    const res = await fetch('/api/v1/kb/reset', { method: 'POST' });
    const data = await res.json();
    currentKBId = null;
    document.getElementById('kbEditorPlaceholder').classList.remove('hidden');
    document.getElementById('kbEditorForm').classList.add('hidden');
    renderKBList(data.instructions || []);
    kbLoaded = true;
  } catch (e) { alert('Reset failed.'); }
}

/* ── KB File Attachments ───────────────────────────────── */
async function loadKBFiles(instId) {
  const listEl = document.getElementById('kbFileList');
  if (!listEl || !instId) return;
  try {
    const res = await fetch(`/api/v1/kb/instructions/${instId}/files`);
    const data = await res.json();
    renderKBFiles(data.files || []);
  } catch (e) {
    listEl.innerHTML = '<p class="muted-hint">Could not load files.</p>';
  }
}

function renderKBFiles(files) {
  const listEl = document.getElementById('kbFileList');
  if (!listEl) return;
  if (!files.length) {
    listEl.innerHTML = '<p class="muted-hint" id="kbFilesEmpty">No files attached.</p>';
    return;
  }
  listEl.innerHTML = files.map(f => `
    <div class="kb-file-chip">
      <span class="kb-file-icon">${f.file_type === 'pdf' ? '📄' : '📝'}</span>
      <span class="kb-file-name">${escHtml(f.filename)}</span>
      <button class="kb-file-delete" onclick="deleteKBFile('${escHtml(f.filename)}')" title="Remove">✕</button>
    </div>`).join('');
}

async function uploadKBFile(input) {
  if (!currentKBId) { alert('Save the instruction first, then attach files.'); input.value = ''; return; }
  const file = input.files[0];
  if (!file) return;
  const form = new FormData();
  form.append('file', file, file.name);
  input.value = '';
  try {
    const res = await fetch(`/api/v1/kb/instructions/${currentKBId}/files`, {
      method: 'POST', body: form,
    });
    const data = await res.json();
    if (!res.ok) { alert(data.error || 'Upload failed.'); return; }
    await loadKBFiles(currentKBId);
  } catch (e) { alert('Upload failed.'); }
}

async function deleteKBFile(filename) {
  if (!currentKBId || !confirm(`Remove "${filename}"?`)) return;
  try {
    const res = await fetch(`/api/v1/kb/instructions/${currentKBId}/files/${encodeURIComponent(filename)}`, {
      method: 'DELETE',
    });
    if (res.ok) await loadKBFiles(currentKBId);
  } catch (e) { alert('Delete failed.'); }
}

/* ── Settings Modal ────────────────────────────────────── */
async function loadAISettings() {
  try {
    const res = await fetch('/api/v1/settings/ai');
    applyAISettings(await res.json());
  } catch (e) {}
}

async function loadTranscriptionSettings() {
  try {
    const res = await fetch('/api/v1/settings/transcription');
    applyTranscriptionSettings(await res.json());
  } catch (e) {}
}

function applyAISettings(data) {
  const prov = data.provider || 'none';
  setEl('aiProvider', prov);

  const claude = data.claude || {};
  if (claude.api_key) setEl('claudeApiKey', claude.api_key);
  setEl('claudeModel', claude.model || 'claude-sonnet-4-6');

  const openai = data.openai || {};
  if (openai.api_key) setEl('openaiApiKey', openai.api_key);
  setEl('openaiModel', openai.model || 'gpt-4o');

  const ollama = data.ollama || {};
  setEl('ollamaHost', ollama.host || 'http://localhost:11434');
  setEl('ollamaModel', ollama.model || 'llama3.2');

  updateAIProviderUI();

  const badge = document.getElementById('aiBadgeBar');
  if (prov !== 'none') {
    badge.textContent = `AI: ${prov}`;
    badge.className = 'ai-badge active';
  } else {
    badge.textContent = 'AI: off';
    badge.className = 'ai-badge inactive';
  }
}

function applyTranscriptionSettings(data) {
  const prov = data.provider || 'none';
  setEl('transcriptionProvider', prov);

  const wl = data.whisper_local || {};
  setEl('whisperModel', wl.model_size || 'large-v3-turbo');
  setEl('whisperDevice', wl.device || 'auto');

  const ot = data.openai || {};
  if (ot.api_key) setEl('openaiTransKey', ot.api_key);

  updateTranscriptionUI();

  const badge = document.getElementById('transcriptionBadge');
  if (badge) {
    if (prov !== 'none') {
      badge.textContent = prov === 'whisper_local' ? 'whisper' : prov;
      badge.className = 'ai-badge active';
    } else {
      badge.textContent = 'trans: off';
      badge.className = 'ai-badge inactive';
    }
  }
}

function openSettings() { document.getElementById('settingsModal').classList.remove('hidden'); }
function closeSettings() { document.getElementById('settingsModal').classList.add('hidden'); }
function handleModalOverlayClick(e) {
  if (e.target === document.getElementById('settingsModal')) closeSettings();
}

function updateAIProviderUI() {
  const prov = document.getElementById('aiProvider').value;
  document.getElementById('claudeSettings').classList.toggle('hidden', prov !== 'claude');
  document.getElementById('openaiSettings').classList.toggle('hidden', prov !== 'openai');
  document.getElementById('ollamaSettings').classList.toggle('hidden', prov !== 'ollama');
}

function updateTranscriptionUI() {
  const prov = document.getElementById('transcriptionProvider').value;
  document.getElementById('whisperLocalSettings').classList.toggle('hidden', prov !== 'whisper_local');
  document.getElementById('openaiTransSettings').classList.toggle('hidden', prov !== 'openai');
}

async function saveSettings() {
  const aiPayload = {
    provider: getEl('aiProvider'),
    claude: { api_key: getEl('claudeApiKey'), model: getEl('claudeModel') },
    openai: { api_key: getEl('openaiApiKey'), model: getEl('openaiModel') },
    ollama: { host: getEl('ollamaHost'), model: getEl('ollamaModel') },
  };
  const transPayload = {
    provider: getEl('transcriptionProvider'),
    whisper_local: { model_size: getEl('whisperModel'), device: getEl('whisperDevice') },
    openai: { api_key: getEl('openaiTransKey') },
  };
  try {
    const [aiRes, transRes] = await Promise.all([
      fetch('/api/v1/settings/ai', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(aiPayload) }),
      fetch('/api/v1/settings/transcription', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(transPayload) }),
    ]);
    applyAISettings(await aiRes.json());
    applyTranscriptionSettings(await transRes.json());
    closeSettings();
  } catch (err) {
    alert('Failed to save settings. Is the server running?');
  }
}

/* ── Helpers ───────────────────────────────────────────── */
function makeStat(label, value, sub = '') {
  const el = document.createElement('div');
  el.className = 'stat';
  el.innerHTML = `
    <div class="stat-label">${label}</div>
    <div class="stat-value">${value}</div>
    ${sub ? `<div class="stat-sub">${sub}</div>` : ''}
  `;
  return el;
}

function switchTab(btn) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  btn.classList.add('active');
  document.getElementById(`tab-${btn.dataset.tab}`).classList.add('active');
}

function switchTabById(id) {
  const btn = document.querySelector(`.tab[data-tab="${id}"]`);
  if (btn) switchTab(btn);
}

function setLoading(on) {
  const btn = document.getElementById('analyzeBtn');
  btn.disabled = on;
  document.getElementById('analyzeBtnText').textContent = on ? 'Analyzing…' : 'Analyze Session';
  document.getElementById('analyzeSpinner').classList.toggle('hidden', !on);
}

function showResults() {
  document.getElementById('splash').classList.add('hidden');
  document.getElementById('results').classList.remove('hidden');
}

function hideResults() {
  document.getElementById('results').classList.add('hidden');
  document.getElementById('splash').classList.remove('hidden');
}

function showError(msg) {
  document.getElementById('errorMsg').textContent = msg;
  document.getElementById('errorBanner').classList.remove('hidden');
}

function dismissError() {
  document.getElementById('errorBanner').classList.add('hidden');
}

function getEl(id) { const el = document.getElementById(id); return el ? el.value : ''; }
function setEl(id, val) { const el = document.getElementById(id); if (el) el.value = val; }

/* ── Bootstrap ─────────────────────────────────────────── */
init();
