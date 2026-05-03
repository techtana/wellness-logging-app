/* ── State ────────────────────────────────────────────── */
let turnCount = 0;

const DEMO = [
  { speaker: 'therapist', text: "Hello, how have you been feeling since our last session?" },
  { speaker: 'client',    text: "Honestly, not great. I've been really anxious, especially at work. I always feel like I'm going to fail somehow." },
  { speaker: 'therapist', text: "I hear you. What does that anxiety feel like for you day to day?" },
  { speaker: 'client',    text: "Like a constant dread. I wake up and immediately start worrying. I'm scared my boss thinks I'm incompetent. He never says anything but I can tell he's disappointed in me." },
  { speaker: 'therapist', text: "It sounds like you're reading a lot into his silence. What evidence do you have that he's disappointed?" },
  { speaker: 'client',    text: "I don't know… none really. But I always assume the worst. It's like every mistake I make proves I'm a failure. I should be better by now." },
  { speaker: 'therapist', text: "That pattern of thinking — where one setback defines your entire worth — is something we can work with together. How does that land with you?" },
  { speaker: 'client',    text: "It makes sense when you put it that way. I'm grateful you help me see it differently. I just wish I could stay calm more often." },
];

const EMOTION_ICONS = {
  Anxious: '😰', Depressed: '😔', Frustrated: '😤', Hopeful: '🌱',
  Happy: '😊', Angry: '😠', Worried: '😟', Confused: '😕',
  Calm: '😌', Embarrassed: '😳',
};

/* ── Turn builder ─────────────────────────────────────── */
function addTurn(speaker, text = '') {
  turnCount++;
  const id = `turn-${turnCount}`;
  const list = document.getElementById('turns');
  const el = document.createElement('div');
  el.className = 'turn';
  el.dataset.speaker = speaker;
  el.id = id;
  el.innerHTML = `
    <div class="turn-header">
      <span class="turn-badge">${speaker}</span>
      <button class="turn-delete" title="Remove" onclick="removeTurn('${id}')">&#x2715;</button>
    </div>
    <textarea placeholder="Enter ${speaker} speech…" rows="2">${text}</textarea>
  `;
  list.appendChild(el);
  el.querySelector('textarea').focus();
  syncEmptyState();
}

function removeTurn(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
  syncEmptyState();
}

function syncEmptyState() {
  const hasTurns = document.getElementById('turns').children.length > 0;
  document.getElementById('emptyTurns').style.display = hasTurns ? 'none' : '';
}

function clearAll() {
  document.getElementById('turns').innerHTML = '';
  document.getElementById('sessionId').value = '';
  syncEmptyState();
  hideResults();
}

function loadDemo() {
  clearAll();
  DEMO.forEach(t => addTurn(t.speaker, t.text));
}

/* ── Collect transcript ───────────────────────────────── */
function collectTranscript() {
  const turns = [...document.querySelectorAll('.turn')];
  return turns.map((el, i) => ({
    timestamp: i,
    speaker: el.dataset.speaker,
    text: el.querySelector('textarea').value.trim(),
  })).filter(t => t.text.length > 0);
}

/* ── Analyze ──────────────────────────────────────────── */
async function analyze() {
  const transcript = collectTranscript();
  if (transcript.length === 0) {
    showError('Please add at least one turn with text before analyzing.');
    return;
  }

  const sessionId = document.getElementById('sessionId').value.trim()
    || `session_${Date.now()}`;

  setLoading(true);
  hideResults();
  dismissError();

  try {
    const res = await fetch('/api/v1/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ transcript, session_id: sessionId }),
    });
    const data = await res.json();

    if (!res.ok || data.status === 'error') {
      showError(data.message || data.error || 'Analysis failed.');
      return;
    }
    renderResults(data);
  } catch (err) {
    showError('Could not reach the server. Make sure the API is running.');
  } finally {
    setLoading(false);
  }
}

/* ── Render results ───────────────────────────────────── */
function renderResults(data) {
  const sections = data.insight_report?.sections || {};
  const analysis = data.analysis || {};
  const sentiment = analysis.sentiment_analysis || {};
  const relational = analysis.relational_dynamics || {};
  const thematic = analysis.thematic_analysis || {};

  renderSummaryTab(sections, sentiment, relational);
  renderEmotionsTab(sentiment, sections.emotional_mapping || {});
  renderThemesTab(sections.thematic_analysis || {}, thematic);
  renderDynamicsTab(relational, sections.relational_dynamics || {});
  renderPlanTab(sections.clinical_hypothesis || {}, sections.recommendations || {});

  showResults();
  switchTabById('summary');
}

/* ── Summary tab ──────────────────────────────────────── */
function renderSummaryTab(sections, sentiment, relational) {
  const exec = sections.executive_summary || {};
  const summary = sentiment.summary || {};
  const alliance = relational.therapeutic_alliance || {};

  // Stats
  const statRow = document.getElementById('statRow');
  statRow.innerHTML = '';
  statRow.appendChild(makeStat('Dominant Emotion', summary.overall_sentiment || '—', `intensity avg ${summary.average_intensity || 0}`));
  statRow.appendChild(makeStat('Stability', summary.emotional_stability || '—'));
  statRow.appendChild(makeStat('Alliance', alliance.rating || '—'));
  const shifts = sentiment.significant_shifts || [];
  statRow.appendChild(makeStat('Emotional Shifts', shifts.length, 'detected'));

  // Tone
  const toneCard = document.getElementById('toneCard');
  toneCard.innerHTML = `
    <div class="card-title">Tone Trajectory</div>
    <p style="font-size:14px;line-height:1.6;color:var(--text)">${exec.overall_tone_trajectory || '—'}</p>
  `;

  // Takeaways
  const tCard = document.getElementById('takeawaysCard');
  const takeaways = exec.key_takeaways || [];
  const focus = exec.priority_focus_area;
  tCard.innerHTML = `
    <div class="card-title">Key Takeaways</div>
    <div class="insight-list">
      ${takeaways.map(t => `<div class="insight-item"><div class="insight-dot"></div><span>${t}</span></div>`).join('')}
      ${focus ? `<div class="insight-item" style="margin-top:8px;padding-top:8px;border-top:1px solid var(--border)">
        <div class="insight-dot" style="background:var(--warn)"></div>
        <span><strong>Priority:</strong> ${focus}</span>
      </div>` : ''}
    </div>
  `;
}

/* ── Emotions tab ─────────────────────────────────────── */
function renderEmotionsTab(sentiment, emotionMapping) {
  const summary = sentiment.summary || {};
  const points = sentiment.emotion_points || [];
  const shifts = sentiment.significant_shifts || [];

  // Summary card
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

  // Trajectory
  const trajItems = points.slice(0, 20).map((p, i) => {
    const icon = EMOTION_ICONS[p.emotion] || '●';
    return `<div class="traj-item">
      <div class="traj-dot">${icon}</div>
      <span>${i + 1}</span>
    </div>`;
  }).join('');

  document.getElementById('emotionTrajectoryCard').innerHTML = `
    <div class="card-title">Emotional Trajectory</div>
    ${points.length ? `<div class="trajectory">${trajItems}</div>
      <p style="margin-top:10px;font-size:12px;color:var(--text-muted)">Showing first ${Math.min(20,points.length)} of ${points.length} turns</p>`
    : '<p class="muted">Not enough data.</p>'}
  `;

  // Shifts
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

/* ── Themes tab ───────────────────────────────────────── */
function renderThemesTab(reportThematic, rawThematic) {
  const dominant = reportThematic.dominant_themes || [];
  const underlying = reportThematic.underlying_themes || [];
  const distortions = rawThematic.cognitive_distortions || [];

  const themeItems = [
    ...dominant.map(t => `<span class="tag">${t}</span>`),
    ...underlying.map(t => `<span class="tag" style="opacity:.7">${t}</span>`),
  ].join('');

  document.getElementById('themesCard').innerHTML = `
    <div class="card-title">Identified Themes</div>
    ${themeItems ? `<div class="tag-group">${themeItems}</div>` : '<p class="muted">No themes identified.</p>'}
  `;

  const distItems = distortions.slice(0, 8).map(d => `
    <div class="distortion-row">
      <span style="font-size:13px">${d.distortion_type}</span>
      <span class="severity-badge severity-${(d.severity || 'moderate').toLowerCase()}">${d.severity || 'Moderate'}</span>
    </div>`).join('');

  document.getElementById('distortionsCard').innerHTML = `
    <div class="card-title">Cognitive Distortions</div>
    ${distItems || '<p class="muted">No cognitive distortions detected.</p>'}
  `;
}

/* ── Dynamics tab ─────────────────────────────────────── */
function renderDynamicsTab(relational, reportDynamics) {
  const alliance = relational.therapeutic_alliance || {};
  const components = alliance.components || {};
  const profiles = relational.speaker_profiles || {};
  const events = relational.relational_events || [];

  // Alliance
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
      <div class="alliance-bar-wrap">
        <div class="alliance-bar" style="width:${Math.round(score)}%"></div>
      </div>
      <div class="alliance-labels"><span>Weak</span><span>Strong</span></div>
    </div>
    <div style="margin-top:14px">${compBars}</div>
  `;

  // Speaker profiles
  const speakerRows = Object.entries(profiles).map(([name, info]) => {
    const cls = name.toLowerCase().includes('therapist') ? 'therapist' : 'client';
    const initials = name.slice(0, 2).toUpperCase();
    return `
      <div class="speaker-row">
        <div class="speaker-avatar ${cls}">${initials}</div>
        <div class="speaker-info">
          <div class="speaker-name" style="text-transform:capitalize">${name}</div>
          <div class="speaker-meta">${info.word_count || 0} words · ${info.style ? `<span class="speaker-style">${info.style}</span>` : ''}</div>
        </div>
      </div>`;
  }).join('');

  document.getElementById('speakerCard').innerHTML = `
    <div class="card-title">Speaker Profiles</div>
    ${speakerRows || '<p class="muted">No speaker data.</p>'}
  `;

  // Events
  const dominantDynamic = relational.dominant_dynamic;
  const eventItems = events.slice(0, 5).map(e => `
    <div class="insight-item">
      <div class="insight-dot" style="background:var(--client)"></div>
      <span><strong>${e.event_type}</strong> — ${e.context ? e.context.slice(0, 80) + '…' : ''}</span>
    </div>`).join('');

  document.getElementById('eventsCard').innerHTML = `
    <div class="card-title">Relational Events ${dominantDynamic ? `— <span style="color:var(--primary)">${dominantDynamic}</span>` : ''}</div>
    <div class="insight-list">
      ${eventItems || '<p class="muted">No significant relational events detected.</p>'}
    </div>
  `;
}

/* ── Plan tab ─────────────────────────────────────────── */
function renderPlanTab(hypothesis, recommendations) {
  const immediate = recommendations.immediate_actions || [];
  const nextSession = recommendations.next_session_focus;
  const monitoring = recommendations.monitoring_points || [];
  const redFlags = recommendations.red_flags || [];

  const recItems = [
    ...immediate.map(a => `<div class="insight-item"><div class="insight-dot"></div><span>${a}</span></div>`),
    nextSession ? `<div class="insight-item"><div class="insight-dot" style="background:var(--warn)"></div><span><strong>Next session:</strong> ${nextSession}</span></div>` : '',
    ...monitoring.map(m => `<div class="insight-item"><div class="insight-dot" style="background:var(--client)"></div><span>${m}</span></div>`),
    ...redFlags.map(r => `<div class="insight-item"><div class="insight-dot" style="background:var(--danger)"></div><span style="color:var(--danger)">${r}</span></div>`),
  ].join('');

  document.getElementById('recommendCard').innerHTML = `
    <div class="card-title">Clinical Recommendations</div>
    <div class="insight-list">${recItems || '<p class="muted">No recommendations.</p>'}</div>
  `;

  // Interventions & approaches
  const interventions = hypothesis.potential_interventions || [];
  const approaches = hypothesis.therapeutic_approaches || [];
  const allInterv = [
    ...interventions.map(i => `<span class="tag">${i}</span>`),
    ...approaches.map(a => `<span class="tag green">${a}</span>`),
  ].join('');

  document.getElementById('interventionsCard').innerHTML = `
    <div class="card-title">Suggested Interventions</div>
    ${allInterv ? `<div class="tag-group">${allInterv}</div>` : '<p class="muted">No specific interventions suggested.</p>'}
  `;

  // Journaling prompts
  const prompts = hypothesis.journaling_prompts || [];
  const promptItems = prompts.map((p, i) => `
    <div style="padding:10px 12px;background:#f8fafc;border-radius:7px;border-left:3px solid var(--primary);font-size:13px;line-height:1.5">
      <span style="font-size:11px;font-weight:700;color:var(--text-muted);display:block;margin-bottom:3px">PROMPT ${i + 1}</span>
      ${p}
    </div>`).join('');

  document.getElementById('journalingCard').innerHTML = `
    <div class="card-title">Journaling Prompts</div>
    <div style="display:flex;flex-direction:column;gap:8px">
      ${promptItems || '<p class="muted">No prompts generated.</p>'}
    </div>
  `;
}

/* ── Helpers ──────────────────────────────────────────── */
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
  const txt = document.getElementById('analyzeBtnText');
  const spinner = document.getElementById('analyzeSpinner');
  btn.disabled = on;
  txt.textContent = on ? 'Analyzing…' : 'Analyze Session';
  spinner.classList.toggle('hidden', !on);
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
  const b = document.getElementById('errorBanner');
  document.getElementById('errorMsg').textContent = msg;
  b.classList.remove('hidden');
}

function dismissError() {
  document.getElementById('errorBanner').classList.add('hidden');
}

/* ── Init ─────────────────────────────────────────────── */
syncEmptyState();
