const API_BASE_URL = window.API_BASE_URL || localStorage.getItem('HCP_API_BASE_URL') || 'http://13.235.49.213:8000';
let charts = [];
let searchTimer;
let isOfflineMode = false;
const channels = ['Email', 'Website', 'Webinar', 'Veeva'];

const MOCK_DASHBOARD = {
  total_hcps: 1248,
  high_engagement: 412,
  medium_engagement: 586,
  low_engagement: 250,
  average_engagement_score: 78.4,
  last_updated: new Date().toISOString(),
  engagement_distribution: { High: 412, Medium: 586, Low: 250 },
  score_distribution: { '0-20': 45, '21-40': 205, '41-60': 320, '61-80': 438, '81-100': 240 },
  channel_effectiveness: { Email: 68, Website: 84, Webinar: 72, Veeva: 91 },
  channel_allocation: { Email: 20, Website: 28, Webinar: 22, Veeva: 30 }
};

const MOCK_HCPS = [
  { hcp_id: "HCP-1001", name: "Dr. Sarah Jenkins", specialty: "Cardiology", sub_specialty: "Interventional Cardiology", organization_type: "Academic Medical Center", city: "New York", state: "NY", country: "USA", hcp_status: "Active", preferred_language: "English", engagement_level: "High", historical_engagement_score: 82, predicted_engagement_score: 91, hybrid_engagement_score: 87, email_probability: 0.72, website_probability: 0.85, webinar_probability: 0.65, veeva_probability: 0.94, next_best_channel: "Veeva Rep Call", recommendation_reason: "High historical responsiveness to face-to-face Veeva detailings and upcoming clinical trial release." },
  { hcp_id: "HCP-1002", name: "Dr. Marcus Chen", specialty: "Oncology", sub_specialty: "Thoracic Oncology", organization_type: "Cancer Care Network", city: "Boston", state: "MA", country: "USA", hcp_status: "Active", preferred_language: "English", engagement_level: "High", historical_engagement_score: 88, predicted_engagement_score: 95, hybrid_engagement_score: 92, email_probability: 0.64, website_probability: 0.89, webinar_probability: 0.91, veeva_probability: 0.78, next_best_channel: "Webinar", recommendation_reason: "Frequent attendee of peer-led oncology webinars with high completion rate." },
  { hcp_id: "HCP-1003", name: "Dr. Elena Rostova", specialty: "Neurology", sub_specialty: "Multiple Sclerosis", organization_type: "Specialty Clinic", city: "Chicago", state: "IL", country: "USA", hcp_status: "Active", preferred_language: "English", engagement_level: "Medium", historical_engagement_score: 61, predicted_engagement_score: 74, hybrid_engagement_score: 68, email_probability: 0.81, website_probability: 0.70, webinar_probability: 0.45, veeva_probability: 0.52, next_best_channel: "Email Newsletter", recommendation_reason: "Prefers concise digital email updates over rep visits during clinic hours." },
  { hcp_id: "HCP-1004", name: "Dr. James Wilson", specialty: "Endocrinology", sub_specialty: "Diabetes Care", organization_type: "Community Hospital", city: "Houston", state: "TX", country: "USA", hcp_status: "Active", preferred_language: "English", engagement_level: "Medium", historical_engagement_score: 55, predicted_engagement_score: 62, hybrid_engagement_score: 59, email_probability: 0.58, website_probability: 0.82, webinar_probability: 0.38, veeva_probability: 0.49, next_best_channel: "Website Portal", recommendation_reason: "Regularly accesses online dosing calculators and medical resources." },
  { hcp_id: "HCP-1005", name: "Dr. Priya Patel", specialty: "Pediatrics", sub_specialty: "Pediatric Asthma", organization_type: "Children's Health System", city: "San Francisco", state: "CA", country: "USA", hcp_status: "Active", preferred_language: "English", engagement_level: "Low", historical_engagement_score: 34, predicted_engagement_score: 42, hybrid_engagement_score: 38, email_probability: 0.42, website_probability: 0.51, webinar_probability: 0.25, veeva_probability: 0.31, next_best_channel: "Email Spotlight", recommendation_reason: "Low baseline interaction; targeted email digests recommended." }
];

function updateSyncStatus(isLive) {
  const el = document.getElementById('apiStatusText');
  if (el) {
    el.textContent = isLive ? 'API connected' : 'Demo Mode (Offline)';
    el.style.color = isLive ? '' : '#e2b340';
  }
}

function handleMock(path) {
  if (path.startsWith('/api/dashboard')) {
    return MOCK_DASHBOARD;
  }
  if (path.startsWith('/api/hcps?query=')) {
    const q = decodeURIComponent(path.split('query=')[1] || '').toLowerCase();
    if (!q) return MOCK_HCPS;
    return MOCK_HCPS.filter(h =>
      (h.name && h.name.toLowerCase().includes(q)) ||
      (h.hcp_id && h.hcp_id.toLowerCase().includes(q)) ||
      (h.specialty && h.specialty.toLowerCase().includes(q))
    );
  }
  if (path.startsWith('/api/hcps/')) {
    const id = decodeURIComponent(path.replace('/api/hcps/', ''));
    const found = MOCK_HCPS.find(h => h.hcp_id.toLowerCase() === id.toLowerCase()) || MOCK_HCPS[0];
    return found;
  }
  return {};
}

async function api(path) {
  if (isOfflineMode) {
    updateSyncStatus(false);
    return handleMock(path);
  }
  try {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), 400);
    const r = await fetch(`${API_BASE_URL}${path}`, { signal: controller.signal });
    clearTimeout(id);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const data = await r.json();
    updateSyncStatus(true);
    return data;
  } catch (e) {
    isOfflineMode = true;
    updateSyncStatus(false);
    return handleMock(path);
  }
}

function num(v) { return Number(v ?? 0); }
function pct(v) { let n = num(v); return n <= 1 && n > 0 ? n * 100 : n; }

function destroyCharts() {
  charts.forEach(c => c.destroy());
  charts = [];
}

function renderKpis(d) {
  const data = [
    ['TOTAL HCPs', d.total_hcps, 'Registered healthcare professionals', '◌'],
    ['HIGH ENGAGEMENT', d.high_engagement, 'High engagement HCPs', '↗'],
    ['MEDIUM ENGAGEMENT', d.medium_engagement, 'Medium engagement HCPs', '≈'],
    ['LOW ENGAGEMENT', d.low_engagement, 'Low engagement HCPs', '↘'],
    ['AVG HYBRID SCORE', d.average_engagement_score, 'Backend-calculated score', '⌁']
  ];
  document.getElementById('kpis').innerHTML = data.map(([t, v, s, i]) => `
    <article class="card kpi">
      <div class="kpi-icon">${i}</div>
      <p>${t}</p>
      <h2>${v ?? '—'}</h2>
      <small>${s}</small>
    </article>
  `).join('');
}

function makeCharts(d) {
  if (typeof Chart === 'undefined') return;
  destroyCharts();
  const dist = d.engagement_distribution || {};
  const engCanvas = document.getElementById('engagementChart');
  if (engCanvas) {
    charts.push(new Chart(engCanvas, {
      type: 'doughnut',
      data: {
        labels: Object.keys(dist),
        datasets: [{
          data: Object.values(dist),
          backgroundColor: ['#5542a5', '#7c88c8', '#d6dbe8'],
          borderWidth: 0,
          borderRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '68%',
        plugins: {
          legend: {
            position: 'bottom',
            labels: { usePointStyle: true, padding: 18, font: { family: 'Poppins' } }
          }
        }
      }
    }));
  }

  const scores = d.score_distribution || {};
  const scoreCanvas = document.getElementById('scoreChart');
  if (scoreCanvas) {
    charts.push(new Chart(scoreCanvas, {
      type: 'bar',
      data: {
        labels: Object.keys(scores),
        datasets: [{
          label: 'HCP count',
          data: Object.values(scores),
          backgroundColor: '#5c61b8',
          borderRadius: 9,
          borderSkipped: false
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { display: false } },
          y: { grid: { color: '#eef0f5' }, beginAtZero: true }
        }
      }
    }));
  }

  const alloc = d.channel_allocation || {};
  const allocCanvas = document.getElementById('allocationChart');
  if (allocCanvas) {
    charts.push(new Chart(allocCanvas, {
      type: 'bar',
      data: {
        labels: channels,
        datasets: [
          { label: 'Baseline', data: [25, 25, 25, 25], backgroundColor: '#bcb5df', borderRadius: 7 },
          { label: 'Model-Driven', data: channels.map(c => pct(alloc[c] ?? alloc[c.toLowerCase()])), backgroundColor: '#ffffff', borderRadius: 7 }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { labels: { color: '#fff', font: { family: 'Poppins' } } } },
        scales: {
          x: { ticks: { color: '#e5e1f7' }, grid: { display: false } },
          y: { beginAtZero: true, max: 100, ticks: { color: '#e5e1f7', callback: v => v + '%' }, grid: { color: '#ffffff18' } }
        }
      }
    }));
  }
}

function renderChannels(d) {
  const values = d.channel_effectiveness || {};
  document.getElementById('channelBars').innerHTML = channels.map(c => {
    const v = pct(values[c] ?? values[c.toLowerCase()]);
    return `
      <div class="channel-item">
        <div class="channel-top">
          <span>${c}</span>
          <span>${v.toFixed(0)}%</span>
        </div>
        <div class="bar-track">
          <div class="bar-fill" style="width:${Math.min(v, 100)}%"></div>
        </div>
      </div>
    `;
  }).join('');
}

function render(d) {
  const errorBox = document.getElementById('errorBox');
  if (errorBox) errorBox.classList.add('hidden');
  renderKpis(d);
  renderChannels(d);
  makeCharts(d);
  document.getElementById('lastUpdated').textContent = d.last_updated ? `Updated ${new Date(d.last_updated).toLocaleTimeString()}` : 'Data updated';
}

async function loadDashboard() {
  document.getElementById('errorBox').classList.add('hidden');
  document.getElementById('kpis').innerHTML = Array(5).fill('<article class="card kpi loading"><p>Loading</p><h2>000</h2></article>').join('');
  const data = await api('/api/dashboard');
  render(data);
}

async function searchHcp(q) {
  const box = document.getElementById('searchResults');
  if (q.length < 2) {
    box.classList.remove('show');
    return;
  }
  const data = await api(`/api/hcps?query=${encodeURIComponent(q)}`);
  const rows = Array.isArray(data) ? data : (data.items || data.results || []);
  box.innerHTML = rows.length ? rows.slice(0, 8).map(h => `
    <a class="search-item" href="hcp.html?id=${encodeURIComponent(h.hcp_id || h.HCP_ID)}">
      <b>${h.name || `${h.first_name || ''} ${h.last_name || ''}`}</b><br>
      <small>${h.hcp_id || h.HCP_ID || ''} · ${h.specialty || ''}</small>
    </a>
  `).join('') : '<div class="search-item">No HCP found</div>';
  box.classList.add('show');
}

function updateActiveNavLink(currentId) {
  const navLinks = document.querySelectorAll('#sidebarNav a');
  navLinks.forEach(link => {
    const href = link.getAttribute('href');
    if (href === `#${currentId}`) {
      link.classList.add('active');
    } else if (href && href.startsWith('#')) {
      link.classList.remove('active');
    }
  });
}

function initNavigation() {
  const navLinks = document.querySelectorAll('#sidebarNav a');
  const sidebar = document.getElementById('sidebar');
  const mobileMenuBtn = document.getElementById('mobileMenuBtn');
  const sidebarOverlay = document.getElementById('sidebarOverlay');

  if (mobileMenuBtn && sidebar && sidebarOverlay) {
    mobileMenuBtn.addEventListener('click', () => {
      sidebar.classList.toggle('open');
      sidebarOverlay.classList.toggle('open');
    });
    sidebarOverlay.addEventListener('click', () => {
      sidebar.classList.remove('open');
      sidebarOverlay.classList.remove('open');
    });
  }

  navLinks.forEach(link => {
    link.addEventListener('click', e => {
      const targetId = link.getAttribute('href');
      if (targetId && targetId.startsWith('#')) {
        e.preventDefault();
        const sectionId = targetId.substring(1);
        const targetSection = document.getElementById(sectionId);
        if (targetSection) {
          if (sidebar) sidebar.classList.remove('open');
          if (sidebarOverlay) sidebarOverlay.classList.remove('open');

          updateActiveNavLink(sectionId);

          const topbarHeight = 90;
          const targetPosition = targetSection.getBoundingClientRect().top + window.pageYOffset - topbarHeight;
          window.scrollTo({ top: Math.max(0, targetPosition), behavior: 'smooth' });
        }
      }
    });
  });

  const navSectionIds = ['overview', 'engagement', 'channels', 'allocation'];
  window.addEventListener('scroll', () => {
    let currentId = 'overview';
    for (let i = navSectionIds.length - 1; i >= 0; i--) {
      const id = navSectionIds[i];
      const sec = document.getElementById(id);
      if (sec && sec.offsetHeight > 0) {
        const rect = sec.getBoundingClientRect();
        if (rect.top <= 200) {
          currentId = id;
          break;
        }
      }
    }
    updateActiveNavLink(currentId);
  }, { passive: true });
}

document.getElementById('hcpSearch').addEventListener('input', e => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => searchHcp(e.target.value.trim()), 300);
});

document.addEventListener('click', e => {
  if (!e.target.closest('.search-wrap')) {
    document.getElementById('searchResults').classList.remove('show');
  }
});

document.getElementById('refreshBtn').addEventListener('click', loadDashboard);

initNavigation();
loadDashboard();
