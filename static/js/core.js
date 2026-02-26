/**
 * PortGuard CCMS - Operator Dashboard - Core Module
 * Handles initialization, utilities, and API communication
 */

// ============= CONFIGURATION =============
const API_BASE = window.location.origin + '/api';
const AUTH_BASE = window.location.origin + '/auth';
const REFRESH_INTERVALS = {
    DASHBOARD_DATA: 30000,  // 30 seconds
    CONTAINERS: 10000,      // 10 seconds
    NETWORK_STATUS: 5000    // 5 seconds
};

// ============= INITIALIZATION =============
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
    setupEventListeners();
    setupMobileSidebar();
    startAutoRefresh();
});

function initializeApp() {
    console.log('🚀 Initializing PortGuard Operator Dashboard...');
    loadUserProfile();
    loadDashboardData();
    loadContainers();
    updateNetworkStatus();
}

function setupEventListeners() {
    // Sidebar navigation
    document.querySelectorAll('.sidebar-link').forEach(link => {
        link.addEventListener('click', (e) => {
            if (e.currentTarget.onclick) {
                e.currentTarget.onclick();
            }
        });
    });

    // Logout button
    const logoutBtn = document.querySelector('.logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', logout);
    }
}

function setupMobileSidebar() {
    const sidebar = document.querySelector('.sidebar');
    const headerTop = document.querySelector('.header-top');
    if (!sidebar || !headerTop) return;

    let toggleBtn = document.getElementById('mobileSidebarToggle');
    if (!toggleBtn) {
        toggleBtn = document.createElement('button');
        toggleBtn.id = 'mobileSidebarToggle';
        toggleBtn.className = 'mobile-sidebar-toggle';
        toggleBtn.type = 'button';
        toggleBtn.setAttribute('aria-label', 'Toggle navigation menu');
        toggleBtn.innerHTML = '☰';
        headerTop.prepend(toggleBtn);
    }

    let backdrop = document.getElementById('mobileSidebarBackdrop');
    if (!backdrop) {
        backdrop = document.createElement('div');
        backdrop.id = 'mobileSidebarBackdrop';
        backdrop.className = 'sidebar-backdrop';
        document.body.appendChild(backdrop);
    }

    const closeSidebar = () => document.body.classList.remove('sidebar-open');

    if (toggleBtn.dataset.bound !== 'true') {
        toggleBtn.addEventListener('click', () => {
            document.body.classList.toggle('sidebar-open');
        });
        toggleBtn.dataset.bound = 'true';
    }

    if (backdrop.dataset.bound !== 'true') {
        backdrop.addEventListener('click', closeSidebar);
        backdrop.dataset.bound = 'true';
    }

    if (!window.__mobileSidebarEscBound) {
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape') {
                closeSidebar();
            }
        });
        window.__mobileSidebarEscBound = true;
    }

    if (!window.__mobileSidebarResizeBound) {
        window.addEventListener('resize', () => {
            if (window.innerWidth > 1024) {
                closeSidebar();
            }
        });
        window.__mobileSidebarResizeBound = true;
    }

    document.querySelectorAll('.sidebar-link').forEach((link) => {
        if (link.dataset.mobileCloseBound === 'true') return;
        link.addEventListener('click', () => {
            if (window.innerWidth <= 1024) {
                closeSidebar();
            }
        });
        link.dataset.mobileCloseBound = 'true';
    });
}

function startAutoRefresh() {
    setInterval(updateNetworkStatus, REFRESH_INTERVALS.NETWORK_STATUS);
    setInterval(loadDashboardData, REFRESH_INTERVALS.DASHBOARD_DATA);
    setInterval(loadContainers, REFRESH_INTERVALS.CONTAINERS);
}

// ============= USER PROFILE =============
async function loadUserProfile() {
    try {
        const token = localStorage.getItem('access_token');
        if (!token) {
            window.location.href = '/login';
            return;
        }

        const response = await fetch(`${AUTH_BASE}/me`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.ok) {
            const user = await response.json();
            updateProfileDisplay(user);
        } else if (response.status === 401) {
            localStorage.removeItem('access_token');
            window.location.href = '/login';
        }
    } catch (error) {
        console.error('❌ Error loading user profile:', error);
    }
}

function updateProfileDisplay(user) {
    const avatarEl = document.getElementById('profileAvatar');
    const nameEl = document.getElementById('profileName');
    const roleEl = document.getElementById('profileRole');

    if (avatarEl) avatarEl.textContent = user.full_name?.substring(0, 2).toUpperCase() || 'U';
    if (nameEl) nameEl.textContent = user.full_name || 'User';
    if (roleEl) roleEl.textContent = user.role || 'Operator';
}

// ============= NETWORK STATUS =============
async function updateNetworkStatus() {
    try {
        const response = await fetch(`${API_BASE}/health`, {
            timeout: 3000
        });
        setNetworkStatus(response.ok);
    } catch (error) {
        setNetworkStatus(false);
    }
}

function setNetworkStatus(isOnline) {
    const statusEl = document.getElementById('networkStatus');
    if (statusEl) {
        statusEl.className = `network-status ${isOnline ? 'online' : 'offline'}`;
        statusEl.innerHTML = `<span>${isOnline ? 'Online' : 'Offline'}</span>`;
    }
}

// ============= AUTHENTICATION =============
async function logout() {
    try {
        // No server-side logout endpoint; clear client token only.
    } catch (error) {
        console.error('Logout error:', error);
    } finally {
        localStorage.removeItem('access_token');
        window.location.href = '/login';
    }
}

// ============= API UTILITIES =============
async function apiCall(endpoint, options = {}) {
    const token = localStorage.getItem('access_token');
    const url = `${API_BASE}${endpoint}`;
    
    const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        ...options.headers
    };

    try {
        const response = await fetch(url, {
            ...options,
            headers
        });

        if (response.status === 401) {
            localStorage.removeItem('access_token');
            window.location.href = '/login';
            return null;
        }

        return response;
    } catch (error) {
        console.error(`❌ API Error: ${endpoint}`, error);
        throw error;
    }
}

// ============= UTILITY FUNCTIONS =============
function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function formatTime(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function getStatusClass(status) {
    const statusMap = {
        'NEW': 'status-new',
        'PENDING_REVIEW': 'status-new',
        'REGISTERED': 'status-ready',
        'PACKING': 'status-in-progress',
        'UNPACKING': 'status-in-progress',
        'COMPLETED': 'status-completed',
        'IN_USE': 'status-in-progress'
    };
    return statusMap[status] || 'status-new';
}

function getProgressForStatus(status) {
    const progressMap = {
        'NEW': '0%',
        'PENDING_REVIEW': '10%',
        'REGISTERED': '25%',
        'PACKING': '50%',
        'UNPACKING': '65%',
        'COMPLETED': '100%'
    };
    return progressMap[status] || '0%';
}

// ============= ERROR HANDLING =============
function showAlert(message, type = 'info') {
    console.log(`[${type.toUpperCase()}] ${message}`);
    // In production, you might use a toast notification system
    alert(message);
}

function showError(message) {
    showAlert(`❌ ${message}`, 'error');
}

function showSuccess(message) {
    showAlert(`✅ ${message}`, 'success');
}

// Export for use in other modules
window.APP = {
    apiCall,
    loadUserProfile,
    showAlert,
    showError,
    showSuccess,
    formatDate,
    formatTime,
    getStatusClass,
    getProgressForStatus,
    REFRESH_INTERVALS
};
