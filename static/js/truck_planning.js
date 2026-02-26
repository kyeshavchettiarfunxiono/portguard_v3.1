async function loadTruckPlanBookings() {
    const bookingSelect = document.getElementById('truckPlanBooking');
    if (!bookingSelect) return;

    const response = await APP.apiCall('/bookings');
    if (!response?.ok) return;

    const bookings = await response.json();
    bookingSelect.innerHTML = '<option value="">Select booking...</option>' + bookings.map((booking) => (
        `<option value="${booking.id}">${booking.booking_reference} - ${booking.vessel_name} (${booking.client})</option>`
    )).join('');
}

function renderTruckPlans(plans) {
    const list = document.getElementById('truckPlanList');
    if (!list) return;

    if (!plans.length) {
        list.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 2rem; color: #888;">No truck plans created yet.</div>';
        return;
    }

    list.innerHTML = plans.map((plan) => {
        const plannedDate = plan.planned_date ? new Date(plan.planned_date).toLocaleString() : '-';
        const createdAt = plan.created_at ? new Date(plan.created_at).toLocaleString() : '-';

        const statusClass = plan.status === 'LOCKED' ? 'status-ready' : 'status-new';
        const finalizeBtn = plan.status === 'DRAFT'
            ? `<button class="btn btn-primary" onclick="finalizeTruckPlan('${plan.id}')">Finalize</button>`
            : '';
        const deleteBtn = plan.status === 'DRAFT'
            ? `<button class="btn btn-secondary" onclick="deleteTruckPlan('${plan.id}')">Delete</button>`
            : '';

        return `
            <div class="job-card">
                <div class="job-header">
                    <div class="job-id">${plan.vessel_name || 'Unknown Vessel'}</div>
                    <span class="job-status ${statusClass}">${plan.status}</span>
                </div>
                <div class="job-details">
                    <div class="job-detail"><span class="job-label">Quantity:</span> <span class="job-value">${plan.planned_quantity}</span></div>
                    <div class="job-detail"><span class="job-label">Planned Date:</span> <span class="job-value">${plannedDate}</span></div>
                    <div class="job-detail"><span class="job-label">Created:</span> <span class="job-value">${createdAt}</span></div>
                </div>
                <div class="job-actions" style="margin-top: 0.9rem; display: flex; gap: 0.6rem;">
                    ${finalizeBtn}
                    ${deleteBtn}
                </div>
            </div>
        `;
    }).join('');
}

async function loadTruckPlans() {
    const response = await APP.apiCall('/plans');
    if (!response?.ok) return;

    const plans = await response.json();
    renderTruckPlans(plans);
}

async function createTruckPlan(event) {
    event.preventDefault();

    const bookingId = document.getElementById('truckPlanBooking')?.value;
    const quantity = Number(document.getElementById('truckPlanQuantity')?.value || 0);
    const plannedDate = document.getElementById('truckPlanDate')?.value;
    const error = document.getElementById('truckPlanError');

    if (error) {
        error.classList.add('is-hidden');
        error.textContent = '';
    }

    if (!bookingId || quantity < 1 || !plannedDate) {
        if (error) {
            error.textContent = 'Please complete all fields.';
            error.classList.remove('is-hidden');
        }
        return;
    }

    const response = await APP.apiCall('/plans', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            booking_id: bookingId,
            planned_quantity: quantity,
            planned_date: plannedDate,
        }),
    });

    if (!response?.ok) {
        let detail = 'Failed to create plan.';
        try {
            const payload = await response.json();
            if (payload?.detail) detail = payload.detail;
        } catch (_err) {}

        if (error) {
            error.textContent = detail;
            error.classList.remove('is-hidden');
        }
        return;
    }

    const form = document.getElementById('truckPlanForm');
    if (form) form.reset();

    await loadTruckPlans();
}

async function finalizeTruckPlan(planId) {
    const response = await APP.apiCall(`/plans/${planId}/finalize`, { method: 'POST' });
    if (response?.ok) {
        await loadTruckPlans();
        return;
    }

    let detail = 'Failed to finalize plan.';
    try {
        const payload = await response.json();
        if (payload?.detail) detail = payload.detail;
    } catch (_err) {}
    alert(detail);
}

async function deleteTruckPlan(planId) {
    const confirmed = confirm('Delete this draft plan?');
    if (!confirmed) return;

    const response = await APP.apiCall(`/plans/${planId}`, { method: 'DELETE' });
    if (response?.ok) {
        await loadTruckPlans();
        return;
    }

    let detail = 'Failed to delete plan.';
    try {
        const payload = await response.json();
        if (payload?.detail) detail = payload.detail;
    } catch (_err) {}
    alert(detail);
}

function attachTruckPlanningHandlers() {
    const form = document.getElementById('truckPlanForm');
    if (form && !form.dataset.bound) {
        form.addEventListener('submit', createTruckPlan);
        form.dataset.bound = 'true';
    }
}

window.loadTruckPlans = loadTruckPlans;
window.loadTruckPlanBookings = loadTruckPlanBookings;
window.attachTruckPlanningHandlers = attachTruckPlanningHandlers;
window.finalizeTruckPlan = finalizeTruckPlan;
window.deleteTruckPlan = deleteTruckPlan;
