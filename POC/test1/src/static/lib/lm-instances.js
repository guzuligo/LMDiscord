/* LM Studio Instances UI Management */

let lmInstancesData = [];
let lmModelsData = [];

// API base path (backend uses underscore: /api/lm_instances)
const API_BASE = '/api/lm_instances';

function loadLmInstances() {
    fetch(API_BASE)
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                lmInstancesData = data.instances || {};
                lmActiveId = data.active_id || null;
                renderLMInstances();
            } else {
                document.getElementById('lm-instances-grid').innerHTML =
                    '<p style="color:#f38ba8;font-size:13px;">Failed to load instances: ' + (data.error || 'Unknown error') + '</p>';
            }
        })
        .catch(err => {
            console.error('Failed to load LM instances:', err);
            document.getElementById('lm-instances-grid').innerHTML =
                '<p style="color:#f38ba8;font-size:13px;">Error loading instances: ' + err.message + '</p>';
        });
}

// Track active instance ID at module level
let lmActiveId = null;

function renderLMInstances() {
    const container = document.getElementById('lm-instances-grid');
    if (!container) return;

    const instances = Object.values(lmInstancesData);
    if (instances.length === 0) {
        container.innerHTML = '<p style="color:#6c7086;font-size:13px;">No LM Studio instances configured. Add one below.</p>';
        return;
    }

    container.innerHTML = instances.map(inst => {
        const activeClass = inst.id === lmActiveId ? 'active' : '';
        return `
            <div class="lm-instance-card ${activeClass}" data-instance-id="${inst.id}">
                <div class="lm-card-header">
                    <div>
                        <h4>${escapeHtml(inst.display_name || inst.id)}</h4>
                        <span class="lm-instance-id">${inst.id}</span>
                    </div>
                    <span class="lm-status-badge ${inst.is_connected ? 'connected' : 'disconnected'}">
                        ${inst.is_connected ? 'Online' : 'Offline'}
                    </span>
                </div>
                <div class="lm-card-body">
                    <div class="lm-host-port">${escapeHtml(inst.hostname)}:${inst.port}</div>
                    ${inst.selected_model ? `<div style="margin-top:4px;">Model: ${escapeHtml(inst.selected_model)}</div>` : ''}
                </div>
                ${inst.available_models && inst.available_models.length > 0 ? `
                    <div class="lm-model-selector">
                        <label>Models (${inst.available_models.length}):</label>
                        <select onchange="onModelChange('${inst.id}', this.value)">
                            <option value="">Auto-select</option>
                            ${inst.available_models.map(m => `<option value="${escapeHtml(m)}" ${m === inst.selected_model ? 'selected' : ''}>${escapeHtml(m)}</option>`).join('')}
                        </select>
                    </div>
                ` : ''}
                <div class="lm-card-actions">
                    ${inst.id !== lmActiveId ? `<button class="lm-activate-btn" onclick="activateInstance('${inst.id}')">Activate</button>` : '<button disabled>Active</button>'}
                    <button onclick="testInstance('${inst.id}')">Test</button>
                    ${inst.id !== 'local' ? `<button onclick="removeInstance('${inst.id}')">Remove</button>` : ''}
                </div>
            </div>
        `;
    }).join('');
}

function addLMInstanceFromUI() {
    const hostname = document.getElementById('lmAddHostname').value.trim();
    const port = parseInt(document.getElementById('lmAddPort').value.trim());
    if (!hostname) {
        showStatus('Hostname is required', 'error');
        return;
    }
    if (isNaN(port) || port < 1 || port > 65535) {
        showStatus('Invalid port number', 'error');
        return;
    }
    addLMInstance(hostname, port);
}

function addLMInstance(hostname, port) {
    // Use hostname:port as ID for uniqueness
    const instanceId = hostname + ':' + port;
    
    fetch(API_BASE, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            id: instanceId,
            hostname: hostname,
            port: port,
            display_name: hostname + ':' + port
        })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            showStatus('Instance added successfully', 'success');
            loadLmInstances();
        } else {
            showStatus('Failed to add instance: ' + (data.error || 'Unknown error'), 'error');
        }
    })
    .catch(err => showStatus('Error: ' + err.message, 'error'));
}

function removeInstance(instanceId) {
    if (!confirm('Remove this instance?')) return;
    
    fetch(API_BASE + '/' + instanceId, {method: 'DELETE'})
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                showStatus('Instance removed', 'success');
                loadLmInstances();
            } else {
                showStatus('Failed: ' + (data.error || 'Unknown error'), 'error');
            }
        })
        .catch(err => showStatus('Error: ' + err.message, 'error'));
}

function activateInstance(instanceId) {
    fetch(API_BASE + '/' + instanceId + '/activate', {method: 'POST'})
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                showStatus('Instance activated', 'success');
                loadLmInstances();
            } else {
                showStatus('Failed: ' + (data.error || 'Unknown error'), 'error');
            }
        })
        .catch(err => showStatus('Error: ' + err.message, 'error'));
}

function selectModelFromCard(instanceId, model) {
    // Select model on a specific instance's active model
    if (!model) return;
    
    fetch(API_BASE + '/' + instanceId + '/select_model', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({model_id: model})
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            showStatus(`Model set to: ${model}`, 'success');
            loadLmInstances();
        } else {
            showStatus('Failed: ' + (data.error || 'Unknown error'), 'error');
        }
    })
    .catch(err => showStatus('Error: ' + err.message, 'error'));
}

function testInstance(instanceId) {
    fetch(API_BASE + '/' + instanceId + '/discover', {method: 'POST'})
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                showStatus(`Test OK: ${instanceId} (${data.count} models found)`, 'success');
            } else {
                showStatus(`Test failed: ${data.error || 'Unknown error'}`, 'error');
            }
            loadLmInstances();
        })
        .catch(err => showStatus('Error: ' + err.message, 'error'));
}

function onModelChange(instanceId, model) {
    // When clicking model in instance card, select it for that instance
    selectModelFromCard(instanceId, model);
}

function loadLMModels() {
    // Load models for active instance
    fetch(API_BASE + '/active/model')
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                lmModelsData = data;
            }
        })
        .catch(err => console.error('Failed to load LM models:', err));
}

function showStatus(msg, type) {
    const el = document.getElementById('lm-status-msg');
    if (!el) return;
    
    el.textContent = msg;
    el.className = 'lm-status-msg ' + type;
    el.style.display = 'block';
    
    setTimeout(() => {
        el.style.display = 'none';
    }, 3000);
}

// Initialize LM instances tab
document.addEventListener('DOMContentLoaded', function() {
    const tab = document.getElementById('lm-instances-tab');
    if (tab) {
        tab.addEventListener('click', function() {
            loadLmInstances();
            loadLMModels();
        });
    }
});
