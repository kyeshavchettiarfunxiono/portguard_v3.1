let containerPlanningBookings = [];

function formatClientLabel(value) {
    return String(value || '')
        .trim()
        .replace(/_/g, ' ')
        .replace(/\s+/g, ' ')
        .replace(/\b\w/g, (c) => c.toUpperCase());
}

function getSelectedPlanningDate() {
    const range = document.getElementById('containerPlanningViewRange')?.value || 'today';
    const customInput = document.getElementById('containerPlanningCustomDate');
    const now = new Date();

    if (range === 'tomorrow') {
        now.setDate(now.getDate() + 1);
        return now.toISOString().slice(0, 10);
    }

    if (range === 'custom') {
        return customInput?.value || now.toISOString().slice(0, 10);
    }

    return now.toISOString().slice(0, 10);
}

function setSummaryCards(summary) {
    const planned = document.getElementById('containerPlanningPlannedCount');
    const actual = document.getElementById('containerPlanningActualCount');
    const variance = document.getElementById('containerPlanningVariance');
    const completed = document.getElementById('containerPlanningCompletedCount');

    if (planned) planned.textContent = String(summary?.planned_containers || 0);
    if (actual) actual.textContent = String(summary?.actual_containers || 0);
    if (variance) variance.textContent = String(summary?.variance || 0);
    if (completed) completed.textContent = String(summary?.completed_containers || 0);
}

function renderAnalysisList(plans, planningDate) {
    const list = document.getElementById('containerPlanningAnalysis');
    const title = document.getElementById('containerPlanningAnalysisTitle');
    if (!list) return;

    const dateLabel = new Date(planningDate).toLocaleDateString(undefined, {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
    if (title) {
        title.textContent = `Planned vs Actual Analysis - ${dateLabel}`;
    }

    if (!plans.length) {
        list.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 2rem; color: #6b7280;">No container plans for ${new Date(planningDate).toLocaleDateString()}</div>`;
        return;
    }

    list.innerHTML = plans.map((plan) => {
        const createdAt = plan.created_at ? new Date(plan.created_at).toLocaleString() : '-';
        return `
            <div class="job-card">
                <div class="job-header">
                    <div class="job-id">${plan.vessel_name}</div>
                    <span class="job-status status-ready">${plan.container_type}</span>
                </div>
                <div class="job-details">
                    <div class="job-detail"><span class="job-label">Client:</span> <span class="job-value">${formatClientLabel(plan.client_name)}</span></div>
                    <div class="job-detail"><span class="job-label">Quantity:</span> <span class="job-value">${plan.planned_quantity}</span></div>
                    <div class="job-detail"><span class="job-label">Booking Ref:</span> <span class="job-value">${plan.booking_reference || '-'}</span></div>
                    <div class="job-detail"><span class="job-label">Created:</span> <span class="job-value">${createdAt}</span></div>
                </div>
                <div style="margin-top: 0.6rem; color: #555;">${plan.notes || ''}</div>
                <div class="job-actions" style="margin-top: 0.8rem; display: flex; gap: 0.5rem;">
                    <button class="btn btn-secondary" onclick="deleteContainerPlanningEntry('${plan.id}')">Delete</button>
                </div>
            </div>
        `;
    }).join('');
}

async function loadContainerPlanningSummaryAndList() {
    const planningDate = getSelectedPlanningDate();
    const [summaryResponse, plansResponse] = await Promise.all([
        APP.apiCall(`/container-plans/summary?planning_date=${encodeURIComponent(planningDate)}`),
        APP.apiCall(`/container-plans/?planning_date=${encodeURIComponent(planningDate)}`)
    ]);

    if (!summaryResponse?.ok || !plansResponse?.ok) {
        APP.showError('Failed to load container planning dashboard');
        return;
    }

    const summary = await summaryResponse.json();
    const plans = await plansResponse.json();

    setSummaryCards(summary);
    renderAnalysisList(Array.isArray(plans) ? plans : [], planningDate);
}

async function loadContainerPlanningBookingOptions() {
    const bookingSelect = document.getElementById('containerPlanningBookingId');
    const clientMode = document.getElementById('containerPlanningClientMode');
    if (!bookingSelect || !clientMode) return;

    const response = await APP.apiCall('/container-plans/booking-options');
    if (!response?.ok) return;

    containerPlanningBookings = await response.json();

    bookingSelect.innerHTML = '<option value="">Select from existing vessel bookings</option>' +
        containerPlanningBookings.map((b) => `
            <option value="${b.id}">${b.booking_reference} - ${b.vessel_name} (${formatClientLabel(b.client)})</option>
        `).join('');

    const clients = Array.from(new Set(containerPlanningBookings.map((b) => String(b.client || '').trim()).filter(Boolean)));
    clientMode.innerHTML = clients
        .map((c) => `<option value="${c}">${formatClientLabel(c)}</option>`)
        .join('') + '<option value="CUSTOM" selected>Custom Client</option>';
}

function toggleContainerPlanningForm(forceShow) {
    const section = document.getElementById('containerPlanningFormSection');
    if (!section) return;

    if (typeof forceShow === 'boolean') {
        section.style.display = forceShow ? 'block' : 'none';
        return;
    }

    section.style.display = section.style.display === 'none' || !section.style.display ? 'block' : 'none';
}

function onContainerPlanningBookingSelected() {
    const bookingId = document.getElementById('containerPlanningBookingId')?.value;
    if (!bookingId) return;

    const selected = containerPlanningBookings.find((b) => String(b.id) === String(bookingId));
    if (!selected) return;

    const vesselName = document.getElementById('containerPlanningVesselName');
    const clientMode = document.getElementById('containerPlanningClientMode');
    const clientName = document.getElementById('containerPlanningClientName');
    const containerType = document.getElementById('containerPlanningType');
    const bookingRef = document.getElementById('containerPlanningBookingReference');

    if (vesselName) vesselName.value = selected.vessel_name || '';
    if (clientMode) clientMode.value = selected.client || 'CUSTOM';
    if (clientName) clientName.value = selected.client || '';
    if (containerType) {
        const normalizedType = String(selected.container_type || '').toUpperCase();
        if (normalizedType.includes('20')) containerType.value = '20FT';
        else if (normalizedType.includes('HC')) containerType.value = 'HC';
        else containerType.value = '40FT';
    }
    if (bookingRef) bookingRef.value = selected.booking_reference || '';
}

function onContainerPlanningClientModeChanged() {
    const clientMode = document.getElementById('containerPlanningClientMode')?.value || 'CUSTOM';
    const clientName = document.getElementById('containerPlanningClientName');
    if (!clientName) return;

    if (clientMode === 'CUSTOM') {
        clientName.value = '';
        clientName.placeholder = 'Enter custom client name';
        clientName.readOnly = false;
    } else {
        clientName.value = clientMode;
        clientName.readOnly = true;
    }
}

async function createContainerPlanningEntry(event) {
    event.preventDefault();

    const planningDate = document.getElementById('containerPlanningDate')?.value;
    const bookingIdValue = document.getElementById('containerPlanningBookingId')?.value || null;
    const bookingReference = document.getElementById('containerPlanningBookingReference')?.value?.trim() || null;
    const vesselName = document.getElementById('containerPlanningVesselName')?.value?.trim();
    const clientName = document.getElementById('containerPlanningClientName')?.value?.trim();
    const containerType = document.getElementById('containerPlanningType')?.value;
    const plannedQuantityValue = document.getElementById('containerPlanningQuantity')?.value;
    const notes = document.getElementById('containerPlanningNotes')?.value?.trim() || null;

    if (!planningDate || !vesselName || !clientName || !containerType || !plannedQuantityValue) {
        APP.showError('Please complete all required fields');
        return;
    }

    const payload = {
        planning_date: planningDate,
        booking_id: bookingIdValue || null,
        booking_reference: bookingReference,
        vessel_name: vesselName,
        client_name: clientName,
        container_type: containerType,
        planned_quantity: Number(plannedQuantityValue),
        notes,
    };

    const response = await APP.apiCall('/container-plans/', {
        method: 'POST',
        body: JSON.stringify(payload),
    });

    if (!response?.ok) {
        let detail = 'Failed to create container plan.';
        try {
            const err = await response.json();
            if (err?.detail) detail = typeof err.detail === 'string' ? err.detail : JSON.stringify(err.detail);
        } catch (_error) {}
        APP.showError(detail);
        return;
    }

    APP.showSuccess('Container plan created successfully.');
    const form = document.getElementById('containerPlanningForm');
    if (form) form.reset();

    document.getElementById('containerPlanningDate').value = planningDate;
    onContainerPlanningClientModeChanged();
    await loadContainerPlanningSummaryAndList();
    toggleContainerPlanningForm(false);
}

async function deleteContainerPlanningEntry(planId) {
    const confirmed = confirm('Delete this container plan?');
    if (!confirmed) return;

    const response = await APP.apiCall(`/container-plans/${planId}`, { method: 'DELETE' });
    if (!response?.ok) {
        APP.showError('Failed to delete container plan');
        return;
    }

    APP.showSuccess('Container plan deleted.');
    await loadContainerPlanningSummaryAndList();
}

function onContainerPlanningViewRangeChanged() {
    const range = document.getElementById('containerPlanningViewRange')?.value || 'today';
    const customInput = document.getElementById('containerPlanningCustomDate');
    if (!customInput) return;

    customInput.style.display = range === 'custom' ? 'inline-flex' : 'none';

    if (range !== 'custom') {
        customInput.value = getSelectedPlanningDate();
    }

    loadContainerPlanningSummaryAndList();
}

function attachContainerPlanningHandlers() {
    const viewRange = document.getElementById('containerPlanningViewRange');
    const customDate = document.getElementById('containerPlanningCustomDate');
    const form = document.getElementById('containerPlanningForm');
    const bookingSelect = document.getElementById('containerPlanningBookingId');
    const clientMode = document.getElementById('containerPlanningClientMode');

    if (viewRange && viewRange.dataset.bound !== 'true') {
        viewRange.addEventListener('change', onContainerPlanningViewRangeChanged);
        viewRange.dataset.bound = 'true';
    }

    if (customDate && customDate.dataset.bound !== 'true') {
        customDate.addEventListener('change', () => loadContainerPlanningSummaryAndList());
        customDate.dataset.bound = 'true';
    }

    if (form && form.dataset.bound !== 'true') {
        form.addEventListener('submit', createContainerPlanningEntry);
        form.dataset.bound = 'true';
    }

    if (bookingSelect && bookingSelect.dataset.bound !== 'true') {
        bookingSelect.addEventListener('change', onContainerPlanningBookingSelected);
        bookingSelect.dataset.bound = 'true';
    }

    if (clientMode && clientMode.dataset.bound !== 'true') {
        clientMode.addEventListener('change', onContainerPlanningClientModeChanged);
        clientMode.dataset.bound = 'true';
    }
}

async function loadContainerPlanningBoard() {
    await loadContainerPlanningBookingOptions();

    const selectedDate = getSelectedPlanningDate();
    const planningDateInput = document.getElementById('containerPlanningDate');
    const customDateInput = document.getElementById('containerPlanningCustomDate');

    if (planningDateInput && !planningDateInput.value) {
        planningDateInput.value = selectedDate;
    }
    if (customDateInput && !customDateInput.value) {
        customDateInput.value = selectedDate;
    }

    onContainerPlanningClientModeChanged();
    await loadContainerPlanningSummaryAndList();
}

window.toggleContainerPlanningForm = toggleContainerPlanningForm;
window.loadContainerPlanningBoard = loadContainerPlanningBoard;
window.attachContainerPlanningHandlers = attachContainerPlanningHandlers;
window.deleteContainerPlanningEntry = deleteContainerPlanningEntry;
