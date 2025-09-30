const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

const API_URL = window.location.origin;
let ADMIN_TOKEN = null;

let currentUserFilter = '';
let currentSubFilter = '';

// Verify admin access on load
async function verifyAccess() {
    try {
        // Check if opened in Telegram
        if (!tg.initData) {
            showError('❌ Open this page in Telegram Mini App');
            return false;
        }

        const response = await fetch(`${API_URL}/admin/auth/verify`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                initData: tg.initData
            })
        });

        if (!response.ok) {
            if (response.status === 403) {
                showError('🚫 Access denied. Admin only.');
            } else {
                showError('❌ Authentication failed');
            }
            return false;
        }

        const data = await response.json();
        ADMIN_TOKEN = data.token;

        // Show username in header
        const header = document.querySelector('.header h1');
        if (data.user && data.user.first_name) {
            header.textContent = `📊 Admin Panel - ${data.user.first_name}`;
        }

        return true;
    } catch (error) {
        console.error('Error verifying access:', error);
        showError('❌ Connection error');
        return false;
    }
}

function showError(message) {
    document.body.innerHTML = `
        <div style="display: flex; align-items: center; justify-content: center; height: 100vh; padding: 20px; text-align: center;">
            <div>
                <div style="font-size: 48px; margin-bottom: 20px;">${message.split(' ')[0]}</div>
                <div style="font-size: 18px; opacity: 0.7;">${message.substring(message.indexOf(' ') + 1)}</div>
            </div>
        </div>
    `;
}

// Load dashboard data
async function loadDashboard() {
    try {
        const response = await fetch(`${API_URL}/admin/dashboard`, {
            headers: {
                'Authorization': `Bearer ${ADMIN_TOKEN}`
            }
        });
        const data = await response.json();

        document.getElementById('totalUsers').textContent = data.total_users;
        document.getElementById('activeSubs').textContent = data.active_subscriptions;
        document.getElementById('todayRevenue').textContent = `${data.today_revenue.toFixed(0)}₽`;
    } catch (error) {
        console.error('Error loading dashboard:', error);
    }
}

// Load users list
async function loadUsers(filter = '') {
    const list = document.getElementById('usersList');
    list.innerHTML = '<div class="loading">Loading...</div>';

    try {
        const url = filter ? `${API_URL}/admin/users?status=${filter}` : `${API_URL}/admin/users`;
        const response = await fetch(url, {
            headers: {
                'Authorization': `Bearer ${ADMIN_TOKEN}`
            }
        });
        const data = await response.json();

        if (data.users.length === 0) {
            list.innerHTML = '<div class="loading">No users found</div>';
            return;
        }

        list.innerHTML = data.users.map(user => `
            <div class="list-item">
                <div class="list-item-header">
                    <div class="list-item-username">@${user.username || user.tg_user_id}</div>
                    <div class="list-item-badge ${user.has_subscription ? 'badge-paid' : (user.is_blocked ? 'badge-blocked' : 'badge-active')}">
                        ${user.has_subscription ? 'PAID' : (user.is_blocked ? 'BLOCKED' : 'FREE')}
                    </div>
                </div>
                <div class="list-item-details">
                    <div class="detail-row">
                        <div class="detail-label">User ID</div>
                        <div class="detail-value">${user.tg_user_id}</div>
                    </div>
                    <div class="detail-row">
                        <div class="detail-label">Questions Left</div>
                        <div class="detail-value">${user.free_questions_left}</div>
                    </div>
                    <div class="detail-row">
                        <div class="detail-label">First Seen</div>
                        <div class="detail-value">${formatDate(user.first_seen_at)}</div>
                    </div>
                    <div class="detail-row">
                        <div class="detail-label">Last Seen</div>
                        <div class="detail-value">${formatDate(user.last_seen_at)}</div>
                    </div>
                </div>
                ${user.subscription_end ? `
                    <div class="detail-row" style="margin-top: 8px">
                        <div class="detail-label">Subscription Ends</div>
                        <div class="detail-value">${formatDate(user.subscription_end)}</div>
                    </div>
                ` : ''}
            </div>
        `).join('');
    } catch (error) {
        list.innerHTML = '<div class="error">Error loading users</div>';
        console.error('Error loading users:', error);
    }
}

// Load subscriptions list
async function loadSubscriptions(filter = '') {
    const list = document.getElementById('subscriptionsList');
    list.innerHTML = '<div class="loading">Loading...</div>';

    try {
        const url = filter ? `${API_URL}/admin/subscriptions?status=${filter}` : `${API_URL}/admin/subscriptions`;
        const response = await fetch(url, {
            headers: {
                'Authorization': `Bearer ${ADMIN_TOKEN}`
            }
        });
        const data = await response.json();

        if (data.subscriptions.length === 0) {
            list.innerHTML = '<div class="loading">No subscriptions found</div>';
            return;
        }

        list.innerHTML = data.subscriptions.map(sub => `
            <div class="sub-item">
                <div class="sub-header">
                    <div class="sub-user">@${sub.username || sub.tg_user_id}</div>
                    <div class="sub-amount">${sub.amount.toFixed(0)} ${sub.currency}</div>
                </div>
                <div class="sub-details">
                    <span class="sub-plan">${sub.plan_code}</span>
                    <span style="opacity: 0.6; font-size: 12px">${formatDate(sub.started_at)} → ${formatDate(sub.ends_at)}</span>
                </div>
            </div>
        `).join('');
    } catch (error) {
        list.innerHTML = '<div class="error">Error loading subscriptions</div>';
        console.error('Error loading subscriptions:', error);
    }
}

// Format date
function formatDate(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now - date;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// Tab switching
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

        tab.classList.add('active');
        document.getElementById(`${tab.dataset.tab}-tab`).classList.add('active');

        if (tab.dataset.tab === 'users') {
            loadUsers(currentUserFilter);
        } else if (tab.dataset.tab === 'subscriptions') {
            loadSubscriptions(currentSubFilter);
        }
    });
});

// User filters
document.querySelectorAll('[data-filter]').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('[data-filter]').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        currentUserFilter = btn.dataset.filter;
        loadUsers(currentUserFilter);
    });
});

// Subscription filters
document.querySelectorAll('[data-filter-sub]').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('[data-filter-sub]').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        currentSubFilter = btn.dataset.filterSub;
        loadSubscriptions(currentSubFilter);
    });
});

// CRM Test handler
document.getElementById('testCrmBtn').addEventListener('click', async () => {
    const btn = document.getElementById('testCrmBtn');
    const resultsDiv = document.getElementById('crmTestResults');

    btn.disabled = true;
    btn.textContent = '⏳ Тестируем...';
    resultsDiv.style.display = 'none';

    try {
        const response = await fetch(`${API_URL}/admin/test/crm`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${ADMIN_TOKEN}`
            }
        });

        const data = await response.json();

        if (data.status === 'success') {
            resultsDiv.innerHTML = `
                <h4 class="success">✅ CRM Тест Успешно</h4>
                <div class="result-item">
                    <strong>Admin ID:</strong> ${data.admin_id}
                </div>
                <div class="result-item">
                    <strong>Planner:</strong> Создано задач: ${data.planner.tasks_created}
                    <br>
                    ${data.planner.created_tasks.map(t =>
                        `<div style="margin-left: 10px; margin-top: 5px;">• ${t.type} - ${new Date(t.due_at).toLocaleString()}</div>`
                    ).join('')}
                </div>
                <div class="result-item">
                    <strong>Dispatcher:</strong>
                    <br>• Отправлено: ${data.dispatcher.sent}
                    <br>• Ошибки: ${data.dispatcher.failed}
                    <br>• Заблокировано: ${data.dispatcher.blocked}
                </div>
            `;
            resultsDiv.style.display = 'block';
        } else {
            resultsDiv.innerHTML = `
                <h4 class="error">❌ Ошибка теста</h4>
                <div class="result-item">${data.message || 'Unknown error'}</div>
            `;
            resultsDiv.style.display = 'block';
        }
    } catch (error) {
        console.error('Error testing CRM:', error);
        resultsDiv.innerHTML = `
            <h4 class="error">❌ Ошибка</h4>
            <div class="result-item">${error.message}</div>
        `;
        resultsDiv.style.display = 'block';
    } finally {
        btn.disabled = false;
        btn.textContent = '🧪 Тест CRM';
    }
});

// Initial load with access verification
(async function() {
    const hasAccess = await verifyAccess();
    if (hasAccess) {
        loadDashboard();
        loadUsers();

        // Refresh every 30 seconds
        setInterval(() => {
            loadDashboard();
            const activeTab = document.querySelector('.tab.active').dataset.tab;
            if (activeTab === 'users') {
                loadUsers(currentUserFilter);
            } else if (activeTab === 'subscriptions') {
                loadSubscriptions(currentSubFilter);
            }
        }, 30000);
    }
})();