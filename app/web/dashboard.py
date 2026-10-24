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
        <button onclick="triggerJobSync()" class="bg-indigo-600 hover:bg-indigo-500 text-white font-medium px-4 py-2 rounded-lg text-sm flex items-center gap-2 transition">
          <i class="fa-solid fa-rotate"></i> Sync Jobs
        </button>
        <a href="/docs" target="_blank" class="bg-slate-700 hover:bg-slate-600 text-white font-medium px-4 py-2 rounded-lg text-sm flex items-center gap-2 transition">
          <i class="fa-solid fa-book"></i> API Docs
        </a>
      </div>
    </header>

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
          <input type="text" id="job-search-input" placeholder="Search title, company, skills..." class="w-full bg-slate-900 border border-slate-700 rounded-lg pl-10 pr-4 py-2 text-sm text-white focus:outline-none focus:border-indigo-500">
        </div>
        <select id="work-mode-select" class="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-indigo-500">
          <option value="">All Work Modes</option>
          <option value="remote">Remote (Worldwide)</option>
          <option value="hybrid">Hybrid</option>
          <option value="on-site">On-site</option>
        </select>
        <label class="flex items-center gap-2 text-xs text-indigo-300 font-medium whitespace-nowrap cursor-pointer">
          <input type="checkbox" id="fresher-only-checkbox" class="rounded bg-slate-900 border-slate-700 text-indigo-600 focus:ring-0">
          <i class="fa-solid fa-graduation-cap"></i> Fresher / Intern Only
        </label>
        <button onclick="loadJobs()" class="bg-slate-700 hover:bg-slate-600 text-white px-5 py-2 rounded-lg text-sm font-medium whitespace-nowrap">Filter</button>
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
      </div>
    </div>
  </div>

  <script>
    async function checkHealth() {
      try {
        const res = await fetch('/api/v1/health/ai');
        const data = await res.json();
        const badge = document.getElementById('ai-status-badge');
        if (data.status === 'healthy') {
          badge.className = 'badge bg-emerald-950 text-emerald-300 border border-emerald-700';
          badge.innerHTML = `<i class="fa-solid fa-check mr-1.5"></i> ${data.provider.toUpperCase()} (${data.model}) Ready`;
        } else {
          badge.className = 'badge bg-amber-950 text-amber-300 border border-amber-700';
          badge.innerHTML = `<i class="fa-solid fa-triangle-exclamation mr-1.5"></i> ${data.provider.toUpperCase()} (${data.status})`;
        }
      } catch (e) {
        console.error(e);
      }
    }

    async function loadJobs() {
      const q = document.getElementById('job-search-input').value;
      const wm = document.getElementById('work-mode-select') ? document.getElementById('work-mode-select').value : '';
      const fresherOnly = document.getElementById('fresher-only-checkbox') ? document.getElementById('fresher-only-checkbox').checked : false;
      let url = `/api/v1/jobs?query=${encodeURIComponent(q)}&page_size=30`;
      if (wm) url += `&work_mode=${encodeURIComponent(wm)}`;
      if (fresherOnly) url += `&fresher_only=true`;
      const res = await fetch(url);
      const data = await res.json();
      const container = document.getElementById('jobs-container');
      container.innerHTML = '';
      if (!data.items || data.items.length === 0) {
        container.innerHTML = '<div class="card p-6 text-center text-slate-400 col-span-full">No jobs found. Click "Sync Jobs" above to fetch new vacancies or use "Import Job Link".</div>';
        return;
      }
      data.items.forEach(job => {
        const card = document.createElement('div');
        card.className = 'card p-5 flex flex-col justify-between space-y-4 hover:border-slate-600 transition';
        card.innerHTML = `
          <div>
            <div class="flex items-start justify-between gap-2">
              <span class="badge bg-slate-800 text-indigo-400 border border-slate-700 uppercase">${job.source}</span>
              <span class="text-xs text-slate-400">${job.location || 'Remote'}</span>
            </div>
            <h3 class="text-lg font-bold text-white mt-2">${job.title}</h3>
            <p class="text-sm font-medium text-slate-300">${job.company}</p>
            <p class="text-xs text-slate-400 mt-2 line-clamp-3">${job.description}</p>
          </div>
          <div class="pt-3 border-t border-slate-800 flex items-center justify-between gap-2">
            <button onclick="evaluateJob(${job.id})" class="text-xs bg-indigo-900/60 hover:bg-indigo-800 text-indigo-200 border border-indigo-700 px-3 py-1.5 rounded font-medium transition">
              <i class="fa-solid fa-scale-balanced mr-1"></i> Match
            </button>
            <button onclick="generateDraft(${job.id})" class="text-xs bg-emerald-900/60 hover:bg-emerald-800 text-emerald-200 border border-emerald-700 px-3 py-1.5 rounded font-medium transition">
              <i class="fa-solid fa-feather mr-1"></i> Letter
            </button>
            <button onclick="prepareApply(${job.id})" class="text-xs bg-amber-900/60 hover:bg-amber-800 text-amber-200 border border-amber-700 px-3 py-1.5 rounded font-medium transition">
              <i class="fa-solid fa-paper-plane mr-1"></i> Apply
            </button>
          </div>
        `;
        container.appendChild(card);
      });
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
      const btn = event.currentTarget;
      btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Syncing...';
      const res = await fetch('/api/v1/jobs/sync', { method: 'POST' });
      const data = await res.json();
      alert(`Sync finished! Discovered jobs added from: ${data.sources.map(s => s.source + ' (' + s.added + ' added)').join(', ')}`);
      btn.innerHTML = '<i class="fa-solid fa-rotate"></i> Sync Jobs';
      loadJobs();
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
        item.innerHTML = `
          <div class="flex items-center justify-between">
            <div>
              <h3 class="font-bold text-white text-lg">${m.job_title}</h3>
              <p class="text-sm text-slate-400">${m.company}</p>
            </div>
            <div class="text-right">
              <span class="text-2xl font-black ${m.overall_score >= 70 ? 'text-emerald-400' : (m.overall_score >= 35 ? 'text-sky-400' : 'text-amber-400')}">${m.overall_score}%</span>
              <div class="badge ${color} border mt-1">${m.status}</div>
            </div>
          </div>
          <p class="text-sm text-slate-300">${m.rationale}</p>
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
              <span class="badge bg-slate-800 text-slate-300 border border-slate-700">${app.status}</span>
              <span class="text-xs text-slate-400">${app.created_at || ''}</span>
            </div>
            <h3 class="text-lg font-bold text-white mt-1">${app.job_title}</h3>
            <p class="text-sm text-slate-300">${app.company}</p>
            <p class="text-xs text-slate-400 mt-1">Last Step: ${app.last_step || 'Discovered'}</p>
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
      await fetch('/api/v1/profile', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ full_name, email, experience_years, skills })
      });
      alert('Profile saved successfully!');
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
