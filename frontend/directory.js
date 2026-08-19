let currentSkip = 0;
const PAGE_SIZE = 500;
let currentQuery = '';

async function loadDirectory(reset = true) {
  document.getElementById('directoryErrorBox').classList.add('hidden');
  const grid = document.getElementById('directoryGrid');
  const loadMoreBtn = document.getElementById('loadMoreBtn');
  
  if (reset) {
    currentSkip = 0;
    grid.innerHTML = Array(8).fill('<article class="hcp-dir-card loading"><div class="skeleton-lines"></div></article>').join('');
    if (loadMoreBtn) loadMoreBtn.classList.add('hidden');
  } else {
    if (loadMoreBtn) {
      loadMoreBtn.textContent = 'Loading...';
      loadMoreBtn.disabled = true;
    }
  }
  
  let data;
  try {
    data = await api(`/api/hcps?query=${encodeURIComponent(currentQuery)}&skip=${currentSkip}&limit=${PAGE_SIZE}`);
  } catch (e) {
    if (reset) document.getElementById('directoryErrorBox').classList.remove('hidden');
    if (loadMoreBtn) {
      loadMoreBtn.textContent = 'Load More HCPs';
      loadMoreBtn.disabled = false;
    }
    return;
  }
  
  if (!data || data.length === 0) {
    updateSyncStatus(true);
    if (loadMoreBtn) loadMoreBtn.classList.add('hidden');
  } else {
    if (data.length < PAGE_SIZE) {
      if (loadMoreBtn) loadMoreBtn.classList.add('hidden');
    } else {
      if (loadMoreBtn) {
        loadMoreBtn.classList.remove('hidden');
        loadMoreBtn.textContent = 'Load More HCPs';
        loadMoreBtn.disabled = false;
      }
    }
  }

  renderDirectory(data, reset);
}

function loadMore() {
  currentSkip += PAGE_SIZE;
  loadDirectory(false);
}

function renderDirectory(hcps, reset) {
  const grid = document.getElementById('directoryGrid');
  if (reset && (!hcps || hcps.length === 0)) {
    grid.innerHTML = '<div class="empty-state">No HCPs found.</div>';
    return;
  }
  
  if (!hcps || hcps.length === 0) return;

  const html = hcps.map(h => {
    const fullName = `${h.first_name || ''} ${h.last_name || ''}`.trim() || 'Unknown HCP';
    const initial = fullName.charAt(0);
    const score = pct(h.hybrid_engagement_score).toFixed(0);
    const level = h.engagement_level || 'Unknown';
    const levelClass = level.toLowerCase();
    
    return `
      <a href="hcp.html?id=${encodeURIComponent(h.hcp_id || h.HCP_ID)}" class="medielite-card hcp-dir-card">
        <div class="hcp-dir-header">
          <div class="hcp-dir-avatar">${initial}</div>
          <div class="hcp-dir-title">
            <h3>${fullName}</h3>
            <p>${h.specialty || 'General Practice'}</p>
          </div>
        </div>
        <div class="hcp-dir-body">
          <div class="dir-info"><span>ID</span> <b>${h.hcp_id || h.HCP_ID}</b></div>
          <div class="dir-info"><span>Org</span> <b>${h.organization_type || '—'}</b></div>
          <div class="dir-info"><span>Location</span> <b>${[h.city, h.state].filter(Boolean).join(', ') || '—'}</b></div>
        </div>
        <hr class="dashed-line" style="margin: 5px 0 15px; width: 100%;">
        <div class="hcp-dir-footer">
          <div class="dir-score">
            <span>Engagement Score</span>
            <strong>${score}</strong>
          </div>
          <div class="dir-badge level-${levelClass}">${level}</div>
        </div>
      </a>
    `;
  }).join('');

  if (reset) {
    grid.innerHTML = html;
  } else {
    grid.insertAdjacentHTML('beforeend', html);
  }
}

const refreshDirBtn = document.getElementById('refreshDirectoryBtn');
if (refreshDirBtn) refreshDirBtn.addEventListener('click', loadDirectory);

// Wait for script.js to finish setting up
setTimeout(loadDirectory, 50);
