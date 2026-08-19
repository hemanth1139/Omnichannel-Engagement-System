const API_BASE_URL = window.API_BASE_URL || localStorage.getItem('HCP_API_BASE_URL') || 'https://13.235.49.213.nip.io';
let charts = [];
let searchTimer;
const channels = ['Email', 'Website', 'Webinar', 'Sales_Rep'];

function updateSyncStatus(isLive) {
  const el = document.getElementById('apiStatusText');
  if (el) {
    el.textContent = isLive ? 'API connected' : 'Disconnected';
    el.style.color = isLive ? '' : '#e2b340';
  }
}

async function api(path) {
  try {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), 8000);
    const r = await fetch(`${API_BASE_URL}${path}`, { signal: controller.signal });
    clearTimeout(id);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const data = await r.json();
    updateSyncStatus(true);
    return data;
  } catch (e) {
    updateSyncStatus(false);
    throw e;
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
    ['AVG HYBRID SCORE', num(d.average_engagement_score).toFixed(1), 'Backend-calculated score', '⌁']
  ];
  document.getElementById('kpis').innerHTML = data.map(([t, v, s, i]) => `
    <article class="card kpi">
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

  const rawScores = d.score_distribution || {};
  const isArray = Array.isArray(rawScores);
  const scoreLabels = isArray ? rawScores.map(x => x.bucket || x.Bucket) : Object.keys(rawScores);
  const scoreValues = isArray ? rawScores.map(x => x.count || x.Count) : Object.values(rawScores);

  const scoreCanvas = document.getElementById('scoreChart');
  if (scoreCanvas) {
    charts.push(new Chart(scoreCanvas, {
      type: 'bar',
      data: {
        labels: scoreLabels,
        datasets: [{
          label: 'HCP count',
          data: scoreValues,
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
          { label: 'Baseline Spend', data: [25, 25, 25, 25], backgroundColor: '#bcb5df', borderRadius: 7 },
          { label: 'Optimized Cost', data: channels.map(c => pct(alloc[c] ?? alloc[c.toLowerCase()])), backgroundColor: '#ffffff', borderRadius: 7 }
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
          <span>${c.replace('_', ' ')}</span>
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
  const lastUpdatedEl = document.getElementById('lastUpdated');
  if (lastUpdatedEl) {
    lastUpdatedEl.textContent = d.last_updated ? `Updated ${new Date(d.last_updated).toLocaleTimeString()}` : 'Data updated';
  }
}

async function loadDashboard() {
  document.getElementById('errorBox').classList.add('hidden');
  document.getElementById('kpis').innerHTML = Array(5).fill('<article class="card kpi loading"><p>Loading</p><h2>000</h2></article>').join('');

  try {
    let data = await api('/api/dashboard');
    render(data);
  } catch (e) {
    document.getElementById('errorBox').classList.remove('hidden');
    document.getElementById('kpis').innerHTML = Array(5).fill('<article class="card kpi"><p>Error</p><h2>—</h2></article>').join('');
  }
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
      <b>${h.first_name || ''} ${h.last_name || ''}</b><br>
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

const refreshBtn = document.getElementById('refreshBtn');
if (refreshBtn) refreshBtn.addEventListener('click', loadDashboard);

initNavigation();
if (document.getElementById('kpis')) {
  loadDashboard();
}
