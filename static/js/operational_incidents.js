function initOperationalIncidents() {
    const description = document.getElementById('incidentDescription');
    const counter = document.getElementById('incidentCharCount');
    const photoInput = document.getElementById('incidentPhotos');
    const photoHint = document.getElementById('incidentPhotoHint');
    const form = document.getElementById('incidentReportForm');

    if (description && counter && !description.dataset.bound) {
        description.addEventListener('input', () => {
            counter.textContent = `${description.value.length} characters`;
        });
        description.dataset.bound = 'true';
    }

    if (photoInput && photoHint && !photoInput.dataset.bound) {
        photoInput.addEventListener('change', () => {
            const count = photoInput.files ? photoInput.files.length : 0;
            photoHint.textContent = count ? `${count} photo(s) selected` : '';
        });
        photoInput.dataset.bound = 'true';
    }

    if (form && !form.dataset.bound) {
        form.addEventListener('submit', async (event) => {
            event.preventDefault();

            const title = document.getElementById('incidentTitle')?.value.trim();
            const incidentAt = document.getElementById('incidentDateTime')?.value;
            const type = document.getElementById('incidentType')?.value;
            const priority = document.getElementById('incidentPriority')?.value;
            const location = document.getElementById('incidentLocation')?.value.trim();
            const reporter = document.getElementById('incidentReporter')?.value.trim();
            const descriptionValue = document.getElementById('incidentDescription')?.value.trim();

            if (!title || !incidentAt || !type || !priority || !descriptionValue) {
                alert('Please fill in all required fields.');
                return;
            }

            if (descriptionValue.length < 50) {
                alert('Description must be at least 50 characters.');
                return;
            }

            const formData = new FormData();
            formData.append('title', title);
            formData.append('incident_type', type);
            formData.append('priority', priority);
            formData.append('incident_at', incidentAt);
            formData.append('description', descriptionValue);
            if (location) formData.append('location', location);
            if (reporter) formData.append('reporter_name', reporter);

            const photos = photoInput?.files ? Array.from(photoInput.files) : [];
            photos.forEach(photo => formData.append('photos', photo));

            try {
                const token = localStorage.getItem('access_token');
                const response = await fetch('/api/operational-incidents/', {
                    method: 'POST',
                    headers: token ? { 'Authorization': `Bearer ${token}` } : {},
                    body: formData
                });

                if (!response.ok) {
                    const errorText = await response.text();
                    throw new Error(errorText || 'Failed to submit incident report');
                }

                form.reset();
                if (photoHint) photoHint.textContent = '';
                if (counter) counter.textContent = '0 characters';
                alert('Incident report submitted successfully');
                await loadIncidentReports();
            } catch (err) {
                alert(`Failed to submit incident report: ${err.message || err}`);
            }
        });
        form.dataset.bound = 'true';
    }

    loadIncidentReports();
}

function autoInitOperationalIncidents() {
    const target = document.getElementById('incidentReportForm');
    if (target && !target.dataset.initialized) {
        initOperationalIncidents();
        target.dataset.initialized = 'true';
    }
}

async function loadIncidentReports() {
    const list = document.getElementById('incidentReportList');
    if (!list) return;

    try {
        const token = localStorage.getItem('access_token');
        const response = await fetch('/api/operational-incidents/', {
            headers: token ? { 'Authorization': `Bearer ${token}` } : {}
        });

        if (!response.ok) {
            list.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 2rem; color: #f87171;">Failed to load incidents</div>';
            return;
        }

        const reports = await response.json();
        if (!Array.isArray(reports) || reports.length === 0) {
            list.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 2rem; color: #94a3b8;">No incidents yet</div>';
            return;
        }

        list.innerHTML = reports.map(report => {
            const incidentAt = report.incident_at ? new Date(report.incident_at).toLocaleString() : '-';
            const photos = Array.isArray(report.photos) ? report.photos : [];
            const photoRow = photos.length ? `
                <div style="display: flex; gap: 0.5rem; flex-wrap: wrap; margin-top: 0.5rem;">
                    ${photos.slice(0, 4).map(photo => `
                        <img src="${photo.url}" alt="Incident photo" style="width: 64px; height: 64px; object-fit: cover; border-radius: 6px; border: 1px solid #2a3c66;" />
                    `).join('')}
                    ${photos.length > 4 ? `<span style="color: #94a3b8; align-self: center;">+${photos.length - 4} more</span>` : ''}
                </div>
            ` : '';

            return `
                <div class="job-card" style="border: 1px solid #2a3c66;">
                    <div class="job-header">
                        <div class="job-id">${report.title}</div>
                        <span class="job-status status-ready">${report.priority || 'Priority'}</span>
                    </div>
                    <div class="job-details">
                        <div class="job-detail"><span class="job-label">Type:</span> <span class="job-value">${report.incident_type || '-'}</span></div>
                        <div class="job-detail"><span class="job-label">Time:</span> <span class="job-value">${incidentAt}</span></div>
                        <div class="job-detail"><span class="job-label">Location:</span> <span class="job-value">${report.location || '-'}</span></div>
                        <div class="job-detail"><span class="job-label">Reporter:</span> <span class="job-value">${report.reporter_name || '-'}</span></div>
                    </div>
                    <div style="margin-top: 0.5rem; color: #e2e8f0; line-height: 1.4;">${report.description}</div>
                    ${photoRow}
                </div>
            `;
        }).join('');
    } catch (err) {
        list.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 2rem; color: #f87171;">Failed to load incidents</div>';
    }
}

window.initOperationalIncidents = initOperationalIncidents;
window.loadIncidentReports = loadIncidentReports;
window.autoInitOperationalIncidents = autoInitOperationalIncidents;

document.addEventListener('DOMContentLoaded', () => {
    autoInitOperationalIncidents();
    let attempts = 0;
    const interval = setInterval(() => {
        autoInitOperationalIncidents();
        attempts += 1;
        if (attempts > 10) {
            clearInterval(interval);
        }
    }, 300);
});
