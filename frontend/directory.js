async function loadDirectory() {
  document.getElementById('directoryErrorBox').classList.add('hidden');
  const grid = document.getElementById('directoryGrid');
  grid.innerHTML = Array(8).fill('<article class="hcp-dir-card loading"><div class="skeleton-lines"></div></article>').join('');
  
  let data;
  try {
    data = await api('/api/hcps?query=');
  } catch (e) {
    document.getElementById('directoryErrorBox').classList.remove('hidden');
    return;
  }
  
  if (!data || data.length === 0) {
    updateSyncStatus(true);
  }

  renderDirectory(data);
}

function renderDirectory(hcps) {
  const grid = document.getElementById('directoryGrid');
  if (!hcps || hcps.length === 0) {
    grid.innerHTML = '<div class="empty-state">No HCPs found.</div>';
    return;
  }

  grid.innerHTML = hcps.map(h => {
    const fullName = `${h.first_name || ''} ${h.last_name || ''}`.trim() || 'Unknown HCP';
    const initial = fullName.charAt(0);
    const score = pct(h.hybrid_engagement_score).toFixed(0);
    const level = h.engagement_level || 'Unknown';
    const levelClass = level.toLowerCase();
    
    return `
      <a href="hcp.html?id=${encodeURIComponent(h.hcp_id || h.HCP_ID)}" class="hcp-dir-card">
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
        <div class="hcp-dir-footer">
          <div class="dir-score">
            <span>Hybrid Score</span>
            <strong>${score}</strong>
          </div>
          <div class="dir-badge level-${levelClass}">${level}</div>
        </div>
      </a>
    `;
  }).join('');
}

const refreshDirBtn = document.getElementById('refreshDirectoryBtn');
if (refreshDirBtn) refreshDirBtn.addEventListener('click', loadDirectory);

// Wait for script.js to finish setting up
setTimeout(loadDirectory, 50);
