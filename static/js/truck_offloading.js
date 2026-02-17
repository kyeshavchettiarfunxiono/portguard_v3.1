// Truck Offloading (Export) - Truck Unpacking tab

let currentTruckOffloadingId = null;
let currentTruckPhotoStep = null;

function openTruckOffloadingModal() {
    const modal = document.getElementById('truckOffloadingModal');
    if (modal) {
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
        loadTruckClients();
    }
}

function toggleTruckClientMode(mode) {
    const select = document.getElementById('truckClientSelect');
    const manual = document.getElementById('truckClientManual');
    if (!select || !manual) return;
    if (mode === 'manual') {
        select.style.display = 'none';
        manual.style.display = 'block';
    } else {
        select.style.display = 'block';
        manual.style.display = 'none';
    }
}

function closeTruckOffloadingModal() {
    const modal = document.getElementById('truckOffloadingModal');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
        const form = document.getElementById('truckOffloadingForm');
        if (form) form.reset();
    }
}

async function loadTruckClients() {
    try {
        const response = await APP.apiCall('/bookings');
        if (!response?.ok) return;
        const bookings = await response.json();
        const clients = Array.from(new Set(bookings.map(b => b.client).filter(Boolean)));
        const select = document.getElementById('truckClientSelect');
        if (select) {
            select.innerHTML = '<option value="">Select a client</option>' +
                clients.map(c => `<option value="${c}">${c}</option>`).join('');
        }
    } catch (error) {
        console.error('Error loading clients:', error);
    }
}

async function submitTruckOffloading(event) {
    event.preventDefault();

    const payload = {
        truck_registration: document.getElementById('truckRegistration').value.trim(),
        driver_name: document.getElementById('truckDriverName').value.trim(),
        driver_license: document.getElementById('truckDriverLicense').value.trim() || null,
        transporter_name: document.getElementById('truckTransporterName').value.trim(),
        client: document.querySelector('input[name="truckClientMode"]:checked').value === 'manual'
            ? document.getElementById('truckClientManual').value.trim()
            : document.getElementById('truckClientSelect').value,
        delivery_note_number: document.getElementById('truckDeliveryNote').value.trim(),
        commodity_type: document.getElementById('truckCommodityType').value.trim(),
        quantity: parseFloat(document.getElementById('truckQuantity').value || '0'),
        unit: document.getElementById('truckUnit').value,
        horse_registration: document.getElementById('truckHorseRegistration').value.trim() || null,
        notes: document.getElementById('truckNotes').value.trim() || null
    };

    if (!payload.truck_registration || !payload.driver_name || !payload.transporter_name || !payload.client || !payload.delivery_note_number || !payload.commodity_type || !payload.quantity || !payload.unit) {
        APP.showError('Please fill in all required fields');
        return;
    }

    try {
        const response = await fetch('/api/truck-offloading/', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        if (response.ok) {
            const result = await response.json();
            APP.showSuccess(`Truck ${result.truck_registration} registered`);
            closeTruckOffloadingModal();
            loadTruckOffloadingData();
        } else {
            const error = await response.json();
            APP.showError(error.detail || 'Failed to register truck');
        }
    } catch (error) {
        console.error('Error registering truck:', error);
        APP.showError('Error registering truck');
    }
}

async function loadTruckOffloadingData() {
    await Promise.all([
        loadTruckOffloadingList('REGISTERED', 'awaitingTruckUnpackingList'),
        loadTruckOffloadingList('IN_PROGRESS', 'activeTruckUnpackingList'),
        loadTruckOffloadingList('COMPLETED', 'completedTruckUnpackingList')
    ]);
}

async function loadTruckOffloadingList(status, elementId) {
    try {
        const response = await APP.apiCall(`/truck-offloading?status=${status}`);
        if (!response?.ok) return;
        const trucks = await response.json();
        const list = document.getElementById(elementId);
        if (!list) return;

        if (trucks.length === 0) {
            list.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: #888; padding: 2rem;">No trucks</div>';
            return;
        }

        list.innerHTML = trucks.map(t => `
            <div class="job-card">
                <div class="job-header">
                    <div class="job-id">${t.truck_registration}</div>
                    <span class="job-status ${status === 'IN_PROGRESS' ? 'status-in-progress' : status === 'COMPLETED' ? 'status-completed' : 'status-new'}">${status.replace('_', ' ')}</span>
                </div>
                <div class="job-details">
                    <div class="job-detail"><span class="job-label">Driver:</span> <span class="job-value">${t.driver_name}</span></div>
                    <div class="job-detail"><span class="job-label">Client:</span> <span class="job-value">${t.client}</span></div>
                    <div class="job-detail"><span class="job-label">Commodity:</span> <span class="job-value">${t.commodity_type}</span></div>
                </div>
                <div class="job-actions">
                    ${status === 'REGISTERED' ? `<button onclick="startTruckOffloading('${t.id}')">Start Offloading</button>` : ''}
                    ${status === 'IN_PROGRESS' ? `<button onclick="openTruckWorkflow('${t.id}')">Continue</button>` : ''}
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading trucks:', error);
    }
}

async function startTruckOffloading(truckId) {
    try {
        const response = await APP.apiCall(`/truck-offloading/${truckId}/start`, { method: 'POST' });
        if (response?.ok) {
            openTruckWorkflow(truckId);
            loadTruckOffloadingData();
        } else {
            const error = await response.json();
            APP.showError(error.detail || 'Failed to start offloading');
        }
    } catch (error) {
        console.error('Error starting offloading:', error);
        APP.showError('Error starting offloading');
    }
}

async function openTruckWorkflow(truckId) {
    currentTruckOffloadingId = truckId;
    await loadTruckOffloadingDetails(truckId);
    const modal = document.getElementById('truckOffloadingWorkflowModal');
    if (modal) {
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }
}

function closeTruckWorkflow() {
    const modal = document.getElementById('truckOffloadingWorkflowModal');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
}

async function loadTruckOffloadingDetails(truckId) {
    const response = await APP.apiCall(`/truck-offloading/${truckId}`);
    if (!response?.ok) return;
    const truck = await response.json();

    document.getElementById('truckWorkflowId').textContent = truck.truck_registration;
    document.getElementById('truckWorkflowDriver').textContent = truck.driver_name;
    document.getElementById('truckWorkflowClient').textContent = truck.client;
    document.getElementById('truckWorkflowStep').textContent = formatTruckStep(truck.current_step);
    document.getElementById('truckArrivalCount').textContent = `${truck.arrival_photos}/2`;
    document.getElementById('truckDamageCount').textContent = `${truck.damage_photos}/1`;
    document.getElementById('truckOffloadingCount').textContent = `${truck.offloading_photos}/2`;
    document.getElementById('truckCompletionCount').textContent = `${truck.completion_photos}/2`;

    const damageType = document.getElementById('truckDamageType');
    const damageSeverity = document.getElementById('truckDamageSeverity');
    const damageLocation = document.getElementById('truckDamageLocation');
    const damageDescription = document.getElementById('truckDamageDescription');
    if (damageType) damageType.value = truck.damage_type || '';
    if (damageSeverity) damageSeverity.value = truck.damage_severity || '';
    if (damageLocation) damageLocation.value = truck.damage_location || '';
    if (damageDescription) damageDescription.value = truck.damage_description || '';

    const damageDriverName = document.getElementById('truckDamageDriverName');
    const damageDriverComments = document.getElementById('truckDamageDriverComments');
    if (damageDriverName) damageDriverName.value = truck.damage_signoff_name || '';
    if (damageDriverComments) damageDriverComments.value = truck.damage_signoff_comments || '';

    const signoffInput = document.getElementById('truckFinalSignoffName');
    if (signoffInput) signoffInput.value = truck.signoff_name || '';

    const actualQuantity = document.getElementById('truckActualQuantity');
    if (actualQuantity) actualQuantity.value = truck.actual_quantity ?? '';
    const varianceNotes = document.getElementById('truckVarianceNotes');
    if (varianceNotes) varianceNotes.value = truck.variance_notes || '';

    const assessmentStatus = document.getElementById('truckDamageAssessmentStatus');
    if (assessmentStatus) {
        assessmentStatus.textContent = truck.damage_assessment_completed ? 'Completed' : 'Pending';
        assessmentStatus.style.color = truck.damage_assessment_completed ? '#28a745' : '#d9534f';
    }

    updateTruckWorkflowControls(truck);
    return truck;
}

function canAdvanceTruckStep(truck) {
    switch (truck.current_step) {
        case 'ARRIVAL_PHOTOS':
            return (truck.arrival_photos || 0) >= 2;
        case 'DAMAGE_ASSESSMENT':
            return Boolean(truck.damage_assessment_completed);
        case 'OFFLOADING_PHOTOS':
            return (truck.offloading_photos || 0) >= 2;
        case 'COMPLETION_PHOTOS':
            return (truck.completion_photos || 0) >= 2;
        case 'DRIVER_SIGNOFF':
            return Boolean(truck.signoff_name);
        default:
            return false;
    }
}

function updateTruckWorkflowControls(truck) {
    const advanceBtn = document.getElementById('truckAdvanceBtn');
    const completeBtn = document.getElementById('truckCompleteBtn');
    const signoffBtn = document.getElementById('truckSignoffBtn');
    const hint = document.getElementById('truckCompleteHint');

    const isSignoffStep = truck.current_step === 'DRIVER_SIGNOFF';
    const hasSignoff = Boolean(truck.signoff_name);
    const canAdvance = canAdvanceTruckStep(truck);

    if (advanceBtn) advanceBtn.disabled = !canAdvance;
    if (signoffBtn) signoffBtn.disabled = !isSignoffStep;
    if (completeBtn) completeBtn.disabled = !(isSignoffStep && hasSignoff);

    if (hint) {
        if (!isSignoffStep) {
            hint.textContent = 'Complete only after driver sign-off step.';
        } else if (!hasSignoff) {
            hint.textContent = 'Capture driver signature to enable completion.';
        } else {
            hint.textContent = '';
        }
    }
}

function formatTruckStep(step) {
    return step.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, char => char.toUpperCase());
}

function openTruckPhotoModal(step) {
    currentTruckPhotoStep = step;
    const modal = document.getElementById('truckPhotoUploadModal');
    if (modal) {
        modal.style.display = 'flex';
    }
}

function closeTruckPhotoModal() {
    const modal = document.getElementById('truckPhotoUploadModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

async function uploadTruckPhotos() {
    if (!currentTruckOffloadingId || !currentTruckPhotoStep) return;
    const files = document.getElementById('truckPhotoFileInput').files;
    if (!files.length) {
        APP.showError('Please select photos');
        return;
    }

    try {
        for (const file of files) {
            const formData = new FormData();
            formData.append('file', file);
            const response = await fetch(`/api/truck-offloading/${currentTruckOffloadingId}/photo-upload?step=${currentTruckPhotoStep}`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` },
                body: formData
            });
            if (!response.ok) {
                const error = await response.json();
                APP.showError(error.detail || 'Photo upload failed');
                return;
            }
        }
        APP.showSuccess('Media uploaded');
        closeTruckPhotoModal();
        document.getElementById('truckPhotoFileInput').value = '';
        const truck = await loadTruckOffloadingDetails(currentTruckOffloadingId);
        if (truck && truck.current_step === 'COMPLETION_PHOTOS' && canAdvanceTruckStep(truck)) {
            await advanceTruckOffloadingStep();
        }
    } catch (error) {
        console.error('Error uploading photos:', error);
        APP.showError('Error uploading photos');
    }
}

async function advanceTruckOffloadingStep() {
    if (!currentTruckOffloadingId) return;
    const response = await APP.apiCall(`/truck-offloading/${currentTruckOffloadingId}/advance-step`, { method: 'POST' });
    if (response?.ok) {
        await loadTruckOffloadingDetails(currentTruckOffloadingId);
    } else {
        const error = await response.json();
        APP.showError(error.detail || 'Cannot advance step');
    }
}

async function revertTruckOffloadingStep() {
    if (!currentTruckOffloadingId) return;
    const response = await APP.apiCall(`/truck-offloading/${currentTruckOffloadingId}/revert-step`, { method: 'POST' });
    if (response?.ok) {
        await loadTruckOffloadingDetails(currentTruckOffloadingId);
    } else {
        const error = await response.json();
        APP.showError(error.detail || 'Cannot revert step');
    }
}

async function reportTruckDamage() {
    if (!currentTruckOffloadingId) return;
    const damageType = document.getElementById('truckDamageType').value.trim();
    const severity = document.getElementById('truckDamageSeverity').value.trim();
    const location = document.getElementById('truckDamageLocation').value.trim();
    const description = document.getElementById('truckDamageDescription').value.trim();
    if (!damageType || !severity || !location || !description) {
        APP.showError('Please complete all damage details');
        return;
    }
    const response = await APP.apiCall(`/truck-offloading/${currentTruckOffloadingId}/damage-report`, {
        method: 'POST',
        body: JSON.stringify({
            damage_type: damageType,
            severity,
            location,
            description
        })
    });
    if (response?.ok) {
        APP.showSuccess('Damage reported');
        await loadTruckOffloadingDetails(currentTruckOffloadingId);
    } else {
        const error = await response.json();
        APP.showError(error.detail || 'Failed to report damage');
    }
}

async function completeTruckDamageAssessment() {
    if (!currentTruckOffloadingId) return;
    const driverName = document.getElementById('truckDamageDriverName').value.trim();
    const driverComments = document.getElementById('truckDamageDriverComments').value.trim();
    if (!driverName) {
        APP.showError('Please enter driver name for acknowledgement');
        return;
    }
    const response = await APP.apiCall(`/truck-offloading/${currentTruckOffloadingId}/damage-assessment/complete`, {
        method: 'POST',
        body: JSON.stringify({
            driver_name: driverName,
            driver_comments: driverComments || null
        })
    });
    if (response?.ok) {
        APP.showSuccess('Damage assessment completed');
        await loadTruckOffloadingDetails(currentTruckOffloadingId);
    } else {
        const error = await response.json();
        APP.showError(error.detail || 'Failed to complete damage assessment');
    }
}

async function signoffTruck() {
    if (!currentTruckOffloadingId) return;
    const name = document.getElementById('truckFinalSignoffName').value.trim();
    if (!name) {
        APP.showError('Please enter sign-off name');
        return;
    }
    const actualQuantityValue = document.getElementById('truckActualQuantity').value;
    const varianceNotes = document.getElementById('truckVarianceNotes').value.trim();
    const response = await APP.apiCall(`/truck-offloading/${currentTruckOffloadingId}/signoff`, {
        method: 'POST',
        body: JSON.stringify({
            driver_name: name,
            actual_quantity: actualQuantityValue ? parseFloat(actualQuantityValue) : null,
            variance_notes: varianceNotes || null
        })
    });
    if (response?.ok) {
        APP.showSuccess('Driver signed off');
        await loadTruckOffloadingDetails(currentTruckOffloadingId);
    } else {
        const error = await response.json();
        APP.showError(error.detail || 'Failed to sign off');
    }
}

async function completeTruckOffloading() {
    if (!currentTruckOffloadingId) return;
    const truck = await loadTruckOffloadingDetails(currentTruckOffloadingId);
    if (!truck) return;

    if (truck.current_step !== 'DRIVER_SIGNOFF') {
        if (canAdvanceTruckStep(truck)) {
            await advanceTruckOffloadingStep();
            APP.showError('Advance to Driver Signoff before completing.');
        } else {
            APP.showError('Complete only after driver sign-off step.');
        }
        return;
    }

    if (!truck.signoff_name) {
        APP.showError('Capture driver signature to complete.');
        return;
    }

    const response = await APP.apiCall(`/truck-offloading/${currentTruckOffloadingId}/complete`, { method: 'POST' });
    if (response?.ok) {
        APP.showSuccess('Offloading completed');
        closeTruckWorkflow();
        loadTruckOffloadingData();
    } else {
        const error = await response.json();
        APP.showError(error.detail || 'Failed to complete');
    }
}

window.openTruckOffloadingModal = openTruckOffloadingModal;
window.closeTruckOffloadingModal = closeTruckOffloadingModal;
window.submitTruckOffloading = submitTruckOffloading;
window.loadTruckOffloadingData = loadTruckOffloadingData;
window.startTruckOffloading = startTruckOffloading;
window.openTruckWorkflow = openTruckWorkflow;
window.closeTruckWorkflow = closeTruckWorkflow;
window.openTruckPhotoModal = openTruckPhotoModal;
window.closeTruckPhotoModal = closeTruckPhotoModal;
window.uploadTruckPhotos = uploadTruckPhotos;
window.advanceTruckOffloadingStep = advanceTruckOffloadingStep;
window.revertTruckOffloadingStep = revertTruckOffloadingStep;
window.reportTruckDamage = reportTruckDamage;
window.completeTruckDamageAssessment = completeTruckDamageAssessment;
window.signoffTruck = signoffTruck;
window.completeTruckOffloading = completeTruckOffloading;
window.toggleTruckClientMode = toggleTruckClientMode;
