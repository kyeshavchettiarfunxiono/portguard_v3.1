// Backload Truck Packing (Export Truck)

let currentBackloadTruckId = null;
let currentBackloadPhotoStep = null;

function openBackloadTruckModal() {
    const modal = document.getElementById('backloadTruckModal');
    if (modal) {
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
        loadBackloadClients();
    }
}

function closeBackloadTruckModal() {
    const modal = document.getElementById('backloadTruckModal');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
        const form = document.getElementById('backloadTruckForm');
        if (form) form.reset();
    }
}

async function loadBackloadClients() {
    try {
        const response = await APP.apiCall('/bookings');
        if (!response?.ok) return;
        const bookings = await response.json();
        const clients = Array.from(new Set(bookings.map(b => b.client).filter(Boolean)));
        const select = document.getElementById('backloadClient');
        if (select) {
            select.innerHTML = '<option value="">Select a client</option>' +
                clients.map(c => `<option value="${c}">${c}</option>`).join('');
        }
    } catch (error) {
        console.error('Error loading clients:', error);
    }
}

async function submitBackloadTruck(event) {
    event.preventDefault();

    const payload = {
        truck_registration: document.getElementById('backloadTruckRegistration').value.trim(),
        driver_name: document.getElementById('backloadDriverName').value.trim(),
        transporter_name: document.getElementById('backloadTransporterName').value.trim(),
        client: document.getElementById('backloadClient').value,
        cargo_type: document.getElementById('backloadCargoType').value.trim(),
        cargo_description: document.getElementById('backloadCargoDescription').value.trim(),
        delivery_destination: document.getElementById('backloadDeliveryDestination').value.trim(),
        quantity: parseFloat(document.getElementById('backloadQuantity').value || '0'),
        unit: document.getElementById('backloadUnit').value,
        horse_registration: document.getElementById('backloadHorseRegistration').value.trim() || null,
        driver_license: document.getElementById('backloadDriverLicense').value.trim() || null,
        delivery_note_number: document.getElementById('backloadDeliveryNote').value.trim() || null,
        gross_weight: parseFloat(document.getElementById('backloadGrossWeight').value || '0') || null,
        notes: document.getElementById('backloadNotes').value.trim() || null
    };

    if (!payload.truck_registration || !payload.driver_name || !payload.transporter_name || !payload.client ||
        !payload.cargo_type || !payload.cargo_description || !payload.delivery_destination || !payload.quantity || !payload.unit) {
        APP.showError('Please fill in all required fields');
        return;
    }

    try {
        const response = await APP.apiCall('/backload-trucks/', {
            method: 'POST',
            body: JSON.stringify(payload)
        });

        if (response?.ok) {
            const result = await response.json();
            APP.showSuccess(`Truck ${result.truck_registration} registered`);
            closeBackloadTruckModal();
            loadBackloadTruckData();
        } else {
            const error = await response.json();
            APP.showError(error.detail || 'Failed to register truck');
        }
    } catch (error) {
        console.error('Error registering truck:', error);
        APP.showError('Error registering truck');
    }
}

async function loadBackloadTruckData() {
    await Promise.all([
        loadBackloadTruckList('REGISTERED', 'newBackloadTruckList'),
        loadBackloadTruckList('IN_PROGRESS', 'activeBackloadTruckList'),
        loadBackloadTruckList('COMPLETED', 'completedBackloadTruckList')
    ]);
}

async function loadBackloadTruckList(status, elementId) {
    try {
        const response = await APP.apiCall(`/backload-trucks?status=${status}`);
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
                    <div class="job-detail"><span class="job-label">Cargo:</span> <span class="job-value">${t.cargo_type}</span></div>
                </div>
                <div class="job-actions">
                    ${status === 'REGISTERED' ? `<button onclick="startBackloadTruck('${t.id}')">Start Packing</button>` : ''}
                    ${status === 'IN_PROGRESS' ? `<button onclick="openBackloadWorkflow('${t.id}')">Continue</button>` : ''}
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading backload trucks:', error);
    }
}

async function startBackloadTruck(truckId) {
    try {
        const response = await APP.apiCall(`/backload-trucks/${truckId}/start`, { method: 'POST' });
        if (response?.ok) {
            openBackloadWorkflow(truckId);
            loadBackloadTruckData();
        } else {
            const error = await response.json();
            APP.showError(error.detail || 'Failed to start packing');
        }
    } catch (error) {
        console.error('Error starting packing:', error);
        APP.showError('Error starting packing');
    }
}

async function openBackloadWorkflow(truckId) {
    currentBackloadTruckId = truckId;
    await loadBackloadDetails(truckId);
    const modal = document.getElementById('backloadWorkflowModal');
    if (modal) {
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }
}

function closeBackloadWorkflow() {
    const modal = document.getElementById('backloadWorkflowModal');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = 'auto';
    }
}

async function loadBackloadDetails(truckId) {
    const response = await APP.apiCall(`/backload-trucks/${truckId}`);
    if (!response?.ok) return;
    const truck = await response.json();

    document.getElementById('backloadWorkflowId').textContent = truck.truck_registration;
    document.getElementById('backloadWorkflowDriver').textContent = truck.driver_name;
    document.getElementById('backloadWorkflowClient').textContent = truck.client;
    document.getElementById('backloadWorkflowStep').textContent = formatBackloadStep(truck.current_step);
    document.getElementById('backloadBeforeCount').textContent = `${truck.before_photos}/2`;
    document.getElementById('backloadPackingCount').textContent = `${truck.packing_photos}/2`;
    document.getElementById('backloadAfterCount').textContent = `${truck.after_photos}/2`;

    const totalWeight = document.getElementById('backloadTotalWeight');
    if (totalWeight) totalWeight.value = truck.total_cargo_weight ?? '';
    const transferOrder = document.getElementById('backloadTransferOrder');
    if (transferOrder) transferOrder.value = truck.transfer_order_number || '';

    const signoffInput = document.getElementById('backloadSignoffName');
    if (signoffInput) signoffInput.value = truck.signoff_name || '';

    renderBackloadItems(truck.items || []);
    updateBackloadWorkflowControls(truck);
    return truck;
}

function canAdvanceBackloadStep(truck) {
    switch (truck.current_step) {
        case 'BEFORE_PHOTOS':
            return (truck.before_photos || 0) >= 2;
        case 'MANIFEST_WEIGHTS':
            return (truck.items || []).length > 0 && Boolean(truck.total_cargo_weight);
        case 'PACKING_PHOTOS':
            return (truck.packing_photos || 0) >= 2;
        case 'AFTER_PHOTOS':
            return (truck.after_photos || 0) >= 2;
        case 'DRIVER_SIGNOFF':
            return Boolean(truck.signoff_name);
        default:
            return false;
    }
}

function updateBackloadWorkflowControls(truck) {
    const proceedBtn = document.getElementById('backloadProceedBtn');
    const advanceBtn = document.getElementById('backloadAdvanceBtn');
    const completeBtn = document.getElementById('backloadCompleteBtn');
    const signoffBtn = document.getElementById('backloadSignoffBtn');
    const hint = document.getElementById('backloadCompleteHint');

    const isManifest = truck.current_step === 'MANIFEST_WEIGHTS';
    const isSignoff = truck.current_step === 'DRIVER_SIGNOFF';
    const canAdvance = canAdvanceBackloadStep(truck);

    if (proceedBtn) proceedBtn.disabled = !(isManifest && canAdvance);
    if (advanceBtn) advanceBtn.disabled = !canAdvance;
    if (signoffBtn) signoffBtn.disabled = !isSignoff;
    if (completeBtn) completeBtn.disabled = !(isSignoff && Boolean(truck.signoff_name));

    if (hint) {
        let blockedReason = '';
        if (!canAdvance) {
            switch (truck.current_step) {
                case 'BEFORE_PHOTOS':
                    blockedReason = 'Add 2 before photos to advance.';
                    break;
                case 'MANIFEST_WEIGHTS':
                    if ((truck.items || []).length === 0) {
                        blockedReason = 'Add at least 1 manifest item to advance.';
                    } else if (!truck.total_cargo_weight) {
                        blockedReason = 'Enter total cargo weight to advance.';
                    }
                    break;
                case 'PACKING_PHOTOS':
                    blockedReason = 'Add 2 packing photos to advance.';
                    break;
                case 'AFTER_PHOTOS':
                    blockedReason = 'Add 2 after photos to advance.';
                    break;
                case 'DRIVER_SIGNOFF':
                    if (!truck.signoff_name) {
                        blockedReason = 'Capture driver signature to complete.';
                    }
                    break;
                default:
                    break;
            }
        } else if (!isSignoff) {
            blockedReason = 'Complete only after driver sign-off step.';
        }

        hint.textContent = blockedReason;
        hint.style.display = blockedReason ? 'inline-flex' : 'none';
    }
}

function renderBackloadItems(items) {
    const container = document.getElementById('backloadManifestItems');
    if (!container) return;

    if (!items.length) {
        container.innerHTML = '<div style="text-align: center; color: #888; padding: 1rem;">No items added yet</div>';
        return;
    }

    container.innerHTML = `
        <table style="width: 100%; border-collapse: collapse;">
            <thead>
                <tr style="text-align: left; border-bottom: 1px solid #e0e0e0;">
                    <th style="padding: 0.5rem;">Description</th>
                    <th style="padding: 0.5rem;">Qty</th>
                    <th style="padding: 0.5rem;">Unit</th>
                    <th style="padding: 0.5rem;">Weight (kg)</th>
                </tr>
            </thead>
            <tbody>
                ${items.map(item => `
                    <tr style="border-bottom: 1px solid #f0f0f0;">
                        <td style="padding: 0.5rem;">${item.description}</td>
                        <td style="padding: 0.5rem;">${item.quantity}</td>
                        <td style="padding: 0.5rem;">${item.unit}</td>
                        <td style="padding: 0.5rem;">${item.weight_kg}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

function openBackloadPhotoModal(step) {
    currentBackloadPhotoStep = step;
    const modal = document.getElementById('backloadPhotoUploadModal');
    if (modal) {
        modal.style.display = 'flex';
    }
}

function closeBackloadPhotoModal() {
    const modal = document.getElementById('backloadPhotoUploadModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

async function uploadBackloadPhotos() {
    if (!currentBackloadTruckId || !currentBackloadPhotoStep) return;
    const files = document.getElementById('backloadPhotoFileInput').files;
    if (!files.length) {
        APP.showError('Please select photos');
        return;
    }

    try {
        for (const file of files) {
            const formData = new FormData();
            formData.append('file', file);
            const response = await fetch(`/api/backload-trucks/${currentBackloadTruckId}/photo-upload?step=${currentBackloadPhotoStep}`, {
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
        APP.showSuccess('Photos uploaded');
        closeBackloadPhotoModal();
        document.getElementById('backloadPhotoFileInput').value = '';
        const truck = await loadBackloadDetails(currentBackloadTruckId);
        if (truck && canAdvanceBackloadStep(truck) && truck.current_step === 'AFTER_PHOTOS') {
            await advanceBackloadStep();
        }
    } catch (error) {
        console.error('Error uploading photos:', error);
        APP.showError('Error uploading photos');
    }
}

async function addBackloadManifestItem() {
    if (!currentBackloadTruckId) return;
    const description = document.getElementById('backloadItemDescription').value.trim();
    const quantityValue = document.getElementById('backloadItemQuantity').value;
    const unit = document.getElementById('backloadItemUnit').value.trim();
    const weightValue = document.getElementById('backloadItemWeight').value;

    if (!description || !quantityValue || !unit || !weightValue) {
        APP.showError('Please fill all item fields');
        return;
    }

    const response = await APP.apiCall(`/backload-trucks/${currentBackloadTruckId}/manifest/items`, {
        method: 'POST',
        body: JSON.stringify({
            description,
            quantity: parseFloat(quantityValue),
            unit,
            weight_kg: parseFloat(weightValue)
        })
    });

    if (response?.ok) {
        APP.showSuccess('Item added');
        document.getElementById('backloadItemDescription').value = '';
        document.getElementById('backloadItemQuantity').value = '';
        document.getElementById('backloadItemUnit').value = '';
        document.getElementById('backloadItemWeight').value = '';
        await loadBackloadDetails(currentBackloadTruckId);
    } else {
        const error = await response.json();
        APP.showError(error.detail || 'Failed to add item');
    }
}

async function saveBackloadManifest() {
    if (!currentBackloadTruckId) return;
    const totalWeightValue = document.getElementById('backloadTotalWeight').value;
    if (!totalWeightValue) {
        APP.showError('Please enter total cargo weight');
        return;
    }

    const response = await APP.apiCall(`/backload-trucks/${currentBackloadTruckId}/manifest`, {
        method: 'POST',
        body: JSON.stringify({
            total_cargo_weight: parseFloat(totalWeightValue),
            transfer_order_number: document.getElementById('backloadTransferOrder').value.trim() || null
        })
    });

    if (response?.ok) {
        APP.showSuccess('Manifest saved');
        await loadBackloadDetails(currentBackloadTruckId);
    } else {
        const error = await response.json();
        APP.showError(error.detail || 'Failed to save manifest');
    }
}

async function advanceBackloadStep() {
    if (!currentBackloadTruckId) return;
    const response = await APP.apiCall(`/backload-trucks/${currentBackloadTruckId}/advance-step`, { method: 'POST' });
    if (response?.ok) {
        await loadBackloadDetails(currentBackloadTruckId);
    } else {
        const error = await response.json();
        APP.showError(error.detail || 'Cannot advance step');
    }
}

async function revertBackloadStep() {
    if (!currentBackloadTruckId) return;
    const response = await APP.apiCall(`/backload-trucks/${currentBackloadTruckId}/revert-step`, { method: 'POST' });
    if (response?.ok) {
        await loadBackloadDetails(currentBackloadTruckId);
    } else {
        const error = await response.json();
        APP.showError(error.detail || 'Cannot revert step');
    }
}

async function signoffBackloadTruck() {
    if (!currentBackloadTruckId) return;
    const name = document.getElementById('backloadSignoffName').value.trim();
    if (!name) {
        APP.showError('Please enter driver name');
        return;
    }
    const response = await APP.apiCall(`/backload-trucks/${currentBackloadTruckId}/signoff`, {
        method: 'POST',
        body: JSON.stringify({ driver_name: name })
    });
    if (response?.ok) {
        APP.showSuccess('Driver signed off');
        await loadBackloadDetails(currentBackloadTruckId);
    } else {
        const error = await response.json();
        APP.showError(error.detail || 'Failed to sign off');
    }
}

async function completeBackloadTruck() {
    if (!currentBackloadTruckId) return;
    const truck = await loadBackloadDetails(currentBackloadTruckId);
    if (!truck) return;

    if (truck.current_step !== 'DRIVER_SIGNOFF') {
        if (canAdvanceBackloadStep(truck)) {
            await advanceBackloadStep();
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

    const response = await APP.apiCall(`/backload-trucks/${currentBackloadTruckId}/complete`, { method: 'POST' });
    if (response?.ok) {
        APP.showSuccess('Packing completed');
        closeBackloadWorkflow();
        loadBackloadTruckData();
    } else {
        const error = await response.json();
        APP.showError(error.detail || 'Failed to complete');
    }
}

function formatBackloadStep(step) {
    return step.replace(/_/g, ' ').toLowerCase().replace(/\b\w/g, char => char.toUpperCase());
}

window.openBackloadTruckModal = openBackloadTruckModal;
window.closeBackloadTruckModal = closeBackloadTruckModal;
window.submitBackloadTruck = submitBackloadTruck;
window.loadBackloadTruckData = loadBackloadTruckData;
window.startBackloadTruck = startBackloadTruck;
window.openBackloadWorkflow = openBackloadWorkflow;
window.closeBackloadWorkflow = closeBackloadWorkflow;
window.openBackloadPhotoModal = openBackloadPhotoModal;
window.closeBackloadPhotoModal = closeBackloadPhotoModal;
window.uploadBackloadPhotos = uploadBackloadPhotos;
window.addBackloadManifestItem = addBackloadManifestItem;
window.saveBackloadManifest = saveBackloadManifest;
window.advanceBackloadStep = advanceBackloadStep;
window.revertBackloadStep = revertBackloadStep;
window.signoffBackloadTruck = signoffBackloadTruck;
window.completeBackloadTruck = completeBackloadTruck;
