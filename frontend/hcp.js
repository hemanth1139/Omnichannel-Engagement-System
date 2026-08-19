const API_BASE_URL = window.API_BASE_URL || localStorage.getItem('HCP_API_BASE_URL') || 'http://13.235.49.213:8000';
let comparison;

async function api(path) {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), 1800);
  const r = await fetch(`${API_BASE_URL}${path}`, { signal: controller.signal });
  clearTimeout(id);
  if (!r.ok) throw Error(r.status);
  return await r.json();
}

function val(x) { return x === null || x === undefined || x === '' ? 'Not available' : x; }
function pct(v) { let n = Number(v ?? 0); return n > 0 && n <= 1 ? n * 100 : n; }
function info(label, value) { return `<div class="info-item"><label>${label}</label><b>${val(value)}</b></div>`; }

function loadChart(h) {
  if (comparison) comparison.destroy();
  comparison = new Chart(document.getElementById('comparisonChart'), {
    type: 'bar',
    data: {
      labels: ['Historical', 'Predicted', 'Hybrid'],
      datasets: [{
        data: [pct(h.historical_engagement_score), pct(h.predicted_engagement_score), pct(h.hybrid_engagement_score)],
        backgroundColor: ['#c9cee1', '#7776c6', '#4b3999'],
        borderRadius: 8
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: false } },
        y: { beginAtZero: true, max: 100, grid: { color: '#edf0f5' } }
      }
    }
  });
}

function render(h) {
  const fullName = `${h.first_name || ''} ${h.last_name || ''}`.trim() || 'Unknown HCP';
  document.getElementById('hcpName').textContent = val(fullName);
  document.getElementById('hcpId').textContent = val(h.hcp_id || h.HCP_ID);
  document.getElementById('avatar').textContent = fullName.charAt(0) || 'H';
  const level = val(h.engagement_level);
  document.getElementById('levelBadge').textContent = level;
  document.getElementById('profileInfo').classList.remove('skeleton-lines');
  document.getElementById('profileInfo').innerHTML = [
    info('Specialty', h.specialty),
    info('Sub-specialty', h.sub_specialty),
    info('Organization Type', h.organization_type),
    info('Location', [h.city, h.state, h.country].filter(Boolean).join(', ')),
    info('HCP Status', h.hcp_status),
    info('Preferred Language', h.preferred_language)
  ].join('');

  document.getElementById('summary').innerHTML = [
    ['Historical Score', h.historical_engagement_score],
    ['Predicted Score', h.predicted_engagement_score],
    ['Hybrid Engagement', h.hybrid_engagement_score]
  ].map((x, i) => `<div class="metric ${i === 2 ? 'featured' : ''}"><span>${x[0]}</span><strong>${x[1] === null ? '—' : pct(x[1]).toFixed(0)}</strong></div>`).join('');

  const probs = [
    ['Email', h.email_probability],
    ['Website', h.website_probability],
    ['Webinar', h.webinar_probability],
    ['Sales Rep', h.sales_rep_probability]
  ];

  document.getElementById('probabilities').innerHTML = probs.map(([n, v]) => `
    <div class="prob-row">
      <b>${n}</b>
      <div class="bar-track"><div class="bar-fill" style="width:${Math.min(pct(v), 100)}%"></div></div>
      <b>${pct(v).toFixed(0)}%</b>
    </div>
  `).join('');

  document.getElementById('bestChannel').textContent = val(h.next_best_channel);
  document.getElementById('reason').textContent = val(h.recommended_reason);

  loadChart(h);
}

async function loadHcp() {
  document.getElementById('detailError').classList.add('hidden');
  const id = new URLSearchParams(location.search).get('id') || 'HCP-1001';
  try {
    const data = await api(`/api/hcps/${encodeURIComponent(id)}`);
    render(data);
  } catch (e) {
    document.getElementById('detailError').classList.remove('hidden');
  }
}

loadHcp();

