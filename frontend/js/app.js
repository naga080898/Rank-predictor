/**
 * RankPulse AI — Frontend Application Logic
 * High-performance SPA controller for response sheet evaluation, live rank estimation, and shift analytics.
 */

// API Base URL (Supports independent frontend hosting on Cloudflare Pages/Vercel or local monolith)
const API_BASE = window.API_BASE_URL || '';

// Application State
const state = {
  activeTab: 'predictor',
  selectedFile: null,
  currentEvaluation: null,
  questionFilter: 'all',
  questionSearchQuery: '',
  leaderboardData: [],
  statsData: null,
  samplePdfs: []
};

// DOM Element References
const DOM = {
  // Nav
  brandHomeBtn: document.getElementById('brand-home-btn'),
  navTabs: document.getElementById('main-nav-tabs'),
  tabBtnPredictor: document.getElementById('tab-btn-predictor'),
  tabBtnLeaderboard: document.getElementById('tab-btn-leaderboard'),
  tabBtnStats: document.getElementById('tab-btn-stats'),
  apiStatusText: document.getElementById('api-status-text'),
  btnOpenLookup: document.getElementById('btn-open-lookup'),
  themeToggleBtn: document.getElementById('theme-toggle-btn'),

  // Views
  viewPredictor: document.getElementById('view-predictor'),
  viewScorecard: document.getElementById('view-scorecard'),
  viewLeaderboard: document.getElementById('view-leaderboard'),
  viewStats: document.getElementById('view-stats'),

  // Predictor / Upload
  dropZone: document.getElementById('drop-zone'),
  fileInput: document.getElementById('file-input'),
  selectedFileCard: document.getElementById('selected-file-card'),
  fileNameDisplay: document.getElementById('file-name-display'),
  fileSizeDisplay: document.getElementById('file-size-display'),
  btnRemoveFile: document.getElementById('btn-remove-file'),
  btnSubmitEvaluate: document.getElementById('btn-submit-evaluate'),
  demoSample1: document.getElementById('demo-sample-1'),
  demoSample2: document.getElementById('demo-sample-2'),

  // Scorecard View
  btnBackToUpload: document.getElementById('btn-back-to-upload'),
  btnPrintScorecard: document.getElementById('btn-print-scorecard'),
  btnViewOnLeaderboard: document.getElementById('btn-view-on-leaderboard'),
  scAvatar: document.getElementById('sc-avatar'),
  scCandidateName: document.getElementById('sc-candidate-name'),
  scHallTicket: document.getElementById('sc-hall-ticket'),
  scSubjectTag: document.getElementById('sc-subject-tag'),
  scTestDateTime: document.getElementById('sc-test-date-time'),
  scSubmissionId: document.getElementById('sc-submission-id'),
  scTimestamp: document.getElementById('sc-timestamp'),
  scFinalScore: document.getElementById('sc-final-score'),
  scPosMarks: document.getElementById('sc-pos-marks'),
  scNegMarks: document.getElementById('sc-neg-marks'),
  scPlatformRank: document.getElementById('sc-platform-rank'),
  scTotalSubmissions: document.getElementById('sc-total-submissions'),
  scPercentileBadge: document.getElementById('sc-percentile-badge'),
  scAirRange: document.getElementById('sc-air-range'),
  scShiftRank: document.getElementById('sc-shift-rank'),
  scShiftDifficulty: document.getElementById('sc-shift-difficulty'),
  scTotalQ: document.getElementById('sc-total-q'),
  scAttemptedSummary: document.getElementById('sc-attempted-summary'),
  scCorrectCnt: document.getElementById('sc-correct-cnt'),
  scIncorrectCnt: document.getElementById('sc-incorrect-cnt'),
  scAccuracyRate: document.getElementById('sc-accuracy-rate'),
  scSectionsContainer: document.getElementById('sc-sections-container'),

  // Questions Review
  cntAll: document.getElementById('cnt-all'),
  cntCorrect: document.getElementById('cnt-correct'),
  cntIncorrect: document.getElementById('cnt-incorrect'),
  cntUnattempted: document.getElementById('cnt-unattempted'),
  filterPills: document.querySelectorAll('.filter-pill'),
  qSearchInput: document.getElementById('q-search-input'),
  questionsListContainer: document.getElementById('questions-list-container'),

  // Leaderboard
  podiumContainer: document.getElementById('podium-container'),
  lbSubjectSelect: document.getElementById('lb-subject-select'),
  lbShiftSelect: document.getElementById('lb-shift-select'),
  lbSearchInput: document.getElementById('lb-search-input'),
  leaderboardTbody: document.getElementById('leaderboard-tbody'),

  // Stats / Shift Analytics
  statTotalSubs: document.getElementById('stat-total-subs'),
  statAvgScore: document.getElementById('stat-avg-score'),
  statMedianScore: document.getElementById('stat-median-score'),
  statMaxScore: document.getElementById('stat-max-score'),
  statMinScore: document.getElementById('stat-min-score'),
  statAvgAccuracy: document.getElementById('stat-avg-accuracy'),
  statStdDev: document.getElementById('stat-std-dev'),
  shiftsContainer: document.getElementById('shifts-container'),
  histogramBarsContainer: document.getElementById('histogram-bars-container'),

  // Lookup Modal
  modalLookup: document.getElementById('modal-lookup'),
  btnCloseLookup: document.getElementById('btn-close-lookup'),
  formLookup: document.getElementById('form-lookup'),
  lookupIdentifierInput: document.getElementById('lookup-identifier-input'),

  // Loading Overlay
  loadingOverlay: document.getElementById('loading-overlay'),

  // Toast Container
  toastContainer: document.getElementById('toast-container')
};

// ============================================================================
// Initialization
// ============================================================================
document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  initEventListeners();
  checkApiHealth();
});

function initTheme() {
  const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
  updateThemeToggleUI(currentTheme);
}

function toggleTheme() {
  const currentTheme = document.documentElement.getAttribute('data-theme') || 'dark';
  const newTheme = currentTheme === 'light' ? 'dark' : 'light';
  document.documentElement.setAttribute('data-theme', newTheme);
  localStorage.setItem('rankpulse-theme', newTheme);
  updateThemeToggleUI(newTheme);
  showToast(`Switched to ${newTheme === 'light' ? 'Light' : 'Dark'} Mode`, 'info');
}

function updateThemeToggleUI(theme) {
  if (!DOM.themeToggleBtn) return;
  const title = theme === 'light' ? 'Switch to Dark Mode' : 'Switch to Light Mode';
  DOM.themeToggleBtn.setAttribute('title', title);
  DOM.themeToggleBtn.setAttribute('aria-label', title);
}

function initEventListeners() {
  // Theme Toggle
  if (DOM.themeToggleBtn) {
    DOM.themeToggleBtn.addEventListener('click', toggleTheme);
  }

  // Navigation Tabs
  DOM.navTabs.addEventListener('click', (e) => {
    const btn = e.target.closest('.nav-tab-btn');
    if (!btn) return;
    const targetTab = btn.getAttribute('data-tab');
    switchTab(targetTab);
  });

  DOM.brandHomeBtn.addEventListener('click', (e) => {
    e.preventDefault();
    switchTab('predictor');
  });

  // File Upload Handlers
  DOM.dropZone.addEventListener('click', () => DOM.fileInput.click());
  DOM.fileInput.addEventListener('change', handleFileInputChange);

  // Drag & Drop
  ['dragenter', 'dragover'].forEach(eventName => {
    DOM.dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      DOM.dropZone.classList.add('dragover');
    });
  });

  ['dragleave', 'drop'].forEach(eventName => {
    DOM.dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      DOM.dropZone.classList.remove('dragover');
    });
  });

  DOM.dropZone.addEventListener('drop', (e) => {
    const files = e.dataTransfer.files;
    if (files.length > 0 && files[0].type === 'application/pdf') {
      handleFileSelected(files[0]);
    } else {
      showToast('Please upload a valid PDF file.', 'error');
    }
  });

  DOM.btnRemoveFile.addEventListener('click', removeSelectedFile);
  DOM.btnSubmitEvaluate.addEventListener('click', submitEvaluationForm);

  // Demo Sample PDF evaluation buttons
  DOM.demoSample1.addEventListener('click', () => runDemoSample(1));
  DOM.demoSample2.addEventListener('click', () => runDemoSample(2));

  // Scorecard Actions
  DOM.btnBackToUpload.addEventListener('click', () => switchTab('predictor'));
  DOM.btnPrintScorecard.addEventListener('click', () => window.print());
  DOM.btnViewOnLeaderboard.addEventListener('click', () => switchTab('leaderboard'));

  // Question Filters
  DOM.filterPills.forEach(pill => {
    pill.addEventListener('click', () => {
      DOM.filterPills.forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      state.questionFilter = pill.getAttribute('data-filter');
      renderQuestionsList();
    });
  });

  DOM.qSearchInput.addEventListener('input', (e) => {
    state.questionSearchQuery = e.target.value.toLowerCase().trim();
    renderQuestionsList();
  });

  // Leaderboard Filters
  DOM.lbSubjectSelect.addEventListener('change', fetchAndRenderLeaderboard);
  DOM.lbShiftSelect.addEventListener('change', fetchAndRenderLeaderboard);
  DOM.lbSearchInput.addEventListener('input', debounce(filterLeaderboardLocally, 250));

  // Lookup Modal Handlers
  DOM.btnOpenLookup.addEventListener('click', () => openLookupModal());
  DOM.btnCloseLookup.addEventListener('click', () => closeLookupModal());
  DOM.modalLookup.addEventListener('click', (e) => {
    if (e.target === DOM.modalLookup) closeLookupModal();
  });
  DOM.formLookup.addEventListener('submit', handleLookupSubmit);

  // Copy Hall Ticket
  DOM.scHallTicket.addEventListener('click', () => {
    const text = DOM.scHallTicket.textContent.trim();
    if (text) {
      navigator.clipboard.writeText(text).then(() => {
        showToast(`Copied Hall Ticket: ${text}`, 'success');
      });
    }
  });
}

// ============================================================================
// API & Health Check
// ============================================================================
async function checkApiHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (res.ok) {
      const data = await res.json();
      DOM.apiStatusText.textContent = `API Online (${data.total_submissions_recorded} Submissions)`;
    } else {
      DOM.apiStatusText.textContent = 'API Error';
    }
  } catch {
    DOM.apiStatusText.textContent = 'API Offline';
  }
}

// ============================================================================
// Tab Switching
// ============================================================================
function switchTab(tabId) {
  state.activeTab = tabId;

  // Update Nav Buttons
  document.querySelectorAll('.nav-tab-btn').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('data-tab') === tabId);
  });

  // Hide All Views
  DOM.viewPredictor.style.display = 'none';
  DOM.viewScorecard.style.display = 'none';
  DOM.viewLeaderboard.style.display = 'none';
  DOM.viewStats.style.display = 'none';

  if (tabId === 'predictor') {
    DOM.viewPredictor.style.display = 'block';
  } else if (tabId === 'scorecard') {
    DOM.viewScorecard.style.display = 'block';
  } else if (tabId === 'leaderboard') {
    DOM.viewLeaderboard.style.display = 'block';
    fetchAndRenderLeaderboard();
  } else if (tabId === 'stats') {
    DOM.viewStats.style.display = 'block';
    fetchAndRenderStats();
  }

  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ============================================================================
// File Upload & Evaluation Handler
// ============================================================================
function handleFileInputChange(e) {
  if (e.target.files && e.target.files[0]) {
    handleFileSelected(e.target.files[0]);
  }
}

function handleFileSelected(file) {
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    showToast('Invalid file. Please select a PDF file.', 'error');
    return;
  }
  state.selectedFile = file;
  DOM.fileNameDisplay.textContent = file.name;
  DOM.fileSizeDisplay.textContent = formatBytes(file.size);
  DOM.selectedFileCard.style.display = 'flex';
  DOM.btnSubmitEvaluate.disabled = false;
  showToast(`Selected "${file.name}"`, 'info');
}

function removeSelectedFile(e) {
  e?.stopPropagation();
  state.selectedFile = null;
  DOM.fileInput.value = '';
  DOM.selectedFileCard.style.display = 'none';
  DOM.btnSubmitEvaluate.disabled = true;
}

async function submitEvaluationForm() {
  if (!state.selectedFile) {
    showToast('Please select a PDF file to evaluate.', 'error');
    return;
  }

  const formData = new FormData();
  formData.append('file', state.selectedFile);
  formData.append('positive_marks', 1.0);
  formData.append('negative_marks', 0.0);

  showLoadingOverlay(true);
  simulateLoadingSteps();

  try {
    const res = await fetch(`${API_BASE}/api/evaluate`, {
      method: 'POST',
      body: formData
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Evaluation failed.');
    }

    const data = await res.json();
    state.currentEvaluation = data;
    renderScorecard(data);
    showToast(`Successfully evaluated ${data.candidate.participant_name || 'Scorecard'}! Score: ${data.summary.final_score}`, 'success');
    switchTab('scorecard');
    checkApiHealth();
  } catch (err) {
    showToast(`Evaluation error: ${err.message}`, 'error');
  } finally {
    showLoadingOverlay(false);
  }
}

// 1-Click Demo Evaluation Handler
async function runDemoSample(sampleNumber) {
  showLoadingOverlay(true);
  simulateLoadingSteps();

  try {
    const res = await fetch(`${API_BASE}/api/evaluate-sample/${sampleNumber}?positive_marks=1.0&negative_marks=0.0`, {
      method: 'POST'
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Sample run failed' }));
      throw new Error(err.detail || 'Sample run failed.');
    }

    const data = await res.json();
    state.currentEvaluation = data;
    renderScorecard(data);
    showToast(`Demo Sample #${sampleNumber} Evaluated: Score ${data.summary.final_score}`, 'success');
    switchTab('scorecard');
    checkApiHealth();
  } catch (err) {
    showToast(`Demo error: ${err.message}`, 'error');
  } finally {
    showLoadingOverlay(false);
  }
}

// ============================================================================
// Scorecard Renderer
// ============================================================================
function renderScorecard(data) {
  const cand = data.candidate || {};
  const sum = data.summary || {};
  const rank = data.rank_estimate || {};
  const sec = data.sections || {};
  const questions = data.questions || [];

  // Candidate Profile Banner
  const name = cand.participant_name ? cand.participant_name.trim() : 'Anonymous Candidate';
  DOM.scCandidateName.textContent = name;
  DOM.scAvatar.textContent = name.charAt(0).toUpperCase() || 'C';
  DOM.scHallTicket.textContent = cand.hall_ticket || 'N/A';
  DOM.scSubjectTag.textContent = cand.subject ? `⚡ ${cand.subject}` : 'General Exam';
  
  const dateTimeParts = [];
  if (cand.test_date) dateTimeParts.push(`📅 ${cand.test_date}`);
  if (cand.test_time) dateTimeParts.push(`🕒 ${cand.test_time}`);
  DOM.scTestDateTime.textContent = dateTimeParts.join(' • ') || 'Shift N/A';
  DOM.scSubmissionId.textContent = `#${String(data.submission_id).padStart(4, '0')}`;
  DOM.scTimestamp.textContent = data.submitted_at ? new Date(data.submitted_at).toLocaleTimeString() : 'Recent';

  // Primary Metrics
  DOM.scFinalScore.textContent = sum.final_score.toFixed(2);
  DOM.scPosMarks.textContent = `${sum.correct} / ${sum.total_questions} Marks`;
  DOM.scNegMarks.textContent = `• No Negative Marking`;

  DOM.scPlatformRank.textContent = `#${rank.platform_rank}`;
  DOM.scTotalSubmissions.textContent = rank.total_submissions;
  DOM.scPercentileBadge.textContent = `${rank.percentile}%ile (Top ${Math.max(0.1, (100 - rank.percentile)).toFixed(1)}%)`;

  DOM.scAirRange.textContent = rank.predicted_air_range || '1 - 100';
  DOM.scShiftRank.textContent = `#${rank.shift_rank} / ${rank.total_shift_submissions}`;
  DOM.scShiftDifficulty.textContent = `${rank.shift_difficulty_tier || 'Normal'} Shift • ${rank.shift_percentile}%ile`;

  // Secondary Stats
  DOM.scTotalQ.textContent = sum.total_questions;
  DOM.scAttemptedSummary.textContent = `${sum.attempted} Attempted (${sum.unattempted} Skipped)`;
  DOM.scCorrectCnt.textContent = sum.correct;
  DOM.scIncorrectCnt.textContent = sum.incorrect;
  DOM.scAccuracyRate.textContent = `${sum.accuracy_percent}%`;

  // Filter Button Counts
  DOM.cntAll.textContent = sum.total_questions;
  DOM.cntCorrect.textContent = sum.correct;
  DOM.cntIncorrect.textContent = sum.incorrect;
  DOM.cntUnattempted.textContent = sum.unattempted;

  // Render Section Breakdown Cards
  renderSectionsBreakdown(sec);

  // Render Questions List
  renderQuestionsList();
}

function renderSectionsBreakdown(sections) {
  DOM.scSectionsContainer.innerHTML = '';
  const entries = Object.entries(sections);

  if (entries.length === 0) {
    DOM.scSectionsContainer.innerHTML = '<div style="color: var(--text-dim);">No specific sections recorded.</div>';
    return;
  }

  entries.forEach(([sectionName, s]) => {
    const card = document.createElement('div');
    card.className = 'section-stat-card';

    const correctPct = s.total > 0 ? (s.correct / s.total) * 100 : 0;
    const incorrectPct = s.total > 0 ? (s.incorrect / s.total) * 100 : 0;
    const skippedPct = s.total > 0 ? (s.unattempted / s.total) * 100 : 0;

    card.innerHTML = `
      <div class="section-stat-title">
        <span>${escapeHtml(sectionName)}</span>
        <span class="section-score-pill">${s.score > 0 ? '+' : ''}${s.score} Marks</span>
      </div>
      <div class="section-progress-bar">
        <div class="progress-segment-correct" style="width: ${correctPct}%" title="${s.correct} Correct"></div>
        <div class="progress-segment-incorrect" style="width: ${incorrectPct}%" title="${s.incorrect} Incorrect"></div>
        <div class="progress-segment-skipped" style="width: ${skippedPct}%" title="${s.unattempted} Skipped"></div>
      </div>
      <div class="section-counts-row">
        <span style="color: var(--success);">✓ ${s.correct} Correct</span>
        <span style="color: var(--danger);">✗ ${s.incorrect} Wrong</span>
        <span style="color: var(--text-dim);">– ${s.unattempted} Skipped</span>
      </div>
    `;
    DOM.scSectionsContainer.appendChild(card);
  });
}

function renderQuestionsList() {
  if (!state.currentEvaluation || !state.currentEvaluation.questions) {
    DOM.questionsListContainer.innerHTML = '<div style="text-align: center; color: var(--text-dim); padding: 2rem;">No question details available.</div>';
    return;
  }

  const allQuestions = state.currentEvaluation.questions;
  const filter = state.questionFilter;
  const query = state.questionSearchQuery;

  const filtered = allQuestions.filter(q => {
    // Status Filter
    if (filter !== 'all' && q.status !== filter) {
      return false;
    }
    // Search Query Filter
    if (query) {
      const matchText = (q.question_text || '').toLowerCase().includes(query);
      const matchId = (q.question_id || '').toLowerCase().includes(query);
      const matchNum = String(q.question_number) === query;
      const matchSection = (q.section || '').toLowerCase().includes(query);
      if (!matchText && !matchId && !matchNum && !matchSection) {
        return false;
      }
    }
    return true;
  });

  if (filtered.length === 0) {
    DOM.questionsListContainer.innerHTML = `
      <div style="text-align: center; color: var(--text-dim); padding: 3rem;">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="margin-bottom: 0.5rem;"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
        <p>No questions matched your filter criteria.</p>
      </div>
    `;
    return;
  }

  DOM.questionsListContainer.innerHTML = filtered.map(q => {
    let statusClass = 'status-unattempted';
    let marksBadge = '<span class="q-marks-pill marks-zero">0.00</span>';

    if (q.status === 'CORRECT') {
      statusClass = 'status-correct';
      marksBadge = `<span class="q-marks-pill marks-positive">+${q.marks_awarded.toFixed(2)}</span>`;
    } else if (q.status === 'INCORRECT') {
      statusClass = 'status-incorrect';
      marksBadge = `<span class="q-marks-pill marks-negative">${q.marks_awarded.toFixed(2)}</span>`;
    }

    // Render Options 1..4
    const optionsHtml = [1, 2, 3, 4].map(optNum => {
      const optText = q.options && q.options[optNum] ? q.options[optNum] : `Option ${optNum}`;
      const isCorrectKey = q.correct_option === optNum;
      const isChosenByCandidate = q.chosen_option === optNum;

      let rowClass = '';
      let tagHtml = '';

      if (isCorrectKey && isChosenByCandidate) {
        rowClass = 'is-correct';
        tagHtml = '<span class="q-tag-indicator tag-chosen-correct">✓ Your Answer (Correct)</span>';
      } else if (isCorrectKey) {
        rowClass = 'is-correct';
        tagHtml = '<span class="q-tag-indicator tag-correct-key">Official Key</span>';
      } else if (isChosenByCandidate) {
        rowClass = 'is-chosen-wrong';
        tagHtml = '<span class="q-tag-indicator tag-chosen-wrong">✗ Your Choice</span>';
      }

      return `
        <div class="q-option-row ${rowClass}">
          <span class="q-option-num">${optNum}.</span>
          <span class="q-option-text">${escapeHtml(optText)}</span>
          ${tagHtml}
        </div>
      `;
    }).join('');

    return `
      <div class="question-item-card ${statusClass}">
        <div class="q-header-row">
          <div class="q-num-section">
            <span class="q-num-badge">Q.${q.question_number}</span>
            <span class="q-sec-badge">${escapeHtml(q.section || 'General')}</span>
          </div>
          ${marksBadge}
        </div>

        <div class="q-body-text">${escapeHtml(q.question_text || 'Question text not available in response sheet extraction.')}</div>

        <div class="q-options-grid">
          ${optionsHtml}
        </div>

        <div class="q-footer-meta">
          <span>Question ID: ${q.question_id || 'N/A'}</span>
          <span>Chosen: ${q.chosen_option !== null ? `Option ${q.chosen_option}` : 'Not Answered'} • Correct: ${q.correct_option ? `Option ${q.correct_option}` : 'N/A'}</span>
        </div>
      </div>
    `;
  }).join('');
}

// ============================================================================
// Live Leaderboard Fetcher & Renderer
// ============================================================================
async function fetchAndRenderLeaderboard() {
  const subject = DOM.lbSubjectSelect.value;
  const shift = DOM.lbShiftSelect.value;

  let url = `${API_BASE}/api/leaderboard?limit=100`;
  if (subject) url += `&subject=${encodeURIComponent(subject)}`;
  if (shift) url += `&test_time=${encodeURIComponent(shift)}`;

  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch leaderboard');
    const data = await res.json();
    state.leaderboardData = data;

    // Populate filter dropdowns if empty
    populateLeaderboardFilters(data);

    // Render Podium Top 3
    renderPodium(data);

    // Render Table
    renderLeaderboardTable(data);
  } catch (err) {
    showToast(`Leaderboard error: ${err.message}`, 'error');
  }
}

function populateLeaderboardFilters(data) {
  if (DOM.lbSubjectSelect.options.length <= 1) {
    const subjects = [...new Set(data.map(d => d.subject).filter(Boolean))];
    subjects.forEach(sub => {
      const opt = document.createElement('option');
      opt.value = sub;
      opt.textContent = sub;
      DOM.lbSubjectSelect.appendChild(opt);
    });
  }

  if (DOM.lbShiftSelect.options.length <= 1) {
    const shifts = [...new Set(data.map(d => d.test_time).filter(Boolean))];
    shifts.forEach(sh => {
      const opt = document.createElement('option');
      opt.value = sh;
      opt.textContent = sh;
      DOM.lbShiftSelect.appendChild(opt);
    });
  }
}

function renderPodium(data) {
  if (!data || data.length === 0) {
    DOM.podiumContainer.innerHTML = '';
    return;
  }

  const top1 = data[0];
  const top2 = data[1] || null;
  const top3 = data[2] || null;

  let html = '';

  // Rank 2 (Silver)
  if (top2) {
    html += `
      <div class="podium-card podium-rank-2">
        <div class="podium-badge badge-silver">🥈</div>
        <div class="podium-name">${escapeHtml(top2.participant_name || top2.hall_ticket_masked)}</div>
        <div class="podium-branch">${escapeHtml(top2.subject || 'Branch')}</div>
        <div class="podium-score">${top2.final_score.toFixed(2)}</div>
        <div style="font-size: 0.75rem; color: var(--text-dim);">${top2.percentile}%ile</div>
      </div>
    `;
  }

  // Rank 1 (Gold)
  if (top1) {
    html += `
      <div class="podium-card podium-rank-1">
        <div class="podium-badge badge-gold">👑</div>
        <div class="podium-name" style="font-size: 1.25rem;">${escapeHtml(top1.participant_name || top1.hall_ticket_masked)}</div>
        <div class="podium-branch">${escapeHtml(top1.subject || 'Branch')}</div>
        <div class="podium-score" style="color: #fbbf24; font-size: 2.2rem;">${top1.final_score.toFixed(2)}</div>
        <div style="font-size: 0.8rem; color: #fbbf24; font-weight: 600;">AIR #1 • ${top1.percentile}%ile</div>
      </div>
    `;
  }

  // Rank 3 (Bronze)
  if (top3) {
    html += `
      <div class="podium-card podium-rank-3">
        <div class="podium-badge badge-bronze">🥉</div>
        <div class="podium-name">${escapeHtml(top3.participant_name || top3.hall_ticket_masked)}</div>
        <div class="podium-branch">${escapeHtml(top3.subject || 'Branch')}</div>
        <div class="podium-score">${top3.final_score.toFixed(2)}</div>
        <div style="font-size: 0.75rem; color: var(--text-dim);">${top3.percentile}%ile</div>
      </div>
    `;
  }

  DOM.podiumContainer.innerHTML = html;
}

function renderLeaderboardTable(data) {
  if (!data || data.length === 0) {
    DOM.leaderboardTbody.innerHTML = `
      <tr>
        <td colspan="9" style="text-align: center; color: var(--text-dim); padding: 3rem;">
          No leaderboard entries found for this filter.
        </td>
      </tr>
    `;
    return;
  }

  DOM.leaderboardTbody.innerHTML = data.map(item => {
    let rankBadge = `<span class="rank-pill">#${item.rank}</span>`;
    if (item.rank === 1) rankBadge = `<span class="rank-pill rank-top1">🥇 #1</span>`;
    else if (item.rank === 2) rankBadge = `<span class="rank-pill rank-top2">🥈 #2</span>`;
    else if (item.rank === 3) rankBadge = `<span class="rank-pill rank-top3">🥉 #3</span>`;

    const shiftInfo = [item.test_date, item.test_time].filter(Boolean).join(' ') || 'Standard';

    return `
      <tr>
        <td>${rankBadge}</td>
        <td>
          <div style="font-weight: 600;">${escapeHtml(item.participant_name || 'Candidate')}</div>
          <div style="font-size: 0.75rem; font-family: var(--font-mono); color: var(--text-dim);">${item.hall_ticket_masked}</div>
        </td>
        <td>${escapeHtml(item.subject || 'General')}</td>
        <td style="font-size: 0.8rem; color: var(--text-muted);">${escapeHtml(shiftInfo)}</td>
        <td style="text-align: center; font-family: var(--font-mono); font-size: 0.8rem;">
          <span style="color: var(--success);">${item.correct}</span> / 
          <span style="color: var(--danger);">${item.incorrect}</span> / 
          <span style="color: var(--text-dim);">${item.unattempted}</span>
        </td>
        <td>
          <div style="font-size: 0.8rem; font-weight: 600;">${item.accuracy_percent}%</div>
          <div class="accuracy-bar-mini">
            <div class="accuracy-fill-mini" style="width: ${item.accuracy_percent}%;"></div>
          </div>
        </td>
        <td style="text-align: right; font-family: var(--font-heading); font-weight: 700; font-size: 1.1rem; color: var(--primary-light);">
          ${item.final_score.toFixed(2)}
        </td>
        <td style="text-align: right; font-family: var(--font-mono); font-size: 0.85rem; color: var(--accent-cyan);">
          ${item.percentile}%ile
        </td>
        <td style="text-align: center;">
          <button class="btn-secondary" style="padding: 4px 10px; font-size: 0.75rem;" onclick="inspectCandidateScorecard(${item.submission_id})">
            Inspect
          </button>
        </td>
      </tr>
    `;
  }).join('');
}

function filterLeaderboardLocally() {
  const query = DOM.lbSearchInput.value.toLowerCase().trim();
  if (!query) {
    renderLeaderboardTable(state.leaderboardData);
    return;
  }

  const filtered = state.leaderboardData.filter(d => {
    return (d.participant_name || '').toLowerCase().includes(query) ||
           (d.hall_ticket_masked || '').toLowerCase().includes(query) ||
           (d.subject || '').toLowerCase().includes(query);
  });

  renderLeaderboardTable(filtered);
}

// Global inspect function for table buttons
window.inspectCandidateScorecard = async function(submissionId) {
  showLoadingOverlay(true);
  try {
    const res = await fetch(`${API_BASE}/api/candidate/${submissionId}`);
    if (!res.ok) throw new Error('Candidate not found');
    const data = await res.json();
    state.currentEvaluation = data;
    renderScorecard(data);
    switchTab('scorecard');
  } catch (err) {
    showToast(`Lookup error: ${err.message}`, 'error');
  } finally {
    showLoadingOverlay(false);
  }
};

// ============================================================================
// Shift Analytics & Histogram Renderer
// ============================================================================
async function fetchAndRenderStats() {
  try {
    const res = await fetch(`${API_BASE}/api/stats`);
    if (!res.ok) throw new Error('Failed to fetch statistics');
    const data = await res.json();
    state.statsData = data;

    // Overall metrics
    DOM.statTotalSubs.textContent = data.total_submissions;
    DOM.statAvgScore.textContent = (data.overall.avg_score || 0).toFixed(2);
    DOM.statMedianScore.textContent = `Median: ${(data.overall.median_score || 0).toFixed(2)}`;
    DOM.statMaxScore.textContent = (data.overall.max_score || 0).toFixed(2);
    DOM.statMinScore.textContent = `Lowest: ${(data.overall.min_score || 0).toFixed(2)}`;
    DOM.statAvgAccuracy.textContent = `${(data.overall.avg_accuracy || 0).toFixed(1)}%`;
    DOM.statStdDev.textContent = `Std Dev: ${(data.overall.std_dev || 0).toFixed(2)}`;

    // Shift Cards
    renderShiftsComparison(data.shifts || []);

    // Histogram
    renderHistogram(data.score_distribution || []);
  } catch (err) {
    showToast(`Analytics error: ${err.message}`, 'error');
  }
}

function renderShiftsComparison(shifts) {
  if (!shifts || shifts.length === 0) {
    DOM.shiftsContainer.innerHTML = '<div style="color: var(--text-dim);">No shift data available yet.</div>';
    return;
  }

  DOM.shiftsContainer.innerHTML = shifts.map(sh => {
    return `
      <div class="shift-card">
        <span class="shift-tag">${escapeHtml(sh.shift_key)}</span>
        <div style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.5rem;">
          📅 ${sh.test_date || 'Date N/A'} • 🕒 ${sh.test_time || 'Time N/A'}
        </div>
        <div class="shift-stats-row">
          <div>
            <div class="shift-stat-val">${sh.candidate_count}</div>
            <div class="shift-stat-lbl">Candidates</div>
          </div>
          <div>
            <div class="shift-stat-val" style="color: var(--primary-light);">${sh.avg_score.toFixed(2)}</div>
            <div class="shift-stat-lbl">Shift Avg</div>
          </div>
          <div>
            <div class="shift-stat-val" style="color: var(--success);">${sh.max_score.toFixed(2)}</div>
            <div class="shift-stat-lbl">Shift Max</div>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

function renderHistogram(buckets) {
  if (!buckets || buckets.length === 0) {
    DOM.histogramBarsContainer.innerHTML = '<div style="color: var(--text-dim); padding: 2rem;">No distribution data.</div>';
    return;
  }

  const maxCount = Math.max(...buckets.map(b => b.count), 1);

  DOM.histogramBarsContainer.innerHTML = buckets.map(b => {
    const heightPercent = Math.max(8, (b.count / maxCount) * 100);
    return `
      <div class="hist-col">
        <span class="hist-count">${b.count}</span>
        <div class="hist-bar" style="height: ${heightPercent}%;" title="${b.range_label}: ${b.count} candidates (${b.percentage}%)"></div>
        <span class="hist-label">${b.range_label}</span>
      </div>
    `;
  }).join('');
}

// ============================================================================
// Lookup Modal
// ============================================================================
function openLookupModal() {
  DOM.modalLookup.style.display = 'flex';
  DOM.lookupIdentifierInput.focus();
}

function closeLookupModal() {
  DOM.modalLookup.style.display = 'none';
}

async function handleLookupSubmit(e) {
  e.preventDefault();
  const id = DOM.lookupIdentifierInput.value.trim();
  if (!id) return;

  closeLookupModal();
  showLoadingOverlay(true);

  try {
    const res = await fetch(`${API_BASE}/api/candidate/${encodeURIComponent(id)}`);
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Candidate not found');
    }
    const data = await res.json();
    state.currentEvaluation = data;
    renderScorecard(data);
    showToast(`Found scorecard for ${data.candidate.participant_name || id}`, 'success');
    switchTab('scorecard');
  } catch (err) {
    showToast(`Search failed: ${err.message}`, 'error');
  } finally {
    showLoadingOverlay(false);
  }
}

// ============================================================================
// Helpers & Utilities
// ============================================================================
function showLoadingOverlay(show) {
  DOM.loadingOverlay.style.display = show ? 'flex' : 'none';
  if (show) {
    // Reset steps
    ['step-1', 'step-2', 'step-3', 'step-4'].forEach(id => {
      const el = document.getElementById(id);
      if (el) {
        el.className = 'loading-step-item';
      }
    });
    const s1 = document.getElementById('step-1');
    if (s1) s1.className = 'loading-step-item active';
  }
}

function simulateLoadingSteps() {
  setTimeout(() => {
    const s1 = document.getElementById('step-1');
    const s2 = document.getElementById('step-2');
    if (s1 && s2) { s1.className = 'loading-step-item done'; s2.className = 'loading-step-item active'; }
  }, 300);

  setTimeout(() => {
    const s2 = document.getElementById('step-2');
    const s3 = document.getElementById('step-3');
    if (s2 && s3) { s2.className = 'loading-step-item done'; s3.className = 'loading-step-item active'; }
  }, 650);

  setTimeout(() => {
    const s3 = document.getElementById('step-3');
    const s4 = document.getElementById('step-4');
    if (s3 && s4) { s3.className = 'loading-step-item done'; s4.className = 'loading-step-item active'; }
  }, 1000);
}

function showToast(message, type = 'info') {
  window.showToast = showToast;
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;

  let icon = 'ℹ️';
  if (type === 'success') icon = '✓';
  if (type === 'error') icon = '✗';

  toast.innerHTML = `
    <span style="font-weight: 700;">${icon}</span>
    <span>${escapeHtml(message)}</span>
  `;

  DOM.toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

function formatBytes(bytes) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}
