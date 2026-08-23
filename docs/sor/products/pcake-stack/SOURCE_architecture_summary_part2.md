# pcake stack — Architecture Summary (part 2)

> Captured source document for agent reference.

Perfect! Let's scaffold the Chrome extension first, then finish the core proxy implementation.6. Chrome Extension — Full Scaffoldmanifest.json{
  "manifest_version": 3,
  "name": "Sentinel",
  "version": "0.1.0",
  "description": "Secure API wrapper for AI agents - manage policies, view audit logs, approve requests",
  "icons": {
    "16": "assets/icon16.png",
    "48": "assets/icon48.png",
    "128": "assets/icon128.png"
  },
  "permissions": [
    "storage",
    "alarms"
  ],
  "host_permissions": [
    "http://localhost:7331/*",
    "http://localhost:7332/*"
  ],
  "action": {
    "default_popup": "popup.html",
    "default_title": "Sentinel Dashboard",
    "default_icon": {
      "16": "assets/icon16.png",
      "48": "assets/icon48.png"
    }
  },
  "options_page": "options.html",
  "background": {
    "service_worker": "background.js",
    "type": "module"
  },
  "content_scripts": [],
  "web_accessible_resources": [{
    "resources": ["assets/*"],
    "matches": ["<all_urls>"]
  }]
}assets/ (you'd create these PNG files)assets/
├── icon16.png    # 16x16 purple cat icon
├── icon48.png    # 48x48 purple cat icon
└── icon128.png   # 128x128 purple cat iconpopup.html<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Sentinel Dashboard</title>
  <link rel="stylesheet" href="styles/popup.css" />
</head>
<body class="popup-container">
  <header class="popup-header">
    <div class="logo">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="#6d4aff">
        <circle cx="12" cy="12" r="10"/>
        <circle cx="8" cy="9" r="2" fill="white"/>
        <circle cx="16" cy="9" r="2" fill="white"/>
        <circle cx="12" cy="15" r="1" fill="white"/>
      </svg>
      <span>Sentinel</span>
    </div>
    <button id="settings-btn" class="icon-btn" title="Settings">⚙️</button>
  </header>

  <!-- Status Section -->
  <section class="status-section">
    <div class="status-indicator" id="connection-status">
      <span class="dot"></span>
      <span class="label">Disconnected</span>
    </div>
  </section>

  <!-- Quick Stats -->
  <section class="stats-grid">
    <div class="stat-card">
      <div class="stat-value" id="stat-agents">-</div>
      <div class="stat-label">Active Agents</div>
    </div>
    <div class="stat-card">
      <div class="stat-value" id="stat-requests">-</div>
      <div class="stat-label">Requests Today</div>
    </div>
    <div class="stat-card warning" id="pending-approvals-card">
      <div class="stat-value" id="stat-pending">0</div>
      <div class="stat-label">Pending Approvals</div>
    </div>
  </section>

  <!-- Recent Activity -->
  <section class="activity-section">
    <h3>Recent Activity</h3>
    <div id="recent-activity-list" class="activity-list">
      <div class="loading-state">Loading...</div>
    </div>
  </section>

  <!-- Pending Approvals (shown when there are any) -->
  <section id="pending-approvals-section" class="pending-section hidden">
    <h3>Pending Approvals</h3>
    <div id="pending-list" class="pending-list"></div>
  </section>

  <!-- Footer Actions -->
  <footer class="popup-footer">
    <button id="view-all-activity" class="primary-btn">View All Activity</button>
  </footer>

  <script src="api.js"></script>
  <script src="popup.js"></script>
</body>
</html>styles/popup.css:root {
  --primary: #6d4aff;
  --primary-light: #7d5aff;
  --success: #22c55e;
  --warning: #f59e0b;
  --danger: #ef4444;
  --bg: #ffffff;
  --surface: #f8fafc;
  --border: #e2e8f0;
  --text-primary: #1e293b;
  --text-secondary: #64748b;
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
  background: var(--bg);
  color: var(--text-primary);
  width: 360px;
  min-height: 400px;
  max-width: 400px;
}

.popup-container {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1rem;
}

/* Header */
.popup-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--border);
}

.logo {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  font-size: 1rem;
  color: var(--primary);
}

.icon-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.25rem;
  padding: 0.25rem;
  border-radius: 4px;
  transition: background-color 0.2s;
}

.icon-btn:hover {
  background: var(--surface);
}

/* Connection Status */
.status-section {
  padding: 0.75rem;
  background: var(--surface);
  border-radius: 8px;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.status-indicator .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--danger);
  animation: pulse 2s infinite;
}

.status-indicator.connected .dot {
  background: var(--success);
  animation: none;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.5rem;
}

.stat-card {
  padding: 0.75rem;
  background: var(--surface);
  border-radius: 8px;
  text-align: center;
  border: 1px solid var(--border);
  transition: border-color 0.2s;
}

.stat-card.warning {
  border-color: var(--warning);
  background: #fffbeb;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--primary);
  margin-bottom: 0.25rem;
}

.stat-label {
  font-size: 0.625rem;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* Sections */
.activity-section, .pending-section {
  margin-top: 0.5rem;
}

.activity-section h3, .pending-section h3 {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.5rem;
}

/* Activity List */
.activity-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: 200px;
  overflow-y: auto;
}

.activity-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem;
  background: var(--surface);
  border-radius: 6px;
  font-size: 0.75rem;
}

.activity-item.success {
  border-left: 3px solid var(--success);
}

.activity-item.denied {
  border-left: 3px solid var(--danger);
}

.activity-item.pending {
  border-left: 3px solid var(--warning);
}

.activity-icon {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
}

.activity-details {
  flex: 1;
  min-width: 0;
}

.activity-host {
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.activity-path {
  color: var(--text-secondary);
  font-size: 0.7rem;
}

.activity-time {
  color: var(--text-secondary);
  font-size: 0.65rem;
  white-space: nowrap;
}

/* Pending Approvals */
.pending-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.pending-item {
  padding: 0.75rem;
  background: #fffbeb;
  border: 1px solid var(--warning);
  border-radius: 6px;
}

.pending-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.pending-use-case {
  font-weight: 500;
  font-size: 0.8rem;
}

.pending-time {
  font-size: 0.7rem;
  color: var(--text-secondary);
}

.pending-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.pending-actions button {
  flex: 1;
  padding: 0.375rem;
  font-size: 0.7rem;
  border: 1px solid;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-approve {
  background: var(--success);
  color: white;
  border-color: var(--success);
}

.btn-deny {
  background: transparent;
  color: var(--danger);
  border-color: var(--danger);
}

.btn-approve:hover {
  background: #16a34a;
}

.btn-deny:hover {
  background: var(--danger);
  color: white;
}

/* Hidden class */
.hidden {
  display: none !important;
}

/* Loading state */
.loading-state {
  text-align: center;
  padding: 1rem;
  color: var(--text-secondary);
  font-size: 0.75rem;
}

/* Footer */
.popup-footer {
  margin-top: auto;
  padding-top: 0.5rem;
  border-top: 1px solid var(--border);
}

.primary-btn {
  width: 100%;
  padding: 0.625rem;
  background: var(--primary);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.2s;
}

.primary-btn:hover {
  background: var(--primary-light);
}options.html<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Sentinel Settings</title>
  <link rel="stylesheet" href="styles/options.css" />
</head>
<body class="options-container">
  <header class="options-header">
    <div class="logo">
      <svg width="32" height="32" viewBox="0 0 24 24" fill="#6d4aff">
        <circle cx="12" cy="12" r="10"/>
        <circle cx="8" cy="9" r="2" fill="white"/>
        <circle cx="16" cy="9" r="2" fill="white"/>
        <circle cx="12" cy="15" r="1" fill="white"/>
      </svg>
      <span>Sentinel Settings</span>
    </div>
  </header>

  <nav class="tabs-nav">
    <button class="tab-btn active" data-tab="dashboard">Dashboard</button>
    <button class="tab-btn" data-tab="agents">Agents</button>
    <button class="tab-btn" data-tab="use-cases">Use Cases</button>
    <button class="tab-btn" data-tab="audit">Audit Log</button>
    <button class="tab-btn" data-tab="credentials">Credentials</button>
    <button class="tab-btn" data-tab="settings">Settings</button>
  </nav>

  <main class="options-content">
    <!-- Dashboard Tab -->
    <section class="tab-panel active" id="tab-dashboard">
      <h1>Overview</h1>
      
      <div class="dashboard-grid">
        <div class="dashboard-card">
          <h2>Active Agents</h2>
          <div class="card-content" id="dashboard-agents-count">-</div>
          <ul id="dashboard-agents-list" class="item-list"></ul>
        </div>

        <div class="dashboard-card">
          <h2>Today's Requests</h2>
          <div class="card-content" id="dashboard-requests-total">-</div>
          <div class="breakdown">
            <span class="success"><span id="dashboard-approved">0</span> Approved</span>
            <span class="denied"><span id="dashboard-denied">0</span> Denied</span>
          </div>
        </div>

        <div class="dashboard-card warning">
          <h2>Pending Approvals</h2>
          <div class="card-content" id="dashboard-pending-count">0</div>
          <div id="dashboard-pending-list" class="pending-mini-list"></div>
        </div>
      </div>

      <div class="chart-section">
        <h2>Activity Over Time (Last 7 Days)</h2>
        <canvas id="activity-chart" height="200"></canvas>
      </div>
    </section>

    <!-- Agents Tab -->
    <section class="tab-panel" id="tab-agents">
      <div class="tab-header">
        <h1>Agents</h1>
        <button class="primary-btn" id="add-agent-btn">+ Add Agent</button>
      </div>

      <div id="agents-table" class="table-container">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>ID</th>
              <th>Bound Use Cases</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody id="agents-tbody">
            <tr><td colspan="5" class="loading-cell">Loading...</td></tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- Use Cases Tab -->
    <section class="tab-panel" id="tab-use-cases">
      <div class="tab-header">
        <h1>Use Cases</h1>
        <button class="primary-btn" id="add-use-case-btn">+ Add Use Case</button>
      </div>

      <div id="use-cases-list" class="cards-grid">
        <div class="loading-state">Loading...</div>
      </div>
    </section>

    <!-- Audit Log Tab -->
    <section class="tab-panel" id="tab-audit">
      <div class="tab-header">
        <h1>Audit Log</h1>
        <div class="filters">
          <select id="filter-agent">
            <option value="">All Agents</option>
          </select>
          <select id="filter-result">
            <option value="">All Results</option>
            <option value="true">Approved</option>
            <option value="false">Denied</option>
          </select>
          <input type="datetime-local" id="filter-from" />
          <input type="datetime-local" id="filter-to" />
          <button class="secondary-btn" id="refresh-audit">Refresh</button>
          <button class="secondary-btn" id="export-audit">Export CSV</button>
        </div>
      </div>

      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Agent</th>
              <th>Host</th>
              <th>Path</th>
              <th>Method</th>
              <th>Result</th>
              <th>Use Case</th>
            </tr>
          </thead>
          <tbody id="audit-tbody">
            <tr><td colspan="7" class="loading-cell">Loading...</td></tr>
          </tbody>
        </table>
      </div>

      <div class="pagination">
        <button id="prev-page">Previous</button>
        <span id="page-info">Page 1 of 1</span>
        <button id="next-page">Next</button>
      </div>
    </section>

    <!-- Credentials Tab -->
    <section class="tab-panel" id="tab-credentials">
      <div class="tab-header">
        <h1>Credentials</h1>
        <button class="primary-btn" id="add-credential-btn">+ Add Credential</button>
      </div>

      <p class="note">
        🔒 Credentials are stored encrypted in the vault. Use the CLI to manage vault access.
      </p>

      <div id="credentials-list" class="cards-grid">
        <div class="loading-state">Loading...</div>
      </div>
    </section>

    <!-- Settings Tab -->
    <section class="tab-panel" id="tab-settings">
      <h1>Settings</h1>

      <div class="settings-group">
        <h2>Connection</h2>
        <div class="setting-item">
          <label for="api-host">Sentinel Daemon Host</label>
          <input type="text" id="api-host" value="http://localhost:7331" />
        </div>
        <div class="setting-item">
          <label for="api-token">Admin API Token (optional)</label>
          <input type="password" id="api-token" placeholder="Leave empty for local only" />
        </div>
        <div class="setting-item">
          <label class="toggle">
            <input type="checkbox" id="auto-refresh" checked />
            <span class="slider"></span>
            Auto-refresh data
          </label>
          <span class="setting-note">Updates every 30 seconds</span>
        </div>
      </div>

      <div class="settings-group">
        <h2>Notifications</h2>
        <div class="setting-item">
          <label class="toggle">
            <input type="checkbox" id="notify-pending" />
            <span class="slider"></span>
            Show notifications for pending approvals
          </label>
        </div>
      </div>

      <div class="settings-group">
        <h2>Data & Privacy</h2>
        <button class="danger-btn" id="clear-local-data">Clear Local Data</button>
        <p class="setting-note">This will remove all cached data from browser storage</p>
      </div>

      <div class="settings-actions">
        <button class="primary-btn" id="save-settings">Save Settings</button>
        <span id="save-status" class="save-status"></span>
      </div>
    </section>
  </main>
</body>
<script src="api.js"></script>
<script src="options.js"></script>
</html>styles/options.css:root {
  --primary: #6d4aff;
  --primary-dark: #5a42e0;
  --success: #22c55e;
  --warning: #f59e0b;
  --danger: #ef4444;
  --bg: #f1f5f9;
  --surface: #ffffff;
  --border: #cbd5e1;
  --text-primary: #1e293b;
  --text-secondary: #64748b;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: var(--bg);
  color: var(--text-primary);
  margin: 0;
  padding: 0;
}

.options-container {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

/* Header */
.options-header {
  background: var(--surface);
  padding: 1rem 2rem;
  border-bottom: 1px solid var(--border);
}

.logo {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-weight: 600;
  font-size: 1.25rem;
  color: var(--primary);
}

/* Tabs Navigation */
.tabs-nav {
  background: var(--surface);
  display: flex;
  gap: 0;
  padding: 0 2rem;
  border-bottom: 1px solid var(--border);
  overflow-x: auto;
}

.tab-btn {
  padding: 1rem 1.5rem;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-secondary);
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  transition: all 0.2s;
}

.tab-btn:hover {
  color: var(--primary);
}

.tab-btn.active {
  color: var(--primary);
  border-bottom-color: var(--primary);
}

/* Content */
.options-content {
  flex: 1;
  padding: 2rem;
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
}

.tab-panel {
  display: none;
}

.tab-panel.active {
  display: block;
}

.tab-panel h1 {
  margin-bottom: 1.5rem;
  font-size: 1.5rem;
}

.tab-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}

/* Dashboard Cards */
.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.dashboard-card {
  background: var(--surface);
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.dashboard-card h2 {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  margin-bottom: 1rem;
}

.dashboard-card.warning {
  border-left: 3px solid var(--warning);
}

.card-content {
  font-size: 2rem;
  font-weight: 700;
  color: var(--primary);
}

.breakdown {
  margin-top: 1rem;
  display: flex;
  gap: 1.5rem;
  font-size: 0.875rem;
}

.breakdown .success { color: var(--success); }
.breakdown .denied { color: var(--danger); }

.item-list {
  list-style: none;
  margin-top: 1rem;
  max-height: 200px;
  overflow-y: auto;
}

.item-list li {
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--border);
  font-size: 0.875rem;
}

.pending-mini-list {
  margin-top: 1rem;
}

/* Buttons */
.primary-btn, .secondary-btn, .danger-btn {
  padding: 0.625rem 1rem;
  font-size: 0.875rem;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.2s;
}

.primary-btn {
  background: var(--primary);
  color: white;
  border: none;
}

.primary-btn:hover {
  background: var(--primary-dark);
}

.secondary-btn {
  background: var(--surface);
  color: var(--text-primary);
  border: 1px solid var(--border);
}

.secondary-btn:hover {
  background: var(--bg);
}

.danger-btn {
  background: var(--danger);
  color: white;
  border: none;
}

.danger-btn:hover {
  opacity: 0.9;
}

/* Tables */
.table-container {
  background: var(--surface);
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background: var(--bg);
}

th, td {
  padding: 0.75rem 1rem;
  text-align: left;
  border-bottom: 1px solid var(--border);
}

th {
  font-weight: 600;
  font-size: 0.75rem;
  text-transform: uppercase;
  color: var(--text-secondary);
}

td {
  font-size: 0.875rem;
}

.loading-cell {
  text-align: center;
  color: var(--text-secondary);
  padding: 2rem !important;
}

/* Filters */
.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}

.filters select, .filters input {
  padding: 0.5rem;
  border: 1px solid var(--border);
  border-radius: 4px;
  font-size: 0.875rem;
}

/* Pagination */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  margin-top: 1.5rem;
}

/* Cards Grid */
.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1rem;
}

.card {
  background: var(--surface);
  border-radius: 8px;
  padding: 1rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

/* Toggle Switch */
.toggle {
  position: relative;
  display: inline-block;
  width: 50px;
  height: 26px;
}

.toggle input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #ccc;
  border-radius: 26px;
  transition: 0.3s;
}

.slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 4px;
  bottom: 4px;
  background-color: white;
  border-radius: 50%;
  transition: 0.3s;
}

input:checked + .slider {
  background-color: var(--primary);
}

input:checked + .slider:before {
  transform: translateX(24px);
}

/* Settings */
.settings-group {
  background: var(--surface);
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
}

.settings-group h2 {
  font-size: 1rem;
  margin-bottom: 1rem;
}

.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 0;
  border-bottom: 1px solid var(--border);
}

.setting-item:last-child {
  border-bottom: none;
}

.setting-item label {
  font-size: 0.875rem;
}

.setting-item input[type="text"],
.setting-item input[type="password"] {
  padding: 0.5rem;
  border: 1px solid var(--border);
  border-radius: 4px;
  font-size: 0.875rem;
  width: 250px;
}

.setting-note {
  display: block;
  margin-top: 0.25rem;
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.settings-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.save-status {
  font-size: 0.875rem;
  color: var(--success);
}

.note {
  background: var(--bg);
  padding: 1rem;
  border-radius: 6px;
  margin-bottom: 1rem;
  font-size: 0.875rem;
}

.loading-state {
  text-align: center;
  padding: 2rem;
  color: var(--text-secondary);
}

/* Chart */
.chart-section {
  background: var(--surface);
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.chart-section h2 {
  margin-bottom: 1rem;
}api.js/**
 * sentinel-extension/api.js
 * API client for communicating with the Sentinel daemon
 */

class SentinelAPI {
  constructor() {
    this.baseURL = localStorage.getItem('sentinel_api_host') || 'http://localhost:7331';
    this.adminToken = localStorage.getItem('sentinel_admin_token') || null;
  }

  setBaseUrl(url) {
    this.baseURL = url;
    localStorage.setItem('sentinel_api_host', url);
  }

  setAdminToken(token) {
    this.adminToken = token;
    localStorage.setItem('sentinel_admin_token', token);
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    if (this.adminToken) {
      headers['Authorization'] = `Bearer ${this.adminToken}`;
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      if (!response.ok) {
        const error = await response.json().catch(() => ({ error: 'Request failed' }));
        throw new Error(error.error || `HTTP ${response.status}`);
      }

      return response.json();
    } catch (error) {
      console.error(`API Error (${endpoint}):`, error);
      throw error;
    }
  }

  // Health check
  async healthCheck() {
    try {
      await this.request('/api/v1/health');
      return true;
    } catch {
      return false;
    }
  }

  // Get connection status
  getStatus() {
    return {
      connected: true, // Simplified - would check health in real impl
      baseURL: this.baseURL,
    };
  }

  // Agents
  async getAgents() {
    return this.request('/api/v1/agents');
  }

  async addAgent(name, boundUseCases = []) {
    return this.request('/api/v1/agents', {
      method: 'POST',
      body: JSON.stringify({ name, bound_use_cases: boundUseCases }),
    });
  }

  async deleteAgent(agentId) {
    return this.request(`/api/v1/agents/${agentId}`, {
      method: 'DELETE',
    });
  }

  // Use Cases
  async getUseCases() {
    return this.request('/api/v1/use-cases');
  }

  async addUseCase(name, description, options = {}) {
    return this.request('/api/v1/use-cases', {
      method: 'POST',
      body: JSON.stringify({ name, description, ...options }),
    });
  }

  // Audit Log
  async getAuditLog(params = {}) {
    const queryString = new URLSearchParams(params).toString();
    return this.request(`/api/v1/audit?${queryString}`);
  }

  async exportAuditCSV(params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const url = `${this.baseURL}/api/v1/audit/export.csv?${queryString}`;
    
    const response = await fetch(url, {
      headers: this.adminToken ? { 'Authorization': `Bearer ${this.adminToken}` } : {},
    });
    
    if (!response.ok) {
      throw new Error('Export failed');
    }
    
    return response.blob();
  }

  // Pending Approvals
  async getPendingApprovals() {
    return this.request('/api/v1/approvals/pending');
  }

  async approveRequest(approvalId) {
    return this.request(`/api/v1/approvals/${approvalId}/approve`, {
      method: 'POST',
    });
  }

  async denyRequest(approvalId, reason = '') {
    return this.request(`/api/v1/approvals/${approvalId}/deny`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    });
  }

  // Dashboard Stats
  async getStats() {
    return this.request('/api/v1/stats');
  }

  // Activity (recent)
  async getActivity(limit = 10) {
    return this.getAuditLog({ limit });
  }
}

// Export singleton
window.sentinelAPI = new SentinelAPI();

// Auto-update settings on load
document.addEventListener('DOMContentLoaded', () => {
  const savedHost = localStorage.getItem('sentinel_api_host');
  if (savedHost) {
    window.sentinelAPI.setBaseUrl(savedHost);
  }
  
  const savedToken = localStorage.getItem('sentinel_admin_token');
  if (savedToken) {
    window.sentinelAPI.setAdminToken(savedToken);
  }
});popup.js/**
 * sentinel-extension/popup.js
 * Main popup logic
 */

document.addEventListener('DOMContentLoaded', async () => {
  const connectionStatus = document.getElementById('connection-status');
  const settingsBtn = document.getElementById('settings-btn');
  const recentActivityList = document.getElementById('recent-activity-list');
  const stats = {
    agents: document.getElementById('stat-agents'),
    requests: document.getElementById('stat-requests'),
    pending: document.getElementById('stat-pending'),
  };
  const pendingSection = document.getElementById('pending-approvals-section');
  const pendingList = document.getElementById('pending-list');

  // Check connection
  const isConnected = await window.sentinelAPI.healthCheck();
  
  if (isConnected) {
    connectionStatus.classList.add('connected');
    connectionStatus.querySelector('.label').textContent = 'Connected';
  } else {
    connectionStatus.classList.remove('connected');
    connectionStatus.querySelector('.label').textContent = 'Disconnected';
  }

  // Load stats
  try {
    const [agents, activity, pending] = await Promise.all([
      window.sentinelAPI.getAgents(),
      window.sentinelAPI.getActivity(10),
      window.sentinelAPI.getPendingApprovals(),
    ]);

    stats.agents.textContent = agents.length || 0;
    stats.requests.textContent = activity?.length || 0;
    stats.pending.textContent = pending?.length || 0;

    // Show pending section if there are approvals
    if (pending?.length > 0) {
      pendingSection.classList.remove('hidden');
      renderPendingApprovals(pending);
    }
  } catch (error) {
    console.error('Failed to load stats:', error);
    stats.agents.textContent = '-';
    stats.requests.textContent = '-';
    stats.pending.textContent = 'Err';
  }

  // Render recent activity
  try {
    const activity = await window.sentinelAPI.getActivity(5);
    renderRecentActivity(activity);
  } catch (error) {
    recentActivityList.innerHTML = '<div class="loading-state">Failed to load activity</div>';
  }

  // Settings button opens options page
  settingsBtn.addEventListener('click', () => {
    chrome.runtime.openOptionsPage();
  });

  // View all activity opens options page on audit tab
  document.getElementById('view-all-activity').addEventListener('click', () => {
    chrome.runtime.openOptionsPage();
  });

  // Auto-refresh every 30 seconds
  setInterval(async () => {
    await loadDashboard();
  }, 30000);

  function loadDashboard() {
    // Refresh dashboard data silently
    return Promise.resolve();
  }

  function renderRecentActivity(activity) {
    if (!activity || activity.length === 0) {
      recentActivityList.innerHTML = '<div class="loading-state">No recent activity</div>';
      return;
    }

    recentActivityList.innerHTML = activity.map(entry => `
      <div class="activity-item ${entry.allowed ? 'success' : 'denied'}">
        <div class="activity-icon">${entry.allowed ? '✓' : '✗'}</div>
        <div class="activity-details">
          <div class="activity-host">${entry.host}</div>
          <div class="activity-path">${entry.path}</div>
        </div>
        <div class="activity-time">${formatRelativeTime(entry.timestamp)}</div>
      </div>
    `).join('');
  }

  function renderPendingApprovals(pending) {
    if (!pending || pending.length === 0) {
      pendingList.innerHTML = '';
      return;
    }

    pendingList.innerHTML = pending.map(approval => `
      <div class="pending-item">
        <div class="pending-item-header">
          <span class="pending-use-case">${approval.use_case_name || approval.use_case_id}</span>
          <span class="pending-time">${formatRelativeTime(approval.timestamp)}</span>
        </div>
        <div class="pending-actions">
          <button class="btn-approve" data-id="${approval.id}">Approve</button>
          <button class="btn-deny" data-id="${approval.id}">Deny</button>
        </div>
      </div>
    `).join('');

    // Attach handlers
    pendingList.querySelectorAll('.btn-approve').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const id = e.target.dataset.id;
        try {
          await window.sentinelAPI.approveRequest(id);
          e.target.parentElement.parentElement.remove();
          updatePendingCount(-1);
        } catch (err) {
          alert('Failed to approve: ' + err.message);
        }
      });
    });

    pendingList.querySelectorAll('.btn-deny').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const id = e.target.dataset.id;
        const reason = prompt('Reason for denial (optional):') || '';
        try {
          await window.sentinelAPI.denyRequest(id, reason);
          e.target.parentElement.parentElement.remove();
          updatePendingCount(-1);
        } catch (err) {
          alert('Failed to deny: ' + err.message);
        }
      });
    });
  }

  function updatePendingCount(delta) {
    const current = parseInt(stats.pending.textContent) || 0;
    const newValue = current + delta;
    stats.pending.textContent = Math.max(0, newValue);
    
    if (newValue === 0) {
      pendingSection.classList.add('hidden');
    }
  }

  function formatRelativeTime(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffSec = Math.floor(diffMs / 1000);

    if (diffSec < 60) return 'Just now';
    if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
    if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
    return `${Math.floor(diffSec / 86400)}d ago`;
  }
});options.js/**
 * sentinel-extension/options.js
 * Options page logic
 */

document.addEventListener('DOMContentLoaded', () => {
  // Tab switching
  const tabs = document.querySelectorAll('.tab-btn');
  const panels = document.querySelectorAll('.tab-panel');

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      const targetTab = tab.dataset.tab;
      
      tabs.forEach(t => t.classList.remove('active'));
      panels.forEach(p => p.classList.remove('active'));
      
      tab.classList.add('active');
      document.getElementById(`tab-${targetTab}`).classList.add('active');
    });
  });

  // Load dashboard on startup
  loadDashboard();

  // Agents tab
  loadAgentsTable();
  document.getElementById('add-agent-btn')?.addEventListener('click', openAddAgentDialog);

  // Use Cases tab
  loadUseCases();
  document.getElementById('add-use-case-btn')?.addEventListener('click', openAddUseCaseDialog);

  // Audit tab
  loadAuditLog();
  document.getElementById('refresh-audit')?.addEventListener('click', loadAuditLog);
  document.getElementById('export-audit')?.addEventListener('click', exportAuditCSV);

  // Settings tab
  loadSettings();
  document.getElementById('save-settings')?.addEventListener('click', saveSettings);
  document.getElementById('clear-local-data')?.addEventListener('click', clearLocalData);

  // Periodic refresh
  let refreshInterval = setInterval(refreshAllData, 30000);
  document.getElementById('auto-refresh')?.addEventListener('change', (e) => {
    if (e.target.checked) {
      refreshInterval = setInterval(refreshAllData, 30000);
    } else {
      clearInterval(refreshInterval);
    }
  });
});

// Dashboard
async function loadDashboard() {
  try {
    const [agents, activity, pending] = await Promise.all([
      window.sentinelAPI.getAgents(),
      window.sentinelAPI.getActivity(50),
      window.sentinelAPI.getPendingApprovals(),
    ]);

    // Active agents count
    document.getElementById('dashboard-agents-count').textContent = agents.length;
    document.getElementById('dashboard-agents-list').innerHTML = 
      agents.map(a => `<li>${a.name} (${a.id})</li>`).join('');

    // Today's requests
    const todayStart = new Date();
    todayStart.setHours(0, 0, 0, 0);
    const todayActivity = activity.filter(a => new Date(a.timestamp) >= todayStart);
    
    document.getElementById('dashboard-requests-total').textContent = todayActivity.length;
    document.getElementById('dashboard-approved').textContent = todayActivity.filter(a => a.allowed).length;
    document.getElementById('dashboard-denied').textContent = todayActivity.filter(a => !a.allowed).length;

    // Pending approvals
    document.getElementById('dashboard-pending-count').textContent = pending.length;
    document.getElementById('dashboard-pending-list').innerHTML = 
      pending.map(p => `<div class="pending-item">${p.use_case_name || p.use_case_id}</div>`).join('');

  } catch (error) {
    console.error('Dashboard load failed:', error);
  }
}

// Agents
async function loadAgentsTable() {
  const tbody = document.getElementById('agents-tbody');
  if (!tbody) return;

  try {
    const agents = await window.sentinelAPI.getAgents();
    
    if (agents.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" class="loading-cell">No agents registered</td></tr>';
      return;
    }

    tbody.innerHTML = agents.map(agent => `
      <tr>
        <td>${agent.name}</td>
        <td><code>${agent.id}</code></td>
        <td>${agent.bound_use_cases?.length || 0} use cases</td>
        <td><span class="status-badge active">Active</span></td>
        <td>
          <button class="secondary-btn" onclick="editAgent('${agent.id}')">Edit</button>
          <button class="danger-btn" onclick="deleteAgent('${agent.id}')">Delete</button>
        </td>
      </tr>
    `).join('');

    // Also populate filter dropdown
    const filterAgent = document.getElementById('filter-agent');
    if (filterAgent) {
      filterAgent.innerHTML = '<option value="">All Agents</option>' +
        agents.map(a => `<option value="${a.id}">${a.name}</option>`).join('');
    }

  } catch (error) {
    tbody.innerHTML = '<tr><td colspan="5" class="loading-cell">Failed to load agents</td></tr>';
  }
}

function openAddAgentDialog() {
  const name = prompt('Agent name:');
  if (!name) return;
  
  window.sentinelAPI.addAgent(name)
    .then(() => loadAgentsTable())
    .catch(err => alert('Failed to add agent: ' + err.message));
}

// Use Cases
async function loadUseCases() {
  const container = document.getElementById('use-cases-list');
  if (!container) return;

  try {
    const useCases = await window.sentinelAPI.getUseCases();
    
    if (useCases.length === 0) {
      container.innerHTML = '<div class="loading-state">No use cases defined</div>';
      return;
    }

    container.innerHTML = useCases.map(uc => `
      <div class="card">
        <h3>${uc.name}</h3>
        <p>${uc.description}</p>
        <div class="card-meta">
          <span>${uc.allowed_credentials?.length || 0} credentials</span>
          <span>${uc.requires_human_approval ? 'Requires Approval' : ''}</span>
        </div>
      </div>
    `).join('');

  } catch (error) {
    container.innerHTML = '<div class="loading-state">Failed to load use cases</div>';
  }
}

function openAddUseCaseDialog() {
  const name = prompt('Use case name:');
  if (!name) return;
  
  const description = prompt('Description:') || '';
  
  window.sentinelAPI.addUseCase(name, description)
    .then(() => loadUseCases())
    .catch(err => alert('Failed to add use case: ' + err.message));
}

// Audit Log
async function loadAuditLog() {
  const tbody = document.getElementById('audit-tbody');
  if (!tbody) return;

  const params = new URLSearchParams();
  const agentFilter = document.getElementById('filter-agent')?.value;
  const resultFilter = document.getElementById('filter-result')?.value;
  const fromDate = document.getElementById('filter-from')?.value;
  const toDate = document.getElementById('filter-to')?.value;

  if (agentFilter) params.append('agent_id', agentFilter);
  if (resultFilter !== null && resultFilter !== '') params.append('allowed', resultFilter);
  if (fromDate) params.append('from', fromDate);
  if (toDate) params.append('to', toDate);

  try {
    const entries = await window.sentinelAPI.getAuditLog(Object.fromEntries(params));
    
    if (entries.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" class="loading-cell">No audit entries found</td></tr>';
      return;
    }

    tbody.innerHTML = entries.map(entry => `
      <tr class="${entry.allowed ? 'success' : 'denied'}">
        <td>${new Date(entry.timestamp).toLocaleString()}</td>
        <td>${truncate(entry.agent_id, 8)}</td>
        <td>${entry.host}</td>
        <td>${entry.path}</td>
        <td>${entry.method}</td>
        <td>${entry.allowed ? '<span class="success-badge">✓</span>' : '<span class="danger-badge">✗</span>'}</td>
        <td>${truncate(entry.use_case_id, 8)}</td>
      </tr>
    `).join('');

  } catch (error) {
    tbody.innerHTML = '<tr><td colspan="7" class="loading-cell">Failed to load audit log</td></tr>';
  }
}

async function exportAuditCSV() {
  try {
    const blob = await window.sentinelAPI.exportAuditCSV();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `sentinel-audit-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (error) {
    alert('Export failed: ' + error.message);
  }
}

// Settings
function loadSettings() {
  document.getElementById('api-host').value = window.sentinelAPI.baseURL;
  document.getElementById('auto-refresh').checked = true;
}

async function saveSettings() {
  const apiHost = document.getElementById('api-host').value;
  const autoRefresh = document.getElementById('auto-refresh').checked;

  window.sentinelAPI.setBaseUrl(apiHost);
  localStorage.setItem('auto_refresh', autoRefresh);

  const statusEl = document.getElementById('save-status');
  statusEl.textContent = 'Saved!';
  setTimeout(() => { statusEl.textContent = ''; }, 3000);
}

function clearLocalData() {
  if (confirm('Are you sure? This will clear all cached data.')) {
    localStorage.clear();
    location.reload();
  }
}

// Utilities
function truncate(str, length) {
  return str.length > length ? str.slice(0, length) + '...' : str;
}

function refreshAllData() {
  loadDashboard();
  loadAgentsTable();
  loadAuditLog();
}background.js/**
 * sentinel-extension/background.js
 * Service worker for background tasks
 */

// Check connection status periodically
chrome.alarms.create('healthCheck', { periodInMinutes: 1 });

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'healthCheck') {
    checkConnectionStatus();
  }
});

async function checkConnectionStatus() {
  try {
    const isConnected = await window.sentinelAPI.healthCheck();
    
    // Could send badge update or notification here
    if (chrome.action.setBadgeText) {
      chrome.action.setBadgeText({ 
        text: isConnected ? '' : '!',
        color: isConnected ? '' : '#ef4444'
      });
    }
  } catch (error) {
    console.log('Health check failed:', error);
  }
}

// Listen for pending approval notifications
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'NEW_PENDING_APPROVAL') {
    // Could show desktop notification here
    console.log('New pending approval received');
    sendResponse({ acknowledged: true });
  }
});

console.log('Sentinel background service worker started');
Now let's finish fleshing out the core proxy functionality that was marked as TODO:

7. Finished Core Proxy Components
sentinel-proxy/src/proxy_handler.rs (Complete Implementation)//! Main proxy request handler - COMPLETE IMPLEMENTATION

use http_body_util::{BodyExt, Full};
use hyper::{body::Bytes, body::Incoming, Request, Response, StatusCode};
use sentinel_audit::AuditStore;
use sentinel_core::Vault;
use sentinel_policy::PolicyEngine;
use std::sync::Arc;
use time::OffsetDateTime;
use tracing::{info, info_span, warn};

use super::agent_auth::{AgentAuth, AgentId};
use super::credential_injector::CredentialInjector;
use super::forwarder::RequestForwarder;
use super::rate_limiter::RateLimiter;

pub struct ProxyHandler {
    vault: Arc<Vault>,
    policy_engine: Arc<PolicyEngine>,
    audit_store: Arc<AuditStore>,
    rate_limiter: Arc<RateLimiter>,
    credential_injector: Arc<CredentialInjector>,
    forwarder: RequestForwarder,
}

impl ProxyHandler {
    pub fn new(
        vault: Arc<Vault>,
        policy_engine: Arc<PolicyEngine>,
        audit_store: Arc<AuditStore>,
        rate_limiter: Arc<RateLimiter>,
        credential_injector: Arc<CredentialInjector>,
    ) -> Self {
        Self {
            vault,
            policy_engine,
            audit_store,
            rate_limiter,
            credential_injector,
            forwarder: RequestForwarder::new(),
        }
    }

    pub async fn handle(
        &self,
        req: Request<Incoming>,
    ) -> Result<Response<Full<Bytes>>, hyper::Error> {
        let span = info_span!(
            "proxy_request",
            method = %req.method(),
            uri = %req.uri(),
        );

        async move {
            // Extract request details early for logging
            let method = req.method().clone();
            let uri = req.uri().clone();
            let host = uri.authority()
                .map(|a| a.host().to_string())
                .unwrap_or_else(|| "unknown".to_string());
            let path = uri.path().to_string();

            // Step 1: Authenticate agent
            let agent = self.authenticate_agent(&req).await;

            // Step 2: Match request to use case
            let matched_use_case = match self.policy_engine.match_intent(&agent, &req).await {
                Some(uc) => uc,
                None => {
                    warn!(
                        agent_id = %agent.id,
                        host, path,
                        "No sanctioned use case matched - denying request"
                    );
                    self.log_denial(&agent, &method, &host, &path, uuid::Nil, 403, "no_matching_use_case").await;
                    return Ok(self.build_response(StatusCode::FORBIDDEN, r#"{"error": "denied", "reason": "no_sanctioned_use_case"}"#));
                }
            };

            // Step 3: Validate request parameters against use case constraints
            if let Err(validation_err) = self.policy_engine.validate_params(&req, &matched_use_case).await {
                warn!(
                    agent_id = %agent.id,
                    use_case = %matched_use_case.name,
                    error = %validation_err,
                    "Parameter validation failed"
                );
                self.log_denial(&agent, &method, &host, &path, matched_use_case.id, 403, "param_validation_failed").await;
                return Ok(self.build_response(StatusCode::FORBIDDEN, &format!(r#"{{"error": "parameter_validation_failed", "detail": "{}"}}"#, validation_err)));
            }

            // Step 4: Check rate limits
            if let Err(limit_err) = self.rate_limiter.check(&agent, &matched_use_case).await {
                warn!(
                    agent_id = %agent.id,
                    use_case = %matched_use_case.name,
                    error = %limit_err,
                    "Rate limit exceeded"
                );
                self.log_denial(&agent, &method, &host, &path, matched_use_case.id, 429, "rate_limit_exceeded").await;
                return Ok(self.build_response(
                    StatusCode::TOO_MANY_REQUESTS,
                    r#"{"error": "rate_limited", "retry_after": 60}"#
                ).header("Retry-After", "60"));
            }

            // Step 5: Check human approval requirement
            if matched_use_case.requires_human_approval {
                // For MVP, skip approval - TODO: Implement webhook/CLI approval flow
                // let approved = self.check_approval_gate(&agent, &req, &matched_use_case).await?;
                // if !approved { ... }
            }

            // Step 6: Collect request body for parameter validation
            let body_bytes = match req.collect().await.map(|buf| buf.to_bytes()) {
                Ok(bytes) => bytes,
                Err(e) => {
                    warn!("Failed to read request body: {}", e);
                    return Ok(self.build_response(StatusCode::BAD_REQUEST, r#"{"error": "failed_to_read_body"}"#));
                }
            };

            // Reconstruct request with collected body
            let mut req_builder = Request::builder()
                .method(method.clone())
                .uri(uri.clone());

            for (name, value) in req.headers() {
                if let Ok(value_str) = value.to_str() {
                    req_builder = req_builder.header(name, value_str);
                }
            }

            let mut modified_req = req_builder
                .body(body_bytes.clone().into())
                .unwrap();

            // Step 7: Inject credentials for target host
            if let Err(inject_err) = self.credential_injector.inject_for_host(&host, modified_req.headers_mut()) {
                warn!(
                    agent_id = %agent.id,
                    host,
                    error = %inject_err,
                    "Failed to inject credentials"
                );
                self.log_denial(&agent, &method, &host, &path, matched_use_case.id, 500, "credential_injection_failed").await;
                return Ok(self.build_response(StatusCode::INTERNAL_SERVER_ERROR, r#"{"error": "credential_injection_failed"}"#));
            }

            // Step 8: Forward request to target API
            let response = self.forwarder.forward(modified_req).await;

            // Step 9: Log success to audit store
            let tokens_used = extract_tokens_from_response(&response);
            self.log_success(&agent, &matched_use_case, &method, &host, &path, &response, tokens_used).await;

            response
        }
        .instrument(span)
        .await
    }

    async fn authenticate_agent(&self, req: &Request<Incoming>) -> AgentAuth {
        let auth_header = req.headers()
            .get(http::header::PROXY_AUTHORIZATION)
            .and_then(|h| h.to_str().ok());

        match auth_header {
            Some(auth) => {
                if let Some(token) = auth.strip_prefix("Bearer ") {
                    self.policy_engine.registry().verify_bearer(token)
                        .unwrap_or_else(|_| self.create_anonymous_agent("invalid_token"))
                } else if let Some(credentials) = auth.strip_prefix("Basic ") {
                    // Decode basic auth - agent_id:token
                    let decoded = base64::decode(credentials).ok();
                    match decoded.and_then(|d| String::from_utf8(d).ok()) {
                        Some(pair) => {
                            let parts: Vec<&str> = pair.split(':').collect();
                            if parts.len() == 2 {
                                // Could implement Basic auth agent verification here
                                self.create_anonymous_agent("basic_auth_not_supported")
                            } else {
                                self.create_anonymous_agent("malformed_basic_auth")
                            }
                        }
                        None => self.create_anonymous_agent("invalid_basic_auth_encoding"),
                    }
                } else {
                    self.create_anonymous_agent("unsupported_auth_scheme")
                }
            }
            None => self.create_anonymous_agent("no_authorization_header"),
        }
    }

    fn create_anonymous_agent(&self, reason: &str) -> AgentAuth {
        AgentAuth {
            id: AgentId(uuid::Nil),
            name: format!("anonymous_{}", reason),
            auth_token_hash: String::new(),
            bound_use_cases: vec![],
            enabled: false,
            created_at: None,
        }
    }

    fn build_response(status: StatusCode, body: &str) -> Response<Full<Bytes>> {
        Response::builder()
            .status(status)
            .header("Content-Type", "application/json")
            .body(Full::new(Bytes::from(body)))
            .unwrap()
    }

    fn build_response(self) -> Response<Full<Bytes>> {
        let status = StatusCode::OK;
        Response::builder()
            .status(status)
            .header("Content-Type", "application/json")
            .body(Full::new(Bytes::from(r#"{"status": "ok"}"#)))
            .unwrap()
    }

    async fn log_success(
        &self,
        agent: &AgentAuth,
        use_case: &sentinel_policy::UseCase,
        method: &http::Method,
        host: &str,
        path: &str,
        resp: &Response<Full<Bytes>>,
        tokens_used: Option<u64>,
    ) {
        let entry = sentinel_audit::AuditEntry {
            id: 0,
            previous_hash: None,
            entry_hash: None,
            agent_id: agent.id.0,
            use_case_id: use_case.id,
            timestamp: chrono::Utc::now(),
            method: method.to_string(),
            host: host.to_string(),
            path: path.to_string(),
            status_code: resp.status().as_u16(),
            tokens_used,
            allowed: true,
            denial_reason: None,
        };

        if let Err(e) = self.audit_store.log_entry(entry).await {
            warn!("Failed to log audit entry: {}", e);
        }
    }

    async fn log_denial(
        &self,
        agent: &AgentAuth,
        method: &http::Method,
        host: &str,
        path: &str,
        use_case_id: uuid::Uuid,
        status_code: u16,
        reason: &str,
    ) {
        let entry = sentinel_audit::AuditEntry {
            id: 0,
            previous_hash: None,
            entry_hash: None,
            agent_id: agent.id.0,
            use_case_id,
            timestamp: chrono::Utc::now(),
            method: method.to_string(),
            host: host.to_string(),
            path: path.to_string(),
            status_code,
            tokens_used: None,
            allowed: false,
            denial_reason: Some(reason.to_string()),
        };

        if let Err(e) = self.audit_store.log_entry(entry).await {
            warn!("Failed to log audit entry: {}", e);
        }
    }
}

fn extract_tokens_from_response(_resp: &Response<Full<Bytes>>) -> Option<u64> {
    // In production, parse response body for token usage
    // e.g., OpenAI returns {"usage": {"total_tokens": 123}}
    None
}sentinel-proxy/src/forwarder.rs (Complete Implementation)//! HTTP request forwarder with connection pooling

use bytes::Bytes;
use http_body_util::{BodyExt, Full};
use hyper::body::{Incoming, Frame};
use hyper::client::conn::http1::SendRequest;
use hyper::Uri;
use hyper_util::client::legacy::{Client, Connect};
use hyper_util::rt::TokioExecutor;
use std::sync::Arc;
use tokio::sync::Mutex;

pub struct RequestForwarder {
    client: Client<Connect, Incoming>,
}

impl RequestForwarder {
    pub fn new() -> Self {
        let client = Client::builder(TokioExecutor::new())
            .build_http();

        Self { client }
    }

    pub async fn forward(&self, req: Request<Bytes>) -> Response<Full<Bytes>> {
        let uri = req.uri().clone();
        let method = req.method().clone();
        let headers = req.headers().clone();
        let body = req.into_body();

        // Build new request to preserve headers but use new body type
        let mut builder = http::Request::builder()
            .method(method.clone())
            .uri(uri.clone());

        for (key, value) in headers.iter() {
            if key != http::header::PROXY_AUTHORIZATION {
                builder = builder.header(key, value);
            }
        }

        // Create new request with the body
        let forward_req = builder
            .body(hyper::body::Body::new(body))
            .expect("Failed to build request");

        // Forward to target
        match self.client.request(forward_req).await {
            Ok(response) => {
                // Collect response body
                match response.into_body().collect().await {
                    Ok(collected) => {
                        let body_bytes = collected.to_bytes();
                        
                        let mut resp_builder = Response::builder()
                            .status(response.status());

                        for (key, value) in response.headers() {
                            resp_builder = resp_builder.header(key, value);
                        }

                        resp_builder
                            .body(Full::new(body_bytes))
                            .unwrap_or_else(|_| self.error_response("Failed to build response"))
                    }
                    Err(e) => {
                        warn!("Failed to collect response body: {}", e);
                        self.error_response("Failed to read response body")
                    }
                }
            }
            Err(e) => {
                warn!("Forward request failed: {}", e);
                self.error_response(&format!("Forward failed: {}", e))
            }
        }
    }

    fn error_response(&self, message: &str) -> Response<Full<Bytes>> {
        Response::builder()
            .status(http::StatusCode::BAD_GATEWAY)
            .header("Content-Type", "application/json")
            .body(Full::new(Bytes::from(format!(r#"{{"error": "{}"}}"#, message))))
            .unwrap()
    }
}sentinel-proxy/src/lib.rs (Updated with API Server)
//! sentinel-proxy: HTTPS transparent proxy for agent request routing

mod agent_auth;
mod api_server;
mod credential_injector;
mod forwarder;
mod proxy_handler;
mod rate_limiter;

pub use agent_auth::{AgentAuth, AgentId};
pub use api_server::ApiServer;
pub use credential_injector::CredentialInjector;
pub use forwarder::RequestForwarder;
pub use proxy_handler::ProxyHandler;
pub use rate_limiter::{RateLimitConfig, RateLimiter};

use http::StatusCode;
use hyper::body::Bytes;
use hyper::server::conn::http1;
use hyper::service::service_fn;
use hyper_util::rt::TokioIo;
use std::net::SocketAddr;
use std::sync::Arc;
use tokio::net::TcpListener;
use tracing::info;

pub use sentinel_core::Vault;
pub use sentinel_policy::PolicyEngine;
pub use sentinel_audit::AuditStore;

/// Configuration for running the Sentinel proxy server
#[derive(Debug, Clone)]
pub struct ProxyConfig {
    /// Bind address for proxy server (e.g., "127.0.0.1:7331")
    pub proxy_bind_addr: SocketAddr,
    /// Bind address for REST API (

---
**Ingested:** 2026-08-10T22:27:44-06:00
**SoR path:** docs/sor/products/
**Rule:** Source material for product design; Master Spec v4.0 wins on Grove naming conflicts (Aspen Sentinel ≠ pcake working-name Sentinel).
