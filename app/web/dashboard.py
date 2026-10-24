"""Interactive Web Dashboard for AI Auto Job Apply."""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["Web Dashboard"])

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI Auto Job Apply — Dashboard</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    body { background-color: #0f172a; color: #f8fafc; font-family: ui-sans-serif, system-ui, sans-serif; }
    .card { background-color: #1e293b; border: 1px solid #334155; border-radius: 0.75rem; }
    .badge { display: inline-flex; align-items: center; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; padding: 0.25rem 0.65rem; }
  </style>
</head>
<body class="p-6">
  <div class="max-w-7xl mx-auto space-y-6">
    <!-- Header -->
    <header class="flex flex-col md:flex-row md:items-center justify-between pb-6 border-b border-slate-700 gap-4">
      <div>
        <h1 class="text-3xl font-extrabold tracking-tight text-white flex items-center gap-3">
          <i class="fa-solid fa-robot text-indigo-400"></i> AI Auto Job Apply
        </h1>
        <p class="text-slate-400 text-sm mt-1">Multi-Source Discovery, Transparent Matching & Human-Approved Application Automation</p>
      </div>
      <div class="flex items-center gap-3">
        <span id="ai-status-badge" class="badge bg-slate-800 text-slate-300 border border-slate-600">
          <i class="fa-solid fa-spinner fa-spin mr-1.5"></i> Checking AI...
        </span>
        <button onclick="triggerJobSync()" id="sync-jobs-btn" class="bg-indigo-600 hover:bg-indigo-500 text-white font-medium px-4 py-2 rounded-lg text-sm flex items-center gap-2 transition">
          <i class="fa-solid fa-rotate"></i> Sync Jobs
        </button>
        <a href="/docs" target="_blank" class="bg-slate-700 hover:bg-slate-600 text-white font-medium px-4 py-2 rounded-lg text-sm flex items-center gap-2 transition">
          <i class="fa-solid fa-book"></i> API Docs
        </a>
      </div>
    </header>

    <!-- AI Warning Banner (Shown on 401 Unauthorized or Unhealthy AI Provider) -->
    <div id="ai-warning-banner" class="hidden card p-4 bg-rose-950/40 border-rose-700 text-rose-200 text-sm flex items-start gap-3">
      <i class="fa-solid fa-triangle-exclamation text-rose-400 text-xl mt-0.5"></i>
      <div class="flex-1 space-y-1">
        <p class="font-bold text-white text-base" id="ai-warning-title">AI Provider Authentication Issue</p>
        <p class="text-xs text-rose-300 leading-relaxed" id="ai-warning-msg">
          Groq API returned an authentication error (401 Unauthorized). Please check your GROQ_API_KEY at console.groq.com/keys.
        </p>
      </div>
      <a href="https://console.groq.com/keys" target="_blank" rel="noopener noreferrer" class="text-xs bg-rose-800 hover:bg-rose-700 text-white font-semibold px-3 py-1.5 rounded transition whitespace-nowrap flex items-center gap-1.5">
        <span>Groq Console</span>
        <i class="fa-solid fa-arrow-up-right-from-square"></i>
      </a>
    </div>

    <!-- Navigation Tabs -->
    <div class="flex border-b border-slate-700 gap-6 text-sm font-medium overflow-x-auto">
      <button onclick="switchTab('jobs-tab')" id="tab-jobs-btn" class="tab-btn pb-3 text-indigo-400 border-b-2 border-indigo-400 flex items-center gap-2 whitespace-nowrap">
        <i class="fa-solid fa-briefcase"></i> Discovered Jobs
      </button>
      <button onclick="switchTab('sources-tab')" id="tab-sources-btn" class="tab-btn pb-3 text-slate-400 hover:text-white flex items-center gap-2 whitespace-nowrap">
        <i class="fa-solid fa-network-wired"></i> Sources & Capabilities
      </button>
      <button onclick="switchTab('matches-tab')" id="tab-matches-btn" class="tab-btn pb-3 text-slate-400 hover:text-white flex items-center gap-2 whitespace-nowrap">
        <i class="fa-solid fa-bullseye"></i> Matches & Scores
      </button>
      <button onclick="switchTab('applications-tab')" id="tab-apps-btn" class="tab-btn pb-3 text-slate-400 hover:text-white flex items-center gap-2 whitespace-nowrap">
        <i class="fa-solid fa-file-signature"></i> Applications & Approvals
      </button>
      <button onclick="switchTab('profile-tab')" id="tab-profile-btn" class="tab-btn pb-3 text-slate-400 hover:text-white flex items-center gap-2 whitespace-nowrap">
        <i class="fa-solid fa-user"></i> Candidate Profile
      </button>
    </div>

    <!-- TAB 1: Discovered Jobs -->
    <div id="jobs-tab" class="tab-content space-y-4">
      <!-- Direct Job URL Import Card -->
      <div class="card p-4 space-y-3 bg-slate-800/80 border-indigo-900/50">
        <div class="flex items-center justify-between">
          <span class="text-sm font-semibold text-indigo-300 flex items-center gap-2">
            <i class="fa-solid fa-link"></i> Import Job Link (LinkedIn, Internshala, Glassdoor, Greenhouse, Lever, Ashby, or Employer Career Page)
          </span>
          <span class="text-xs text-slate-400">Strictly legal & ToS compliant</span>
        </div>
        <div class="flex flex-col sm:flex-row gap-2">
          <input type="url" id="import-url-input" placeholder="Paste job URL (e.g. https://www.linkedin.com/jobs/view/... or https://boards.greenhouse.io/...)" class="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-4 py-2 text-sm text-white focus:outline-none focus:border-indigo-500">
          <button onclick="importJobLink()" class="bg-indigo-600 hover:bg-indigo-500 text-white font-medium px-5 py-2 rounded-lg text-sm flex items-center justify-center gap-2 transition">
            <i class="fa-solid fa-file-import"></i> Import Job
          </button>
        </div>
      </div>

      <!-- Search & Filters -->
      <div class="card p-4 flex flex-col md:flex-row gap-3 items-center">
        <div class="relative flex-1 w-full">
          <i class="fa-solid fa-magnifying-glass absolute left-3 top-3 text-slate-400"></i>
          <input type="text" id="job-search-input" onkeydown="if(event.key === 'Enter') loadJobs()" placeholder="Search title, company, skills... (Press Enter)" class="w-full bg-slate-900 border border-slate-700 rounded-lg pl-10 pr-4 py-2 text-sm text-white focus:outline-none focus:border-indigo-500">
        </div>
        <select id="work-mode-select" onchange="loadJobs()" class="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500">
          <option value="">All Work Modes</option>
          <option value="remote">Remote (Worldwide)</option>
          <option value="hybrid">Hybrid</option>
          <option value="on-site">On-site</option>
        </select>
        <select id="job-sort-select" onchange="loadJobs()" class="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500">
          <option value="fresher_first">Fresher / Entry Priority</option>
          <option value="newest">Newest First</option>
          <option value="relevance">Relevance</option>
        </select>
        <label class="flex items-center gap-2 text-xs text-indigo-300 font-medium whitespace-nowrap cursor-pointer">
          <input type="checkbox" id="fresher-only-checkbox" onchange="loadJobs()" class="rounded bg-slate-900 border-slate-700 text-indigo-600 focus:ring-0">
          <i class="fa-solid fa-graduation-cap"></i> Fresher / Intern Only
        </label>
        <button onclick="loadJobs()" class="bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition">
          <i class="fa-solid fa-filter mr-1"></i> Filter
        </button>
      </div>

      <div id="jobs-container" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <!-- Loaded dynamically -->
        <div class="card p-6 text-center text-slate-400 col-span-full">Loading vacancies...</div>
      </div>
    </div>

    <!-- TAB 2: Sources & Capability Matrix -->
    <div id="sources-tab" class="tab-content hidden space-y-4">
      <div class="card p-4 bg-slate-800/80 text-sm text-slate-300">
        <h2 class="text-lg font-bold text-white flex items-center gap-2 mb-1">
          <i class="fa-solid fa-scale-balanced text-indigo-400"></i> Source Capabilities & Legal Compliance Matrix
        </h2>
        <p class="text-xs text-slate-400">Discovery is strictly separated from application submission. Sources requiring anti-scraping compliance are supported via authorized Job-Link Import.</p>
      </div>

      <div id="sources-container" class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <!-- Loaded dynamically -->
        <div class="card p-6 text-center text-slate-400 col-span-full">Loading source matrix...</div>
      </div>
    </div>

    <!-- TAB 3: Matches & Scores -->
    <div id="matches-tab" class="tab-content hidden space-y-4">
      <div class="card p-3 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
        <span class="text-sm font-semibold text-slate-300">
          <i class="fa-solid fa-filter text-indigo-400 mr-1.5"></i> Filter by Match Category
        </span>
        <select id="match-status-filter" onchange="loadMatches()" class="bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500">
          <option value="">All Categories (STRONG_MATCH, PARTIAL_MATCH, NEEDS_REVIEW, INELIGIBLE)</option>
          <option value="STRONG_MATCH">STRONG_MATCH</option>
          <option value="PARTIAL_MATCH">PARTIAL_MATCH</option>
          <option value="NEEDS_REVIEW">NEEDS_REVIEW</option>
          <option value="INELIGIBLE">INELIGIBLE</option>
        </select>
      </div>
      <div id="matches-container" class="space-y-4">
        <div class="card p-6 text-center text-slate-400">No match assessments yet. Click 'Match' on any discovered job!</div>
      </div>
    </div>

    <!-- TAB 4: Applications & Approvals -->
    <div id="applications-tab" class="tab-content hidden space-y-4">
      <div class="card p-4 bg-amber-950/30 border-amber-800 text-amber-200 text-sm flex items-center gap-3">
        <i class="fa-solid fa-shield-halved text-amber-400 text-lg"></i>
        <span><strong>Strict Human-in-the-Loop Gate:</strong> Browser automation only dry-runs and fills forms. No application is ever submitted without your explicit one-click authorization.</span>
      </div>
      <div id="apps-container" class="space-y-4">
        <div class="card p-6 text-center text-slate-400">No applications initiated yet.</div>
      </div>
    </div>

    <!-- TAB 5: Profile & Resumes -->
    <div id="profile-tab" class="tab-content hidden space-y-4">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div class="card p-6 space-y-4">
          <h2 class="text-xl font-bold flex items-center gap-2"><i class="fa-solid fa-id-card text-indigo-400"></i> Candidate Details</h2>
          <div class="space-y-3 text-sm">
            <div>
              <label class="text-slate-400">Full Name</label>
              <input id="prof-name" class="w-full bg-slate-900 border border-slate-700 rounded p-2 text-white mt-1">
            </div>
            <div>
              <label class="text-slate-400">Email Address</label>
              <input id="prof-email" class="w-full bg-slate-900 border border-slate-700 rounded p-2 text-white mt-1">
            </div>
            <div>
              <label class="text-slate-400">Years of Experience</label>
              <input id="prof-exp" type="number" step="0.5" class="w-full bg-slate-900 border border-slate-700 rounded p-2 text-white mt-1">
            </div>
            <div>
              <label class="text-slate-400">Verified Skills (comma separated)</label>
              <input id="prof-skills" class="w-full bg-slate-900 border border-slate-700 rounded p-2 text-white mt-1">
            </div>
            <button onclick="saveProfile()" class="w-full bg-indigo-600 hover:bg-indigo-500 text-white font-medium py-2 rounded transition">Save Profile Changes</button>
          </div>
        </div>

        <div class="card p-6 space-y-4">
          <h2 class="text-xl font-bold flex items-center gap-2"><i class="fa-solid fa-file-pdf text-rose-400"></i> Resume Document Manager</h2>
          <div class="border-2 border-dashed border-slate-700 rounded-lg p-6 text-center space-y-3">
            <input type="file" id="resume-file-input" class="hidden" onchange="uploadResume()">
            <i class="fa-solid fa-cloud-arrow-up text-3xl text-slate-500"></i>
            <p class="text-sm text-slate-300">Upload PDF or Text Resume</p>
            <button onclick="document.getElementById('resume-file-input').click()" class="bg-slate-700 hover:bg-slate-600 text-white text-xs px-4 py-2 rounded">Select File</button>
          </div>
          <div id="resumes-list" class="space-y-2">
            <!-- Resumes dynamically loaded -->
          </div>
        </div>

        <!-- AI Profile Intelligence Card -->
        <div class="card p-6 space-y-4 md:col-span-2">
          <div class="flex items-center justify-between">
            <div>
              <h2 class="text-xl font-bold flex items-center gap-2">
                <i class="fa-solid fa-wand-magic-sparkles text-amber-400"></i> AI Profile Intelligence & Completeness Audit
              </h2>
              <p class="text-xs text-slate-400 mt-1">Audit your profile completeness, standardize skill naming, and discover complementary technologies.</p>
            </div>
            <div class="flex items-center gap-2">
              <button id="revert-profile-btn" onclick="revertProfile()" class="hidden bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 text-xs px-3 py-1.5 rounded transition">
                <i class="fa-solid fa-rotate-left mr-1"></i> Undo Last Changes
              </button>
              <button onclick="runProfileAudit()" class="bg-amber-600 hover:bg-amber-500 text-white font-medium text-xs px-3 py-1.5 rounded transition flex items-center gap-1.5">
                <i class="fa-solid fa-microchip"></i> Run AI Audit
              </button>
            </div>
          </div>

          <div id="audit-results-container" class="space-y-4 hidden border-t border-slate-800 pt-4">
            <!-- Completeness Bar -->
            <div>
              <div class="flex justify-between text-xs mb-1">
                <span class="text-slate-400">Profile Completeness Score</span>
                <span id="audit-score-text" class="text-white font-semibold">0%</span>
              </div>
              <div class="w-full bg-slate-800 rounded-full h-2.5">
                <div id="audit-score-bar" class="bg-indigo-500 h-2.5 rounded-full transition-all duration-500" style="width: 0%"></div>
              </div>
              <p id="audit-status-badge" class="text-xs text-indigo-400 mt-1"></p>
            </div>

            <!-- Missing Sections & Recommendations -->
            <div id="audit-missing-box" class="p-3 bg-slate-900 border border-slate-800 rounded text-xs space-y-1"></div>

            <!-- Skill Normalization Suggestions -->
            <div id="audit-normalization-box" class="space-y-2">
              <h3 class="text-sm font-semibold text-slate-300 flex items-center gap-1.5">
                <i class="fa-solid fa-spell-check text-indigo-400"></i> Canonical Skill Corrections (Typos & Aliases)
              </h3>
              <div id="audit-norm-list" class="space-y-1.5"></div>
            </div>

            <!-- Recommended Complementary Skills -->
            <div id="audit-recommended-box" class="space-y-2">
              <h3 class="text-sm font-semibold text-slate-300 flex items-center gap-1.5">
                <i class="fa-solid fa-lightbulb text-amber-400"></i> Recommended Skills to Boost Matching
              </h3>
              <div id="audit-rec-pills" class="flex flex-wrap gap-1.5"></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <script>
    function escapeHtml(str) {
      if (!str) return '';
      return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
    }

    async function checkHealth() {
      try {
        const res = await fetch('/api/v1/health/ai');
        const data = await res.json();
        const badge = document.getElementById('ai-status-badge');
        const banner = document.getElementById('ai-warning-banner');
        const warningMsg = document.getElementById('ai-warning-msg');

        if (data.status === 'healthy') {
          badge.className = 'badge bg-emerald-950 text-emerald-300 border border-emerald-700';
          badge.innerHTML = `<i class="fa-solid fa-check mr-1.5"></i> ${(data.provider || 'AI').toUpperCase()} (${data.model || 'model'}) Ready`;
          if (banner) banner.classList.add('hidden');
        } else {
          const is401 = data.http_status === 401 || (data.error && data.error.includes('401')) || (data.actionable_message && data.actionable_message.includes('401'));
          badge.className = 'badge bg-rose-950 text-rose-300 border border-rose-700';
          badge.innerHTML = `<i class="fa-solid fa-triangle-exclamation mr-1.5"></i> ${(data.provider || 'AI').toUpperCase()} ${is401 ? '(401 Unauthorized)' : '(Unhealthy)'}`;
          if (banner) {
            banner.classList.remove('hidden');
            if (data.actionable_message && warningMsg) {
              warningMsg.textContent = data.actionable_message;
            }
          }
        }
      } catch (e) {
        console.error("AI health check error:", e);
        const badge = document.getElementById('ai-status-badge');
        if (badge) {
          badge.className = 'badge bg-rose-950 text-rose-300 border border-rose-700';
          badge.innerHTML = '<i class="fa-solid fa-triangle-exclamation mr-1.5"></i> AI Disconnected';
        }
      }
    }

    async function loadJobs() {
      const q = document.getElementById('job-search-input') ? document.getElementById('job-search-input').value.trim() : '';
      const wm = document.getElementById('work-mode-select') ? document.getElementById('work-mode-select').value : '';
      const sortBy = document.getElementById('job-sort-select') ? document.getElementById('job-sort-select').value : 'fresher_first';
      const fresherOnly = document.getElementById('fresher-only-checkbox') ? document.getElementById('fresher-only-checkbox').checked : false;

      const container = document.getElementById('jobs-container');
      container.innerHTML = `
        <div class="card p-8 text-center text-slate-400 col-span-full">
          <i class="fa-solid fa-spinner fa-spin text-2xl text-indigo-400 mb-3"></i>
          <p class="text-sm">Loading job vacancies...</p>
        </div>
      `;

      let url = `/api/v1/jobs?query=${encodeURIComponent(q)}&sort_by=${encodeURIComponent(sortBy)}&page_size=30`;
      if (wm) url += `&work_mode=${encodeURIComponent(wm)}`;
      if (fresherOnly) url += `&fresher_only=true`;

      try {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`Server returned HTTP ${res.status}`);
        const data = await res.json();
        container.innerHTML = '';

        if (!data.items || data.items.length === 0) {
          container.innerHTML = `
            <div class="card p-8 text-center text-slate-400 col-span-full space-y-2">
              <i class="fa-solid fa-inbox text-3xl text-slate-500 mb-1"></i>
              <p class="text-base font-semibold text-slate-300">No jobs match your filter criteria.</p>
              <p class="text-xs text-slate-400">Try clearing filters or click "Sync Jobs" to fetch fresh listings.</p>
            </div>
          `;
          return;
        }

        data.items.forEach(job => {
          const card = document.createElement('div');
          card.className = 'card p-5 flex flex-col justify-between space-y-4 hover:border-slate-500 transition';

          // Detect work mode badge
          const locLower = (job.location || '').toLowerCase();
          const descLower = (job.description || '').toLowerCase();
          let wmBadge = '';
          if (locLower.includes('remote') || descLower.includes('remote') || job.source === 'remoteok') {
            wmBadge = '<span class="badge bg-emerald-950/80 text-emerald-300 border border-emerald-700"><i class="fa-solid fa-house-laptop mr-1"></i> Remote</span>';
          } else if (locLower.includes('hybrid') || descLower.includes('hybrid')) {
            wmBadge = '<span class="badge bg-sky-950/80 text-sky-300 border border-sky-700"><i class="fa-solid fa-building-user mr-1"></i> Hybrid</span>';
          } else {
            wmBadge = '<span class="badge bg-slate-800 text-slate-300 border border-slate-700"><i class="fa-solid fa-building mr-1"></i> On-site</span>';
          }

          // Detect experience / fresher badge
          const titleLower = (job.title || '').toLowerCase();
          const expLower = (job.experience_level || '').toLowerCase();
          let expBadge = '';
          if (titleLower.includes('intern') || titleLower.includes('fresher') || titleLower.includes('trainee') || titleLower.includes('graduate') || expLower.includes('intern') || expLower.includes('entry')) {
            expBadge = '<span class="badge bg-emerald-950 text-emerald-300 border border-emerald-700"><i class="fa-solid fa-graduation-cap mr-1"></i> Fresher / Intern</span>';
          } else if (titleLower.includes('junior') || titleLower.includes('entry') || titleLower.includes('associate')) {
            expBadge = '<span class="badge bg-sky-950 text-sky-300 border border-sky-700"><i class="fa-solid fa-seedling mr-1"></i> Junior / Entry</span>';
          } else if (titleLower.includes('senior') || titleLower.includes('lead') || titleLower.includes('principal') || titleLower.includes('staff') || titleLower.includes('director')) {
            expBadge = '<span class="badge bg-amber-950/70 text-amber-300 border border-amber-700"><i class="fa-solid fa-user-tie mr-1"></i> Senior Role</span>';
          }

          // Match score badge
          let matchBadge = '';
          if (job.match_score !== null && job.match_score !== undefined) {
            let scoreColor = job.match_score >= 70 ? 'bg-emerald-950 text-emerald-300 border-emerald-700' : (job.match_score >= 40 ? 'bg-sky-950 text-sky-300 border-sky-700' : 'bg-amber-950 text-amber-300 border-amber-700');
            matchBadge = `<span class="badge ${scoreColor} border">${job.match_score}% • ${escapeHtml(job.match_status || 'MATCH')}</span>`;
          }

          card.innerHTML = `
            <div>
              <div class="flex flex-wrap items-center justify-between gap-1.5 pb-1">
                <div class="flex items-center gap-1.5 flex-wrap">
                  <span class="badge bg-slate-800 text-indigo-400 border border-slate-700 uppercase font-mono text-[10px]">${escapeHtml(job.source)}</span>
                  ${wmBadge}
                  ${expBadge}
                </div>
                ${matchBadge}
              </div>

              <h3 class="text-base font-bold text-white mt-2 leading-snug">
                <a href="${escapeHtml(job.application_url)}" target="_blank" rel="noopener noreferrer" class="hover:text-indigo-400 transition inline-flex items-center gap-1.5 group">
                  <span>${escapeHtml(job.title)}</span>
                  <i class="fa-solid fa-arrow-up-right-from-square text-xs text-slate-500 group-hover:text-indigo-400"></i>
                </a>
              </h3>

              <div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-300 mt-1.5">
                <span class="font-medium text-slate-200"><i class="fa-regular fa-building text-slate-400 mr-1"></i>${escapeHtml(job.company)}</span>
                <span class="text-slate-400"><i class="fa-solid fa-location-dot text-slate-500 mr-1"></i>${escapeHtml(job.location || 'Remote / Worldwide')}</span>
                ${job.experience_level ? `<span class="text-slate-400"><i class="fa-solid fa-briefcase text-slate-500 mr-1"></i>${escapeHtml(job.experience_level)}</span>` : ''}
              </div>

              <p class="text-xs text-slate-400 mt-2.5 line-clamp-3 leading-relaxed">${escapeHtml(job.description)}</p>
            </div>

            <div class="pt-3 border-t border-slate-800 flex items-center justify-between gap-2">
              <button onclick="evaluateJob(${job.id})" class="text-xs bg-indigo-900/60 hover:bg-indigo-800 text-indigo-200 border border-indigo-700 px-3 py-1.5 rounded font-medium transition flex items-center gap-1">
                <i class="fa-solid fa-scale-balanced"></i> Match
              </button>
              <button onclick="generateDraft(${job.id})" class="text-xs bg-emerald-900/60 hover:bg-emerald-800 text-emerald-200 border border-emerald-700 px-3 py-1.5 rounded font-medium transition flex items-center gap-1">
                <i class="fa-solid fa-feather"></i> Letter
              </button>
              <button onclick="prepareApply(${job.id})" class="text-xs bg-amber-900/60 hover:bg-amber-800 text-amber-200 border border-amber-700 px-3 py-1.5 rounded font-medium transition flex items-center gap-1">
                <i class="fa-solid fa-paper-plane"></i> Apply
              </button>
            </div>
          `;
          container.appendChild(card);
        });
      } catch (err) {
        container.innerHTML = `
          <div class="card p-6 text-center text-rose-300 border-rose-800 col-span-full space-y-2">
            <i class="fa-solid fa-circle-exclamation text-2xl mb-1"></i>
            <p class="font-semibold text-white">Failed to retrieve job vacancies</p>
            <p class="text-xs text-slate-400">${escapeHtml(err.message)}</p>
            <button onclick="loadJobs()" class="mt-2 bg-slate-700 hover:bg-slate-600 text-white text-xs px-4 py-2 rounded transition">Retry</button>
          </div>
        `;
      }
    }

    async function importJobLink() {
      const urlInput = document.getElementById('import-url-input');
      const url = urlInput.value.trim();
      if (!url) {
        alert('Please paste a valid job vacancy URL.');
        return;
      }
      try {
        const res = await fetch('/api/v1/jobs/import', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: url })
        });
        const data = await res.json();
        if (res.ok) {
          alert(`Success! Imported '${data.title}' at '${data.company}' from source [${data.source}].`);
          urlInput.value = '';
          loadJobs();
        } else {
          alert(`Import failed: ${data.detail || 'Could not import job link.'}`);
        }
      } catch (e) {
        alert(`Error importing link: ${e}`);
      }
    }

    async function loadSources() {
      const res = await fetch('/api/v1/jobs/sources');
      const sources = await res.json();
      const container = document.getElementById('sources-container');
      container.innerHTML = '';
      sources.forEach(s => {
        const card = document.createElement('div');
        card.className = 'card p-5 space-y-3';
        const catBadge = s.category === 'api' ? 'bg-sky-950 text-sky-300 border-sky-800' : (s.category === 'ats' ? 'bg-purple-950 text-purple-300 border-purple-800' : 'bg-amber-950 text-amber-300 border-amber-800');
        card.innerHTML = `
          <div class="flex items-center justify-between">
            <h3 class="text-base font-bold text-white flex items-center gap-2">
              <i class="fa-solid fa-circle-check text-emerald-400"></i> ${s.display_name}
            </h3>
            <span class="badge ${catBadge} border uppercase">${s.category}</span>
          </div>
          <p class="text-xs text-slate-400">${s.compliance_policy}</p>
          <div class="grid grid-cols-2 gap-2 text-xs pt-2 border-t border-slate-800">
            <div class="${s.supports_job_fetching ? 'text-emerald-400' : 'text-slate-500'}">
              <i class="fa-solid ${s.supports_job_fetching ? 'fa-check' : 'fa-xmark'} mr-1"></i> Auto Job Fetching
            </div>
            <div class="${s.supports_link_import ? 'text-emerald-400' : 'text-slate-500'}">
              <i class="fa-solid ${s.supports_link_import ? 'fa-check' : 'fa-xmark'} mr-1"></i> Job-Link Import
            </div>
            <div class="${s.supports_form_filling ? 'text-emerald-400' : 'text-slate-500'}">
              <i class="fa-solid ${s.supports_form_filling ? 'fa-check' : 'fa-xmark'} mr-1"></i> Form Pre-Filling
            </div>
            <div class="${s.supports_confirmed_submission ? 'text-emerald-400' : 'text-slate-500'}">
              <i class="fa-solid ${s.supports_confirmed_submission ? 'fa-check' : 'fa-xmark'} mr-1"></i> Submission Verification
            </div>
          </div>
        `;
        container.appendChild(card);
      });
    }

    async function evaluateJob(id) {
      alert("Evaluating job match with deterministic rules & AI...");
      const res = await fetch(`/api/v1/matching/evaluate/${id}`, { method: 'POST' });
      const data = await res.json();
      alert(`Job Match Score: ${data.overall_score}% (${data.status})\n\nRationale:\n${data.rationale}`);
      loadMatches();
      switchTab('matches-tab');
    }

    async function generateDraft(id) {
      alert("Generating tailored cover letter via configured AI provider...");
      const res = await fetch(`/api/v1/content/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: id, draft_type: "cover_letter" })
      });
      const data = await res.json();
      alert(`Cover Letter Generated!\n\nSubject: ${data.subject}\n\nPreview:\n${data.content.substring(0, 300)}...`);
    }

    async function prepareApply(id) {
      if (!confirm("This will launch Playwright to fill form fields in DRY-RUN mode. No submission occurs without your confirmation. Proceed?")) return;
      const res = await fetch(`/api/v1/applications/prepare`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: id })
      });
      const data = await res.json();
      alert(`Dry-run status: ${data.status}\nLast Step: ${data.last_step}\n\n${data.message}`);
      loadApplications();
      switchTab('applications-tab');
    }

    async function confirmSubmit(appId, jobId) {
      if (!confirm("CONFIRM APPLICATION SUBMISSION: Are you completely certain you want to submit this job application? This action cannot be undone.")) return;
      const res = await fetch(`/api/v1/applications/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: jobId, user_confirmed_submission: true, dry_run: false })
      });
      const data = await res.json();
      alert(`Submission result: ${data.status}\nMessage: ${data.message}`);
      loadApplications();
    }

    async function triggerJobSync() {
      const btn = document.getElementById('sync-jobs-btn') || event.currentTarget;
      const oldHtml = btn.innerHTML;
      btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin mr-1.5"></i> Syncing...';
      btn.disabled = true;
      try {
        const res = await fetch('/api/v1/jobs/sync', { method: 'POST' });
        const data = await res.json();
        const lines = (data.sources || []).map(s => {
          let line = `• ${s.source.toUpperCase()}: ${s.fetched} fetched, ${s.parsed != null ? s.parsed : s.fetched} parsed, ${s.added} newly saved, ${s.duplicate != null ? s.duplicate : 0} duplicate`;
          if (s.rejected) line += `, ${s.rejected} rejected`;
          if (s.error) line += ` [Error: ${s.error}]`;
          return line;
        });
        const summaryText = lines.join(`
`);
        alert(`Job Synchronization Finished!

Ingestion Summary across Enabled Sources:

` + summaryText);
        loadJobs();
      } catch (err) {
        alert(`Job synchronization failed: ${err.message}`);
      } finally {
        btn.innerHTML = oldHtml;
        btn.disabled = false;
      }
    }

    async function loadMatches() {
      const statusSelect = document.getElementById('match-status-filter');
      const statusFilter = statusSelect ? statusSelect.value : '';
      let url = '/api/v1/matching';
      if (statusFilter) url += `?status_filter=${encodeURIComponent(statusFilter)}`;
      const res = await fetch(url);
      const data = await res.json();
      const container = document.getElementById('matches-container');
      container.innerHTML = '';
      if (!data || data.length === 0) {
        container.innerHTML = '<div class="card p-6 text-center text-slate-400">No match records found.</div>';
        return;
      }
      data.forEach(m => {
        const item = document.createElement('div');
        item.className = 'card p-5 space-y-3';
        let color = 'text-rose-400 border-rose-700 bg-rose-950/40';
        if (m.status === 'STRONG_MATCH' || m.status === 'ELIGIBLE') {
          color = 'text-emerald-400 border-emerald-700 bg-emerald-950/40';
        } else if (m.status === 'PARTIAL_MATCH') {
          color = 'text-sky-400 border-sky-700 bg-sky-950/40';
        } else if (m.status === 'NEEDS_REVIEW') {
          color = 'text-amber-400 border-amber-700 bg-amber-950/40';
        }
        let badgesHtml = `<div class="badge ${color} border mt-1">${escapeHtml(m.status)}</div>`;
        if (m.is_fallback) {
          badgesHtml += `<span class="badge bg-amber-950/80 text-amber-300 border border-amber-700 text-[10px] ml-1"><i class="fa-solid fa-calculator"></i> Rule Fallback</span>`;
        } else {
          badgesHtml += `<span class="badge bg-indigo-950/80 text-indigo-300 border border-indigo-700 text-[10px] ml-1"><i class="fa-solid fa-brain"></i> AI Evaluated</span>`;
        }

        let lowInfoHtml = '';
        if (m.low_information_warning) {
          lowInfoHtml = `<div class="p-2 bg-amber-950/30 border border-amber-800/50 rounded text-xs text-amber-300 flex items-center gap-1.5"><i class="fa-solid fa-circle-info text-amber-400"></i> ${escapeHtml(m.low_information_warning)}</div>`;
        }

        let positiveMatchesHtml = '';
        if (m.positive_matches && m.positive_matches.length > 0) {
          positiveMatchesHtml = `<div class="text-xs text-slate-400 flex flex-wrap gap-1 items-center"><span class="text-emerald-400 font-semibold">Matched:</span> ${m.positive_matches.map(s => `<span class="badge bg-emerald-950/60 text-emerald-300 border border-emerald-800 text-[10px]">${escapeHtml(s)}</span>`).join('')}</div>`;
        }

        let missingCriteriaHtml = '';
        if (m.missing_criteria && m.missing_criteria.length > 0) {
          missingCriteriaHtml = `<div class="text-xs text-slate-400 flex flex-wrap gap-1 items-center mt-1"><span class="text-rose-400 font-semibold">Missing:</span> ${m.missing_criteria.map(s => `<span class="badge bg-rose-950/60 text-rose-300 border border-rose-800 text-[10px]">${escapeHtml(s)}</span>`).join('')}</div>`;
        }

        item.innerHTML = `
          <div class="flex items-center justify-between">
            <div>
              <h3 class="font-bold text-white text-lg">${escapeHtml(m.job_title)}</h3>
              <p class="text-sm text-slate-400">${escapeHtml(m.company)} • ${escapeHtml(m.location || 'Remote')}</p>
            </div>
            <div class="text-right">
              <span class="text-2xl font-black ${m.overall_score >= 70 ? 'text-emerald-400' : (m.overall_score >= 35 ? 'text-sky-400' : 'text-amber-400')}">${m.overall_score}%</span>
              <div>${badgesHtml}</div>
            </div>
          </div>
          ${lowInfoHtml}
          <p class="text-sm text-slate-300 leading-relaxed">${escapeHtml(m.rationale)}</p>
          ${positiveMatchesHtml}
          ${missingCriteriaHtml}
          <div class="grid grid-cols-3 gap-2 text-xs pt-2 border-t border-slate-800">
            <div>Skills: <span class="font-bold text-indigo-400">${m.skills_score}%</span></div>
            <div>Experience: <span class="font-bold text-indigo-400">${m.experience_score}%</span></div>
            <div>Education: <span class="font-bold text-indigo-400">${m.education_score}%</span></div>
          </div>
        `;
        container.appendChild(item);
      });
    }

    async function loadApplications() {
      const res = await fetch('/api/v1/applications');
      const data = await res.json();
      const container = document.getElementById('apps-container');
      container.innerHTML = '';
      if (!data || data.length === 0) {
        container.innerHTML = '<div class="card p-6 text-center text-slate-400">No applications initiated yet.</div>';
        return;
      }
      data.forEach(app => {
        const item = document.createElement('div');
        item.className = 'card p-5 flex flex-col md:flex-row md:items-center justify-between gap-4';
        item.innerHTML = `
          <div>
            <div class="flex items-center gap-2">
              <span class="badge bg-slate-800 text-slate-300 border border-slate-700">${escapeHtml(app.status)}</span>
              <span class="text-xs text-slate-400">${escapeHtml(app.created_at || '')}</span>
            </div>
            <h3 class="text-lg font-bold text-white mt-1">${escapeHtml(app.job_title)}</h3>
            <p class="text-sm text-slate-300">${escapeHtml(app.company)}</p>
            <p class="text-xs text-slate-400 mt-1">Last Step: ${escapeHtml(app.last_step || 'Discovered')}</p>
          </div>
          <div class="flex items-center gap-3">
            ${app.status === 'READY_FOR_APPROVAL' ? `
              <button onclick="confirmSubmit(${app.id}, ${app.job_id})" class="bg-emerald-600 hover:bg-emerald-500 text-white font-bold px-4 py-2 rounded text-sm transition">
                <i class="fa-solid fa-check-double mr-1.5"></i> Approve & Submit
              </button>
            ` : ''}
          </div>
        `;
        container.appendChild(item);
      });
    }

    async function loadProfile() {
      const res = await fetch('/api/v1/profile');
      const data = await res.json();
      document.getElementById('prof-name').value = data.full_name || '';
      document.getElementById('prof-email').value = data.email || '';
      document.getElementById('prof-exp').value = data.experience_years || 0;
      document.getElementById('prof-skills').value = (data.skills || []).join(', ');

      const resDocs = await fetch('/api/v1/resumes');
      const docs = await resDocs.json();
      const resList = document.getElementById('resumes-list');
      resList.innerHTML = '';
      docs.forEach(doc => {
        const div = document.createElement('div');
        div.className = 'p-3 bg-slate-900 border border-slate-800 rounded flex items-center justify-between text-sm';
        div.innerHTML = `
          <div class="flex items-center gap-2">
            <i class="fa-solid fa-file-pdf text-rose-400"></i>
            <span class="text-white">${doc.filename}</span>
            ${doc.is_primary ? '<span class="badge bg-indigo-900/60 text-indigo-300 border border-indigo-700">Primary</span>' : ''}
          </div>
          <button onclick="deleteResume(${doc.id})" class="text-slate-500 hover:text-rose-400"><i class="fa-solid fa-trash"></i></button>
        `;
        resList.appendChild(div);
      });
    }

    async function saveProfile() {
      const full_name = document.getElementById('prof-name').value;
      const email = document.getElementById('prof-email').value;
      const experience_years = parseFloat(document.getElementById('prof-exp').value);
      const skills = document.getElementById('prof-skills').value.split(',').map(s => s.trim()).filter(s => s);
      try {
        const res = await fetch('/api/v1/profile', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ full_name, email, experience_years, skills })
        });
        if (!res.ok) {
          let errMsg = `Server returned ${res.status}`;
          try {
            const errData = await res.json();
            errMsg = errData.detail || JSON.stringify(errData);
          } catch(_) {}
          alert(`Profile save failed: ${errMsg}`);
          return;
        }
        alert('Profile saved successfully!');
      } catch (err) {
        alert(`Profile save error: ${err.message}`);
      }
    }

    async function uploadResume() {
      const fileInput = document.getElementById('resume-file-input');
      if (!fileInput.files || fileInput.files.length === 0) return;
      const file = fileInput.files[0];
      const formData = new FormData();
      formData.append('file', file);
      formData.append('is_primary', 'true');
      const res = await fetch('/api/v1/resumes/upload', {
        method: 'POST',
        body: formData,
      });
      if (res.ok) {
        alert('Resume uploaded and parsed successfully!');
        loadProfile();
      } else {
        const err = await res.json();
        alert('Upload failed: ' + (err.detail || 'Unknown error'));
      }
    }

    async function deleteResume(id) {
      if (!confirm('Delete this resume?')) return;
      await fetch(`/api/v1/resumes/${id}`, { method: 'DELETE' });
      loadProfile();
    }

    async function runProfileAudit() {
      const btn = event ? event.target.closest('button') : null;
      if (btn) btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Auditing...';
      try {
        const res = await fetch('/api/v1/profile/audit?use_ai=true');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        const container = document.getElementById('audit-results-container');
        container.classList.remove('hidden');

        // Score
        document.getElementById('audit-score-text').textContent = `${data.completeness_score}%`;
        document.getElementById('audit-score-bar').style.width = `${data.completeness_score}%`;
        document.getElementById('audit-status-badge').textContent = data.completeness_status;

        // Undo button
        const undoBtn = document.getElementById('revert-profile-btn');
        if (data.can_undo) {
          undoBtn.classList.remove('hidden');
        } else {
          undoBtn.classList.add('hidden');
        }

        // Missing & recommendations
        const missBox = document.getElementById('audit-missing-box');
        let missHtml = '';
        if (data.missing_sections && data.missing_sections.length > 0) {
          missHtml += `<p class="text-rose-400 font-semibold mb-1"><i class="fa-solid fa-triangle-exclamation mr-1"></i> Missing Sections: ${data.missing_sections.join(', ')}</p>`;
        } else {
          missHtml += '<p class="text-emerald-400 font-semibold mb-1"><i class="fa-solid fa-circle-check mr-1"></i> All core profile sections present!</p>';
        }
        if (data.recommendations && data.recommendations.length > 0) {
          missHtml += '<ul class="list-disc list-inside text-slate-400 space-y-0.5 mt-1">';
          data.recommendations.forEach(r => missHtml += `<li>${escapeHtml(r)}</li>`);
          missHtml += '</ul>';
        }
        missBox.innerHTML = missHtml;

        // Normalization
        const normList = document.getElementById('audit-norm-list');
        const normBox = document.getElementById('audit-normalization-box');
        if (data.skill_suggestions && data.skill_suggestions.length > 0) {
          normBox.classList.remove('hidden');
          normList.innerHTML = '';
          data.skill_suggestions.forEach(sg => {
            const row = document.createElement('div');
            row.className = 'p-2.5 bg-slate-900 border border-slate-800 rounded flex items-center justify-between text-xs';
            row.innerHTML = `
              <div>
                <span class="line-through text-rose-400 font-mono">${escapeHtml(sg.original_skill)}</span>
                <i class="fa-solid fa-arrow-right mx-1.5 text-slate-500"></i>
                <span class="text-emerald-400 font-semibold font-mono">${escapeHtml(sg.suggested_skill)}</span>
                <span class="badge bg-slate-800 text-slate-400 border border-slate-700 ml-2">${escapeHtml(sg.category)}</span>
                <p class="text-slate-400 mt-0.5">${escapeHtml(sg.reason)}</p>
              </div>
              <button onclick="acceptSkillCorrection('${escapeHtml(sg.original_skill)}', '${escapeHtml(sg.suggested_skill)}')" class="bg-emerald-600/30 hover:bg-emerald-600 text-emerald-300 hover:text-white border border-emerald-600/50 text-xs px-2.5 py-1 rounded transition">
                <i class="fa-solid fa-check mr-1"></i> Accept
              </button>
            `;
            normList.appendChild(row);
          });
        } else {
          normBox.classList.add('hidden');
        }

        // Recommended skills
        const recBox = document.getElementById('audit-recommended-box');
        const recPills = document.getElementById('audit-rec-pills');
        if (data.recommended_skills && data.recommended_skills.length > 0) {
          recBox.classList.remove('hidden');
          recPills.innerHTML = '';
          data.recommended_skills.forEach(skill => {
            const btn = document.createElement('button');
            btn.className = 'badge bg-indigo-950/80 hover:bg-indigo-800 text-indigo-300 border border-indigo-700 px-2 py-1 rounded text-xs transition flex items-center gap-1';
            btn.innerHTML = `<i class="fa-solid fa-plus text-indigo-400"></i> ${escapeHtml(skill)}`;
            btn.onclick = () => addRecommendedSkill(skill);
            recPills.appendChild(btn);
          });
        } else {
          recBox.classList.add('hidden');
        }

      } catch (err) {
        alert('Audit failed: ' + err.message);
      } finally {
        if (btn) btn.innerHTML = '<i class="fa-solid fa-microchip"></i> Run AI Audit';
      }
    }

    async function acceptSkillCorrection(orig, sugg) {
      try {
        const payload = { approved_skill_replacements: {} };
        payload.approved_skill_replacements[orig] = sugg;
        const res = await fetch('/api/v1/profile/apply-suggestions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        await loadProfile();
        runProfileAudit();
      } catch (e) {
        alert('Failed to accept skill correction: ' + e.message);
      }
    }

    async function addRecommendedSkill(skill) {
      try {
        const res = await fetch('/api/v1/profile/apply-suggestions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ added_skills: [skill] })
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        await loadProfile();
        runProfileAudit();
      } catch (e) {
        alert('Failed to add skill: ' + e.message);
      }
    }

    async function revertProfile() {
      if (!confirm('Revert profile to previous snapshot?')) return;
      try {
        const res = await fetch('/api/v1/profile/revert', { method: 'POST' });
        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || 'Revert failed');
        }
        alert('Profile reverted successfully!');
        await loadProfile();
        runProfileAudit();
      } catch (e) {
        alert('Undo error: ' + e.message);
      }
    }

    function switchTab(tabId) {
      document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
      document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('text-indigo-400', 'border-b-2', 'border-indigo-400');
        btn.classList.add('text-slate-400');
      });
      document.getElementById(tabId).classList.remove('hidden');
      const activeBtn = document.getElementById('tab-' + tabId.replace('-tab', '') + '-btn');
      if (activeBtn) {
        activeBtn.classList.remove('text-slate-400');
        activeBtn.classList.add('text-indigo-400', 'border-b-2', 'border-indigo-400');
      }
      if (tabId === 'sources-tab') loadSources();
      if (tabId === 'matches-tab') loadMatches();
      if (tabId === 'applications-tab') loadApplications();
      if (tabId === 'profile-tab') loadProfile();
    }

    // Initialize
    checkHealth();
    loadJobs();
  </script>
</body>
</html>
"""


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def dashboard_view():
    """Serve the single-page interactive operations dashboard."""
    return DASHBOARD_HTML
