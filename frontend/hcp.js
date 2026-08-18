const API_BASE_URL = window.API_BASE_URL || localStorage.getItem('HCP_API_BASE_URL') || 'http://13.235.49.213:8000';
let comparison;

const MOCK_HCPS_DETAIL = {
  "HCP-1001": { hcp_id: "HCP-1001", name: "Dr. Sarah Jenkins", specialty: "Cardiology", sub_specialty: "Interventional Cardiology", organization_type: "Academic Medical Center", city: "New York", state: "NY", country: "USA", hcp_status: "Active", preferred_language: "English", engagement_level: "High", historical_engagement_score: 82, predicted_engagement_score: 91, hybrid_engagement_score: 87, email_probability: 0.72, website_probability: 0.85, webinar_probability: 0.65, veeva_probability: 0.94, next_best_channel: "Veeva Rep Call", recommendation_reason: "High historical responsiveness to face-to-face Veeva detailings and upcoming clinical trial release." },
  "HCP-1002": { hcp_id: "HCP-1002", name: "Dr. Marcus Chen", specialty: "Oncology", sub_specialty: "Thoracic Oncology", organization_type: "Cancer Care Network", city: "Boston", state: "MA", country: "USA", hcp_status: "Active", preferred_language: "English", engagement_level: "High", historical_engagement_score: 88, predicted_engagement_score: 95, hybrid_engagement_score: 92, email_probability: 0.64, website_probability: 0.89, webinar_probability: 0.91, veeva_probability: 0.78, next_best_channel: "Webinar", recommendation_reason: "Frequent attendee of peer-led oncology webinars with high completion rate." },
  "HCP-1003": { hcp_id: "HCP-1003", name: "Dr. Elena Rostova", specialty: "Neurology", sub_specialty: "Multiple Sclerosis", organization_type: "Specialty Clinic", city: "Chicago", state: "IL", country: "USA", hcp_status: "Active", preferred_language: "English", engagement_level: "Medium", historical_engagement_score: 61, predicted_engagement_score: 74, hybrid_engagement_score: 68, email_probability: 0.81, website_probability: 0.70, webinar_probability: 0.45, veeva_probability: 0.52, next_best_channel: "Email Newsletter", recommendation_reason: "Prefers concise digital email updates over rep visits during clinic hours." },
  "HCP-1004": { hcp_id: "HCP-1004", name: "Dr. James Wilson", specialty: "Endocrinology", sub_specialty: "Diabetes Care", organization_type: "Community Hospital", city: "Houston", state: "TX", country: "USA", hcp_status: "Active", preferred_language: "English", engagement_level: "Medium", historical_engagement_score: 55, predicted_engagement_score: 62, hybrid_engagement_score: 59, email_probability: 0.58, website_probability: 0.82, webinar_probability: 0.38, veeva_probability: 0.49, next_best_channel: "Website Portal", recommendation_reason: "Regularly accesses online dosing calculators and medical resources." },
  "HCP-1005": { hcp_id: "HCP-1005", name: "Dr. Priya Patel", specialty: "Pediatrics", sub_specialty: "Pediatric Asthma", organization_type: "Children's Health System", city: "San Francisco", state: "CA", country: "USA", hcp_status: "Active", preferred_language: "English", engagement_level: "Low", historical_engagement_score: 34, predicted_engagement_score: 42, hybrid_engagement_score: 38, email_probability: 0.42, website_probability: 0.51, webinar_probability: 0.25, veeva_probability: 0.31, next_best_channel: "Email Spotlight", recommendation_reason: "Low baseline interaction; targeted email digests recommended." }
};

async function api(path) {
  try {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), 1800);
    const r = await fetch(`${API_BASE_URL}${path}`, { signal: controller.signal });
    clearTimeout(id);
    if (!r.ok) throw Error(r.status);
    return await r.json();
  } catch (e) {
    const hcpId = path.replace('/api/hcps/', '');
    if (MOCK_HCPS_DETAIL[hcpId]) {
      return MOCK_HCPS_DETAIL[hcpId];
    }
    return Object.values(MOCK_HCPS_DETAIL)[0];
  }
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
        data: [h.historical_engagement_score, h.predicted_engagement_score, h.hybrid_engagement_score],
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
  document.getElementById('hcpName').textContent = val(h.name);
  document.getElementById('hcpId').textContent = val(h.hcp_id || h.HCP_ID);
  document.getElementById('avatar').textContent = (h.name || 'H').charAt(0);
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
  ].map((x, i) => `<div class="metric ${i === 2 ? 'featured' : ''}"><span>${x[0]}</span><strong>${val(x[1])}</strong></div>`).join('');

  const probs = [
    ['Email', h.email_probability],
    ['Website', h.website_probability],
    ['Webinar', h.webinar_probability],
    ['Veeva', h.veeva_probability]
  ];

  document.getElementById('probabilities').innerHTML = probs.map(([n, v]) => `
    <div class="prob-row">
      <b>${n}</b>
      <div class="bar-track"><div class="bar-fill" style="width:${Math.min(pct(v), 100)}%"></div></div>
      <b>${pct(v).toFixed(0)}%</b>
    </div>
  `).join('');

  document.getElementById('bestChannel').textContent = val(h.next_best_channel);
  document.getElementById('reason').textContent = val(h.recommendation_reason);

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

