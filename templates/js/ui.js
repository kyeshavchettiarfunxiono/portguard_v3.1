/**
 * PortGuard CCMS - Operator Dashboard - UI Module
 * Handles tab switching, page navigation, and UI state management
 */

// ============= TAB MANAGEMENT =============
function switchTab(tabName) {
    console.log(`📑 Switching to tab: ${tabName}`);

    // Hide all tab content
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
        tab.style.display = 'none';
    });

    // Show selected tab
    const selectedTab = document.getElementById(tabName);
    if (selectedTab) {
        selectedTab.classList.add('active');
        selectedTab.style.display = 'block';
        window.scrollTo(0, 0);

        // Refresh data if needed
        if (tabName === 'active-jobs') {
            loadActiveContainers();
        } else if (tabName === 'new-jobs') {
            loadNewContainers();
        } else if (tabName === 'ready') {
            loadReadyContainers();
        } else if (tabName === 'completed') {
            loadCompletedContainers();
        }
    }

    // Update tab buttons
    document.querySelectorAll('.nav-tab').forEach(btn => {
        btn.classList.remove('active');
        if (btn.textContent.toLowerCase().includes(tabName.split('-')[0])) {
            btn.classList.add('active');
        }
    });
}

// ============= PAGE SWITCHING =============
function switchSidebar(page) {
    console.log(`🔀 Switching page: ${page}`);

    // Hide all main pages
    document.querySelectorAll('[id$="Page"]').forEach(page => {
        page.style.display = 'none';
    });

    // Update sidebar active state
    document.querySelectorAll('.sidebar-link').forEach(link => {
        link.classList.remove('active');
    });

    // Show selected page and mark sidebar item
    switch (page) {
        case 'export-packing':
            toggleExportPackingPage(true);
            document.querySelectorAll('.sidebar-link')[0].classList.add('active');
            break;
        case 'export-truck':
            if (window.TabLoader && typeof TabLoader.switchTab === 'function') {
                TabLoader.switchTab('export_truck');
            } else {
                switchTab('export_truck');
            }
            if (typeof loadBackloadTruckData === 'function') {
                loadBackloadTruckData();
            }
            document.querySelectorAll('.sidebar-link')[1].classList.add('active');
            break;
        case 'import-unpacking':
            toggleImportUnpackingPage(true);
            document.querySelectorAll('.sidebar-link')[2].classList.add('active');
            break;
        case 'truck-unpacking':
            if (window.TabLoader && typeof TabLoader.switchTab === 'function') {
                TabLoader.switchTab('truck_unpacking');
            } else {
                switchTab('truck_unpacking');
            }
            if (typeof loadTruckOffloadingData === 'function') {
                loadTruckOffloadingData();
            }
            document.querySelectorAll('.sidebar-link')[3].classList.add('active');
            break;
        case 'damage-reports':
            switchTab('damage');
            document.querySelectorAll('.sidebar-link')[4].classList.add('active');
            break;
        default:
            // Return to overview
            switchTab('overview');
            document.querySelectorAll('.sidebar-link')[0].classList.add('active');
    }
}

// ============= EXPORT PACKING PAGE =============
function toggleExportPackingPage(show) {
    console.log(`📦 ${show ? 'Opening' : 'Closing'} Export Packing page`);
    
    const page = document.getElementById('exportPackingPage');
    const header = document.querySelector('header');
    const tabs = document.getElementById('overview')?.parentElement || null;

    if (show) {
        if (page) page.style.display = 'block';
        if (header) header.style.display = 'block';
        window.scrollTo(0, 0);
        loadExportPackingData();
    } else {
        if (page) page.style.display = 'none';
        if (header) header.style.display = 'block';
        switchTab('overview');
    }
}

async function loadExportPackingData() {
    try {
        const response = await APP.apiCall('/containers');
        if (response?.ok) {
            const containers = await response.json();
            displayExportPackingContainers(containers);
            updateExportPackingStats(containers);
        }
    } catch (error) {
        console.error('Error loading export packing data:', error);
        APP.showError('Failed to load export containers');
    }
}

function displayExportPackingContainers(containers) {
    // Filter export containers
    const exportContainers = containers.filter(c => 
        c.type && !c.type.includes('FCL')
    );

    // Display ready for work
    const readyList = document.getElementById('exportReadyForWorkList');
    if (readyList) {
        const readyContainers = exportContainers.filter(c => 
            ['REGISTERED', 'PACKING'].includes(c.status)
        );

        if (readyContainers.length === 0) {
            readyList.innerHTML = '<div style="grid-column: 1 / -1; text-align: center; padding: 3rem; color: #888;"><p>No containers ready for work</p></div>';
        } else {
            readyList.innerHTML = readyContainers.map(c => `
                <div class="container-card" onclick="openContainer('${c.id}', 'packing')">
                    <div class="container-card-header">
                        <span class="container-number">${c.container_no}</span>
                        <span class="container-client">${c.client || 'N/A'}</span>
                    </div>
                    <div class="container-card-details">
                        <div>
                            <span>Status:</span>
                            <span>${c.status.replace('_', ' ')}</span>
                        </div>
                        <div>
                            <span>Type:</span>
                            <span>${c.type || 'Standard'}</span>
                        </div>
                    </div>
                    <div class="container-card-footer">
                        <span class="progress-bar">${APP.getProgressForStatus(c.status)}</span>
                        <span>→</span>
                    </div>
                </div>
            `).join('');
        }
    }
}

function updateExportPackingStats(containers) {
    const stats = {
        new: containers.filter(c => c.status === 'PENDING_REVIEW').length,
        ready: containers.filter(c => ['REGISTERED', 'PACKING'].includes(c.status)).length,
        inUse: containers.filter(c => c.assigned_to && c.assigned_to !== 'current_user').length,
        needsRepair: containers.filter(c => c.needs_repair).length
    };

    document.getElementById('exportNewCount').textContent = stats.new;
    document.getElementById('exportReadyCount').textContent = stats.ready;
    document.getElementById('exportInUseCount').textContent = stats.inUse;
    document.getElementById('exportNeedsRepairCount').textContent = stats.needsRepair;
    document.getElementById('exportReadyWorkCount').textContent = stats.ready;
}

// ============= IMPORT UNPACKING PAGE =============
function toggleImportUnpackingPage(show) {
    console.log(`📥 ${show ? 'Opening' : 'Closing'} Import Unpacking page`);
    
    const header = document.querySelector('header');
    const tab = document.getElementById('import-unpacking-tab');

    if (show) {
        // Hide all main content
        document.querySelectorAll('.tab-content').forEach(t => {
            t.style.display = 'none';
            t.classList.remove('active');
        });
        
        if (header) header.style.display = 'block';
        if (tab) {
            tab.style.display = 'block';
            tab.classList.add('active');
        }
        window.scrollTo(0, 0);
        loadAvailableFCLContainers();
    } else {
        if (header) header.style.display = 'block';
        if (tab) {
            tab.style.display = 'none';
            tab.classList.remove('active');
        }
        document.getElementById('overview').style.display = 'block';
        document.getElementById('overview').classList.add('active');
    }
}

// ============= MODAL MANAGEMENT =============
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'flex';
        console.log(`📋 Opened modal: ${modalId}`);
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.style.display = 'none';
        const form = modal.querySelector('form');
        if (form) form.reset();
        console.log(`📋 Closed modal: ${modalId}`);
    }
}

// Close modal when clicking outside
document.addEventListener('click', (e) => {
    if (e.target.id && e.target.style.position === 'fixed' && e.target.style.display === 'flex') {
        const form = e.target.querySelector('form');
        if (form && confirm('Close this dialog without saving?')) {
            closeModal(e.target.id);
        }
    }
});

// ============= DASHBOARD DATA LOADING =============
async function loadDashboardData() {
    try {
        const response = await APP.apiCall('/containers');
        if (response?.ok) {
            const containers = await response.json();
            updateDashboardStats(containers);
            displayActiveJob(containers);
        }
    } catch (error) {
        console.error('Error loading dashboard data:', error);
    }
}

function updateDashboardStats(containers) {
    const stats = {
        total: containers.length,
        pending: containers.filter(c => c.status === 'PENDING_REVIEW').length,
        repairs: containers.filter(c => c.needs_repair).length,
        active: containers.filter(c => c.status === 'PACKING' || c.status === 'UNPACKING').length,
        new: containers.filter(c => c.status === 'PENDING_REVIEW').length,
        ready: containers.filter(c => ['REGISTERED', 'PACKING'].includes(c.status)).length,
        completed: containers.filter(c => c.status === 'COMPLETED').length
    };

    document.getElementById('statTotal').textContent = stats.total;
    document.getElementById('statPending').textContent = stats.pending;
    document.getElementById('statRepairs').textContent = stats.repairs;
    document.getElementById('statActive').textContent = stats.active || '-';
    document.getElementById('countNew').textContent = stats.new;
    document.getElementById('countReady').textContent = stats.ready;
    document.getElementById('countCompleted').textContent = stats.completed;
}

function displayActiveJob(containers) {
    const activeContainer = containers.find(c => 
        c.status === 'PACKING' || c.status === 'UNPACKING'
    );

    const card = document.getElementById('activeJobCard');
    if (!card) return;

    if (activeContainer) {
        document.getElementById('activeJobId').textContent = activeContainer.container_no;
        document.getElementById('activeJobType').textContent = activeContainer.type || 'Unknown';
        document.getElementById('activeJobStatus').textContent = activeContainer.status.replace('_', ' ');
        document.getElementById('activeJobStarted').textContent = APP.formatDate(activeContainer.created_at);
    }
}

// Export for use in other modules
window.UI = {
    switchTab,
    switchSidebar,
    toggleExportPackingPage,
    toggleImportUnpackingPage,
    openModal,
    closeModal
};
