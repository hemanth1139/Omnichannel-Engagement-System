let currentSkip = 0;
const PAGE_SIZE = 500;
let currentQuery = '';
let allHcps = [];
let activeNbc = 'all';
let activeLevel = 'all';

// Set Export PDF URL dynamically based on current API base
const exportBtn = document.getElementById('exportPdfBtn');
if (exportBtn) {
  exportBtn.href = `${API_BASE_URL}/api/hcps/export/pdf`;
}

async function loadDirectory(reset = true) {
  document.getElementById('directoryErrorBox').classList.add('hidden');
  const grid = document.getElementById('directoryGrid');
  const loadMoreBtn = document.getElementById('loadMoreBtn');

  if (reset) {
    currentSkip = 0;
    grid.innerHTML = Array(8).fill('<article class="hcp-dir-card loading"><div class="skeleton-lines"></div></article>').join('');
    if (loadMoreBtn) loadMoreBtn.classList.add('hidden');
  } else {
    if (loadMoreBtn) { loadMoreBtn.textContent = 'Loading...'; loadMoreBtn.disabled = true; }
  }

  let data;
  try {
    data = await api(`/api/hcps?query=${encodeURIComponent(currentQuery)}&skip=${currentSkip}&limit=${PAGE_SIZE}`);
  } catch (e) {
    if (reset) document.getElementById('directoryErrorBox').classList.remove('hidden');
    if (loadMoreBtn) { loadMoreBtn.textContent = 'Load More HCPs'; loadMoreBtn.disabled = false; }
    return;
  }

  if (reset) { allHcps = data || []; } else { allHcps = allHcps.concat(data || []); }

  if (!data || data.length < PAGE_SIZE) {
    if (loadMoreBtn) loadMoreBtn.classList.add('hidden');
  } else {
    if (loadMoreBtn) { loadMoreBtn.classList.remove('hidden'); loadMoreBtn.textContent = 'Load More HCPs'; loadMoreBtn.disabled = false; }
  }

  applyFilters();
}

function normalizeNbc(str) {
  return (str || '').toLowerCase().replace(/[_ ]/g, '');
}

function applyFilters() {
  let filtered = allHcps;
  if (activeNbc !== 'all') filtered = filtered.filter(h => normalizeNbc(h.next_best_channel) === normalizeNbc(activeNbc));
  if (activeLevel !== 'all') filtered = filtered.filter(h => (h.engagement_level || '').toLowerCase() === activeLevel.toLowerCase());
  renderDirectory(filtered);
  const el = document.getElementById('filterCount');
  if (el) el.textContent = (activeNbc !== 'all' || activeLevel !== 'all') ? `Showing ${filtered.length} of ${allHcps.length} HCPs` : `${allHcps.length} HCPs`;
}

function loadMore() { currentSkip += PAGE_SIZE; loadDirectory(false); }

function renderDirectory(hcps) {
  const grid = document.getElementById('directoryGrid');
  if (!hcps || hcps.length === 0) {
    grid.innerHTML = '<div class="empty-state" style="text-align:center;padding:60px 20px;color:var(--muted);font-size:16px;">No HCPs match the selected filters.</div>';
    return;
  }
  const nbcIcons = {};
  grid.innerHTML = hcps.map(h => {
    const fullName = `${h.first_name || ''} ${h.last_name || ''}`.trim() || 'Unknown HCP';
    const score = pct(h.hybrid_engagement_score).toFixed(0);
    const level = h.engagement_level || 'Unknown';
    const nbc = h.next_best_channel || '';
    const nbcLabel = nbc.replace('_', ' ') || '—';
    return `
      <a href="hcp.html?id=${encodeURIComponent(h.hcp_id || h.HCP_ID)}" class="medielite-card hcp-dir-card">
        <div class="hcp-dir-header">
          <div class="hcp-dir-avatar">${fullName.charAt(0)}</div>
          <div class="hcp-dir-title"><h3>${fullName}</h3><p>${h.specialty || 'General Practice'}</p></div>
        </div>
        <div class="hcp-dir-body">
          <div class="dir-info"><span>ID</span> <b>${h.hcp_id || h.HCP_ID}</b></div>
          <div class="dir-info"><span>Org</span> <b>${h.organization_type || '—'}</b></div>
          <div class="dir-info"><span>Location</span> <b>${[h.city, h.state].filter(Boolean).join(', ') || '—'}</b></div>
          <div class="dir-info"><span>NBC</span> <b class="nbc-tag">${nbcLabel}</b></div>
        </div>
        <hr class="dashed-line" style="margin:5px 0 15px;width:100%;">
        <div class="hcp-dir-footer">
          <div class="dir-score"><span>Engagement Score</span><strong>${score}</strong></div>
          <div class="dir-badge level-${level.toLowerCase()}">${level}</div>
        </div>
      </a>`;
  }).join('');
}

// Filter chip wiring
document.getElementById('nbcFilters').addEventListener('click', e => {
  const btn = e.target.closest('[data-nbc]');
  if (!btn) return;
  document.querySelectorAll('#nbcFilters .chip').forEach(c => c.classList.remove('active'));
  btn.classList.add('active');
  activeNbc = btn.dataset.nbc;
  applyFilters();
});

document.getElementById('levelFilters').addEventListener('click', e => {
  const btn = e.target.closest('[data-level]');
  if (!btn) return;
  document.querySelectorAll('#levelFilters .chip').forEach(c => c.classList.remove('active'));
  btn.classList.add('active');
  activeLevel = btn.dataset.level;
  applyFilters();
});

const refreshDirBtn = document.getElementById('refreshDirectoryBtn');
if (refreshDirBtn) refreshDirBtn.addEventListener('click', () => loadDirectory());

setTimeout(loadDirectory, 50);


