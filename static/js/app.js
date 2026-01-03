// WebSocket connection
const socket = io();

// State
let currentFilter = 'all';
let requests = [];

// DOM Elements
const connectionStatus = document.getElementById('connectionStatus');
const connectionText = document.getElementById('connectionText');
const requestForm = document.getElementById('requestForm');
const requestsList = document.getElementById('requestsList');
const filterButtons = document.querySelectorAll('.filter-btn');

// Stats elements
const totalRequests = document.getElementById('totalRequests');
const pendingRequests = document.getElementById('pendingRequests');
const processingRequests = document.getElementById('processingRequests');
const completedRequests = document.getElementById('completedRequests');
const failedRequests = document.getElementById('failedRequests');

// Socket.IO Event Handlers
socket.on('connect', () => {
    console.log('Connected to server');
    connectionStatus.classList.add('connected');
    connectionText.textContent = 'Connected';
    loadRequests();
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
    connectionStatus.classList.remove('connected');
    connectionText.textContent = 'Disconnected';
});

socket.on('request_created', (request) => {
    console.log('New request created:', request);
    requests.unshift(request);
    renderRequests();
    updateStats();
    showNotification('New request created', 'success');
});

socket.on('request_updated', (request) => {
    console.log('Request updated:', request);
    const index = requests.findIndex(r => r.id === request.id);
    if (index !== -1) {
        requests[index] = request;
        renderRequests();
        updateStats();

        // Show notification based on status
        if (request.status === 'completed') {
            showNotification(`Request #${request.id} completed successfully`, 'success');
        } else if (request.status === 'failed') {
            showNotification(`Request #${request.id} failed`, 'error');
        }
    }
});

socket.on('request_deleted', (data) => {
    console.log('Request deleted:', data);
    requests = requests.filter(r => r.id !== data.id);
    renderRequests();
    updateStats();
    showNotification('Request deleted', 'info');
});

// Load all requests
async function loadRequests() {
    try {
        const response = await fetch('/api/requests');
        requests = await response.json();
        renderRequests();
        updateStats();
    } catch (error) {
        console.error('Error loading requests:', error);
        showNotification('Error loading requests', 'error');
    }
}

// Form submission
requestForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = new FormData(requestForm);
    const data = Object.fromEntries(formData.entries());

    const submitBtn = requestForm.querySelector('button[type="submit"]');
    const btnText = submitBtn.querySelector('.btn-text');
    const btnLoader = submitBtn.querySelector('.btn-loader');

    // Show loading state
    submitBtn.disabled = true;
    btnText.style.display = 'none';
    btnLoader.style.display = 'inline';

    try {
        const response = await fetch('/api/requests', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        if (response.ok) {
            requestForm.reset();
            showNotification('Request submitted successfully', 'success');
        } else {
            const error = await response.json();
            showNotification(error.message || 'Error submitting request', 'error');
        }
    } catch (error) {
        console.error('Error submitting request:', error);
        showNotification('Error submitting request', 'error');
    } finally {
        // Reset button state
        submitBtn.disabled = false;
        btnText.style.display = 'inline';
        btnLoader.style.display = 'none';
    }
});

// Space creation form submission
const spaceForm = document.getElementById('spaceForm');
if (spaceForm) {
    spaceForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const formData = new FormData(spaceForm);
        const data = Object.fromEntries(formData.entries());

        const submitBtn = spaceForm.querySelector('button[type="submit"]');
        const btnText = submitBtn.querySelector('.btn-text');
        const btnLoader = submitBtn.querySelector('.btn-loader');

        // Show loading state
        submitBtn.disabled = true;
        btnText.style.display = 'none';
        btnLoader.style.display = 'inline';

        try {
            const response = await fetch('/api/space-requests', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });

            if (response.ok) {
                spaceForm.reset();
                showNotification('Space creation request submitted successfully', 'success');
            } else {
                const error = await response.json();
                showNotification(error.message || 'Error submitting space request', 'error');
            }
        } catch (error) {
            console.error('Error submitting space request:', error);
            showNotification('Error submitting space request', 'error');
        } finally {
            // Reset button state
            submitBtn.disabled = false;
            btnText.style.display = 'inline';
            btnLoader.style.display = 'none';
        }
    });
}

// Filter buttons
filterButtons.forEach(btn => {
    btn.addEventListener('click', () => {
        filterButtons.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentFilter = btn.dataset.filter;
        renderRequests();
    });
});

// Render requests
function renderRequests() {
    const filteredRequests = currentFilter === 'all'
        ? requests
        : requests.filter(r => r.status === currentFilter);

    if (filteredRequests.length === 0) {
        requestsList.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📭</div>
                <p>No ${currentFilter === 'all' ? '' : currentFilter} requests found.</p>
            </div>
        `;
        return;
    }

    requestsList.innerHTML = filteredRequests.map(request => createRequestHTML(request)).join('');

    // Add delete button listeners
    document.querySelectorAll('.delete-btn').forEach(btn => {
        btn.addEventListener('click', () => deleteRequest(btn.dataset.id));
    });
}

// Create request HTML
function createRequestHTML(request) {
    const data = request.data;
    const createdAt = new Date(request.created_at);
    const updatedAt = new Date(request.updated_at);
    const requestType = request.type || 'access_request';

    // Build comments HTML
    let commentsHTML = '';
    if (request.comments && request.comments.length > 0) {
        commentsHTML = `
            <div class="request-comments">
                <div class="comments-header">💬 Work Notes / Comments</div>
                <div class="comments-list">
                    ${request.comments.map(comment => `
                        <div class="comment-item">${comment}</div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    // Build result HTML based on request type
    let resultHTML = '';
    if (request.result) {
        if (request.status === 'completed') {
            if (requestType === 'space_creation') {
                resultHTML = `
                    <div class="request-result success">
                        <strong>✅ Space Created Successfully</strong>
                        <div class="result-details">
                            <div>Space Key: <strong>${request.result.space_key}</strong></div>
                            <div>Space URL: <a href="${request.result.space_url}" target="_blank">${request.result.space_url}</a></div>
                        </div>
                    </div>
                `;
            } else {
                const permissions = request.result.permissions ? request.result.permissions.join(', ') : 'N/A';
                resultHTML = `
                    <div class="request-result success">
                        <strong>✅ Access Granted Successfully</strong>
                        <div class="result-details">
                            <div>User: <strong>${request.result.username}</strong></div>
                            <div>Access Level: <strong>${request.result.access_granted}</strong></div>
                            <div>Permissions: <strong>${permissions}</strong></div>
                        </div>
                    </div>
                `;
            }
        } else if (request.status === 'failed' && request.error) {
            resultHTML = `
                <div class="request-result error">
                    <strong>❌ Request Failed</strong>
                    <div class="result-details">${request.error}</div>
                </div>
            `;
        } else if (request.status === 'work_in_progress') {
            resultHTML = `
                <div class="request-result warning">
                    <strong>⚠️ Action Required</strong>
                    <div class="result-details">This request requires attention. See comments below.</div>
                </div>
            `;
        }
    } else if (request.error) {
        resultHTML = `
            <div class="request-result error">
                <strong>❌ Error</strong>
                <div class="result-details">${request.error}</div>
            </div>
        `;
    }

    // Build details based on request type
    let detailsHTML = '';
    if (requestType === 'space_creation') {
        detailsHTML = `
            <div class="request-detail">
                <div class="request-detail-label">Space Name</div>
                <div class="request-detail-value">${data.space_name}</div>
            </div>
            <div class="request-detail">
                <div class="request-detail-label">Space Key</div>
                <div class="request-detail-value">${data.space_key}</div>
            </div>
            <div class="request-detail">
                <div class="request-detail-label">Space Admin</div>
                <div class="request-detail-value">${data.space_admin}</div>
            </div>
            ${data.description ? `
                <div class="request-detail">
                    <div class="request-detail-label">Description</div>
                    <div class="request-detail-value">${data.description}</div>
                </div>
            ` : ''}
        `;
    } else {
        detailsHTML = `
            <div class="request-detail">
                <div class="request-detail-label">User</div>
                <div class="request-detail-value">${data.full_name} (${data.lan_id})</div>
            </div>
            <div class="request-detail">
                <div class="request-detail-label">Email</div>
                <div class="request-detail-value">${data.email}</div>
            </div>
            <div class="request-detail">
                <div class="request-detail-label">Space</div>
                <div class="request-detail-value">${data.space_key}</div>
            </div>
            <div class="request-detail">
                <div class="request-detail-label">Access Level</div>
                <div class="request-detail-value">${data.access}</div>
            </div>
            <div class="request-detail">
                <div class="request-detail-label">Domain</div>
                <div class="request-detail-value">${data.domain}</div>
            </div>
            <div class="request-detail">
                <div class="request-detail-label">Manager</div>
                <div class="request-detail-value">${data.manager}</div>
            </div>
        `;
    }

    return `
        <div class="request-item" data-id="${request.id}">
            <div class="request-header">
                <div class="request-id">Request #${request.id}</div>
                <div class="request-status ${request.status}">${request.status}</div>
            </div>
            <div class="request-details">
                ${detailsHTML}
            </div>
            ${resultHTML}
            ${commentsHTML}
            <div class="request-footer">
                <div class="request-time">
                    Created: ${createdAt.toLocaleString()} | Updated: ${updatedAt.toLocaleString()}
                </div>
                <div class="request-actions">
                    <button class="btn btn-small btn-danger delete-btn" data-id="${request.id}">Delete</button>
                </div>
            </div>
        </div>
    `;
}

// Delete request
async function deleteRequest(id) {
    if (!confirm('Are you sure you want to delete this request?')) {
        return;
    }

    try {
        const response = await fetch(`/api/requests/${id}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            showNotification('Request deleted', 'success');
        } else {
            showNotification('Error deleting request', 'error');
        }
    } catch (error) {
        console.error('Error deleting request:', error);
        showNotification('Error deleting request', 'error');
    }
}

// Update stats
function updateStats() {
    totalRequests.textContent = requests.length;
    pendingRequests.textContent = requests.filter(r => r.status === 'pending').length;
    processingRequests.textContent = requests.filter(r => r.status === 'processing').length;
    completedRequests.textContent = requests.filter(r => r.status === 'completed').length;
    failedRequests.textContent = requests.filter(r => r.status === 'failed').length;
}

// Show notification
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 16px 24px;
        background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        z-index: 1000;
        animation: slideInRight 0.3s ease-out;
    `;

    document.body.appendChild(notification);

    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease-out';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(100%);
            opacity: 0;
        }
    }
    
    .request-result {
        margin-top: 12px;
        padding: 12px;
        border-radius: 8px;
        font-size: 14px;
    }
    
    .request-result.success {
        background: rgba(16, 185, 129, 0.1);
        border: 1px solid rgba(16, 185, 129, 0.3);
        color: #10b981;
    }
    
    .request-result.error {
        background: rgba(239, 68, 68, 0.1);
        border: 1px solid rgba(239, 68, 68, 0.3);
        color: #ef4444;
    }
`;
document.head.appendChild(style);

// Initial load
loadRequests();
