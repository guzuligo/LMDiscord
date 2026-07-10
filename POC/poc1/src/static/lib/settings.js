// ==================== Settings Manager ====================
// Generic settings abstraction to eliminate repetitive loadX/updateX code

class SettingsManager {
    constructor(state) {
        this.state = state;
    }

    /**
     * Load a setting from the server
     * @param {string} endpoint - API endpoint (e.g., '/api/settings/temperature')
     * @param {string} stateKey - State property name
     * @param {function} parser - Function to extract value from API response
     */
    async load(endpoint, stateKey, parser) {
        try {
            const response = await fetch(endpoint);
            const data = await response.json();
            if (data.success && parser) {
                const value = parser(data);
                this.state[stateKey] = value;
                if (parser.element) parser.element.value = value;
            }
        } catch (e) {
            console.error(`Failed to load setting from ${endpoint}:`, e);
        }
    }

    /**
     * Update a setting on the server
     * @param {string} endpoint - API endpoint
     * @param {string} stateKey - State property name
     * @param {function} getValue - Function to get value from DOM
     * @param {function} validate - Validation function, returns [isValid, errorMessage]
     * @param {object} bodyFormatter - Function to format request body
     * @param {string} successMsg - Success message template
     * @param {function} onAfterUpdate - Optional callback after successful update
     */
    async update(endpoint, stateKey, getValue, validate, bodyFormatter, successMsg, onAfterUpdate) {
        try {
            const value = getValue();
            const [isValid, errorMsg] = validate(value);
            
            if (!isValid) {
                addMessage(errorMsg, 'error');
                // Restore previous value
                if (bodyFormatter && bodyFormatter.restoreValue !== undefined) {
                    // handled by caller
                }
                return;
            }

            const body = bodyFormatter(value);
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            
            const data = await response.json();
            if (data.success) {
                this.state[stateKey] = bodyFormatter.extractValue?.(value) ?? value;
                if (onAfterUpdate) onAfterUpdate(value);
                addMessage(successMsg.replace('{value}', value), 'system');
            } else {
                addMessage(data.error || 'Failed to update setting', 'error');
            }
        } catch (e) {
            addMessage(`Error: ${e.message}`, 'error');
        }
    }
}

// ==================== Settings Loaders ====================
// Individual load functions that use the SettingsManager

function createSettingsLoaders(settingsManager) {
    return {
        async loadLogging() {
            try {
                const response = await fetch('/api/settings/logging');
                const data = await response.json();
                if (data.success) {
                    if (settingsManager.state) {
                        settingsManager.state.suppressWerkzeugLogging = data.suppress_werkzeug_logging;
                    }
                    const toggle = document.getElementById('suppressLoggingToggle');
                    if (toggle) toggle.checked = data.suppress_werkzeug_logging;
                    updateLoggingStatusText(data.suppress_werkzeug_logging);
                }
            } catch (e) {
                console.error('Failed to load logging settings:', e);
            }
        },

        async loadMaxTokens() {
            try {
                const response = await fetch('/api/settings/max_tokens');
                const data = await response.json();
                if (data.success) {
                    if (settingsManager.state) settingsManager.state.maxTokens = data.max_tokens;
                    const el = document.getElementById('maxTokensInput');
                    if (el) el.value = data.max_tokens;
                    updateMaxTokensStatusText(data.max_tokens);
                }
            } catch (e) {
                console.error('Failed to load max tokens:', e);
            }
        },

        async loadTemperature() {
            try {
                const response = await fetch('/api/settings/temperature');
                const data = await response.json();
                if (data.success) {
                    if (settingsManager.state) settingsManager.state.temperature = data.temperature;
                    const el = document.getElementById('temperatureInput');
                    if (el) el.value = data.temperature;
                    updateTemperatureStatusText(data.temperature);
                }
            } catch (e) {
                console.error('Failed to load temperature:', e);
            }
        },

        async loadMaxResponseLength() {
            try {
                const response = await fetch('/api/settings/max_response_length');
                const data = await response.json();
                if (data.success) {
                    if (settingsManager.state) settingsManager.state.maxResponseLength = data.max_response_length;
                    const el = document.getElementById('maxResponseLengthInput');
                    if (el) el.value = data.max_response_length;
                    updateMaxResponseLengthStatusText(data.max_response_length);
                }
            } catch (e) {
                console.error('Failed to load max_response_length:', e);
            }
        },

        async loadDelaySettings() {
            try {
                const response = await fetch('/api/settings/delay');
                const data = await response.json();
                if (data.success) {
                    if (settingsManager.state) settingsManager.state.messageDelay = data.message_delay;
                    const el = document.getElementById('delayInput');
                    if (el) el.value = data.message_delay;
                    updateDelayStatusText(data.message_delay);
                }
            } catch (e) {
                console.error('Failed to load delay settings:', e);
            }
        },

        async loadSystemPrompt() {
            try {
                const response = await fetch('/api/settings/system_prompt');
                const data = await response.json();
                if (data.success) {
                    const textarea = document.getElementById('systemPromptTextarea');
                    if (textarea) textarea.value = data.system_prompt;
                    updateSystemPromptStatusText('Loaded');
                }
            } catch (e) {
                console.error('Failed to load system prompt:', e);
                updateSystemPromptStatusText('Error loading');
            }
        }
    };
}

// ==================== Settings Update Functions ====================

async function toggleWerkzeugLogging() {
    const checked = document.getElementById('suppressLoggingToggle').checked;
    try {
        const response = await fetch('/api/settings/logging', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ suppress_werkzeug_logging: checked })
        });
        const data = await response.json();
        if (data.success) {
            if (state) state.suppressWerkzeugLogging = data.suppress_werkzeug_logging;
            updateLoggingStatusText(data.suppress_werkzeug_logging);
            addMessage(checked ? '🔇 Werkzeug HTTP logging suppressed' : '🔊 Werkzeug HTTP logging enabled', 'system');
        } else {
            addMessage('Failed to update logging settings', 'error');
        }
    } catch (e) {
        addMessage('Error: ' + e.message, 'error');
        document.getElementById('suppressLoggingToggle').checked = !checked;
    }
}

function updateLoggingStatusText(suppressed) {
    const text = suppressed ? 'Suppressed ✅' : 'Not suppressed';
    const color = suppressed ? '#a6e3a1' : '#6c7086';
    const el = document.getElementById('loggingStatusText');
    if (el) { el.textContent = text; el.style.color = color; }
}

async function updateMaxTokens() {
    const input = document.getElementById('maxTokensInput');
    const tokens = parseInt(input.value);
    if (isNaN(tokens) || tokens < 1 || tokens > 65536) {
        addMessage('⚠️ Max tokens must be between 1 and 65536', 'error');
        if (state?.maxTokens) input.value = state.maxTokens;
        return;
    }
    try {
        const response = await fetch('/api/settings/max_tokens', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ max_tokens: tokens })
        });
        const data = await response.json();
        if (data.success) {
            if (state) state.maxTokens = tokens;
            updateMaxTokensStatusText(tokens);
            addMessage(`🧠 LM Studio max tokens set to {value}`, 'system');
        } else {
            addMessage('Failed to update max tokens settings', 'error');
            if (state) input.value = state.maxTokens;
        }
    } catch (e) {
        addMessage('Error: ' + e.message, 'error');
        if (state) input.value = state.maxTokens;
    }
}

function updateMaxTokensStatusText(value) {
    const text = `Currently set to ${value} tokens`;
    const el = document.getElementById('maxTokensStatusText');
    if (el) { el.textContent = text; el.style.color = '#a6e3a1'; }
}

async function updateTemperature() {
    const input = document.getElementById('temperatureInput');
    const temp = parseFloat(input.value);
    if (isNaN(temp) || temp < 0 || temp > 2) {
        addMessage('⚠️ Temperature must be between 0.0 and 2.0', 'error');
        if (state?.temperature) input.value = state.temperature;
        return;
    }
    try {
        const response = await fetch('/api/settings/temperature', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ temperature: temp })
        });
        const data = await response.json();
        if (data.success) {
            if (state) state.temperature = temp;
            updateTemperatureStatusText(temp);
            addMessage(`🌡️ LM Studio temperature set to {value}`, 'system');
        } else {
            addMessage('Failed to update temperature settings', 'error');
            if (state) input.value = state.temperature;
        }
    } catch (e) {
        addMessage('Error: ' + e.message, 'error');
        if (state) input.value = state.temperature;
    }
}

function updateTemperatureStatusText(value) {
    const text = `Currently set to ${value}`;
    const el = document.getElementById('temperatureStatusText');
    if (el) { el.textContent = text; el.style.color = '#a6e3a1'; }
}

async function updateMaxResponseLength() {
    const input = document.getElementById('maxResponseLengthInput');
    const length = parseInt(input.value);
    if (isNaN(length) || length < 100 || length > 10000) {
        addMessage('⚠️ Max response length must be between 100 and 10000', 'error');
        if (state?.maxResponseLength) input.value = state.maxResponseLength;
        return;
    }
    try {
        const response = await fetch('/api/settings/max_response_length', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ max_response_length: length })
        });
        const data = await response.json();
        if (data.success) {
            if (state) state.maxResponseLength = length;
            updateMaxResponseLengthStatusText(length);
            addMessage(`📏 Max response length set to {value} characters`, 'system');
        } else {
            addMessage('Failed to update max response length settings', 'error');
            if (state) input.value = state.maxResponseLength;
        }
    } catch (e) {
        addMessage('Error: ' + e.message, 'error');
        if (state) input.value = state.maxResponseLength;
    }
}

function updateMaxResponseLengthStatusText(value) {
    const text = `Currently set to ${value} characters`;
    const el = document.getElementById('maxResponseLengthStatusText');
    if (el) { el.textContent = text; el.style.color = '#a6e3a1'; }
}

async function updateMessageDelay() {
    const input = document.getElementById('delayInput');
    const delay = parseInt(input.value);
    if (isNaN(delay) || delay < 1 || delay > 30) {
        addMessage('⚠️ Delay must be between 1 and 30 seconds', 'error');
        if (state?.messageDelay) input.value = state.messageDelay;
        return;
    }
    try {
        const response = await fetch('/api/settings/delay', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message_delay: delay })
        });
        const data = await response.json();
        if (data.success) {
            if (state) state.messageDelay = delay;
            updateDelayStatusText(delay);
            addMessage(`⏱️ Discord bot message delay set to {value} seconds`, 'system');
        } else {
            addMessage('Failed to update delay settings', 'error');
            if (state) input.value = state.messageDelay;
        }
    } catch (e) {
        addMessage('Error: ' + e.message, 'error');
        if (state) input.value = state.messageDelay;
    }
}

function updateDelayStatusText(value) {
    const text = `Currently set to ${value}s`;
    const el = document.getElementById('delayStatusText');
    if (el) { el.textContent = text; el.style.color = '#a6e3a1'; }
}

// ==================== System Prompt Functions ====================

const DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant in a Discord server.";

async function saveSystemPrompt() {
    const prompt = document.getElementById('systemPromptTextarea').value;
    try {
        const response = await fetch('/api/settings/system_prompt', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ system_prompt: prompt })
        });
        const data = await response.json();
        if (data.success) {
            updateSystemPromptStatusText('Saved ✅');
            addMessage('🎭 Bot personality/system prompt updated', 'system');
        } else {
            addMessage('Failed to update system prompt', 'error');
            updateSystemPromptStatusText('Save failed');
        }
    } catch (e) {
        addMessage('Error: ' + e.message, 'error');
        updateSystemPromptStatusText('Error');
    }
}

async function resetSystemPrompt() {
    if (!confirm('Reset system prompt to default?')) return;
    document.getElementById('systemPromptTextarea').value = DEFAULT_SYSTEM_PROMPT;
    try {
        const response = await fetch('/api/settings/system_prompt', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ system_prompt: DEFAULT_SYSTEM_PROMPT })
        });
        const data = await response.json();
        if (data.success) {
            updateSystemPromptStatusText('Reset to default ✅');
            addMessage('🎭 System prompt reset to default', 'system');
        } else {
            addMessage('Failed to reset system prompt', 'error');
        }
    } catch (e) {
        addMessage('Error: ' + e.message, 'error');
    }
}

function updateSystemPromptStatusText(status) {
    const el = document.getElementById('systemPromptStatusText');
    if (el) {
        el.textContent = status;
        el.style.color = status.includes('Error') || status.includes('failed') ? '#f38ba8' : '#a6e3a1';
    }
}

// ==================== Memory Database Path Functions ====================

const DEFAULT_MEMORY_DB_PATH = "user/data/memory/memory.db";

async function loadMemoryDbPath() {
    try {
        const response = await fetch('/api/settings/memory_db_path');
        const data = await response.json();
        if (data.success) {
            const input = document.getElementById('memoryDbPath');
            if (input) input.value = data.memory_db_path;
            updateMemoryDbStatusText('Loaded');
        }
    } catch (e) {
        console.error('Failed to load memory_db_path:', e);
        updateMemoryDbStatusText('Error loading');
    }
}

async function saveMemoryDbPath() {
    const input = document.getElementById('memoryDbPath');
    const dbPath = input.value.trim();
    if (!dbPath) {
        addMessage('⚠️ Database path cannot be empty', 'error');
        updateMemoryDbStatusText('Save failed');
        return;
    }
    try {
        const response = await fetch('/api/settings/memory_db_path', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ memory_db_path: dbPath })
        });
        const data = await response.json();
        if (data.success) {
            updateMemoryDbStatusText('Saved ✅');
            addMessage(`💾 Memory database path set to ${dbPath}`, 'system');
        } else {
            addMessage(data.error || 'Failed to update memory database path', 'error');
            updateMemoryDbStatusText('Save failed');
        }
    } catch (e) {
        addMessage('Error: ' + e.message, 'error');
        updateMemoryDbStatusText('Error');
    }
}

async function resetMemoryDbPath() {
    if (!confirm('Reset memory database path to default?')) return;
    document.getElementById('memoryDbPath').value = DEFAULT_MEMORY_DB_PATH;
    try {
        const response = await fetch('/api/settings/memory_db_path', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ memory_db_path: DEFAULT_MEMORY_DB_PATH })
        });
        const data = await response.json();
        if (data.success) {
            updateMemoryDbStatusText('Reset to default ✅');
            addMessage('💾 Memory database path reset to default', 'system');
        } else {
            addMessage('Failed to reset memory database path', 'error');
        }
    } catch (e) {
        addMessage('Error: ' + e.message, 'error');
    }
}

function updateMemoryDbStatusText(status) {
    const el = document.getElementById('memoryDbStatusText');
    if (el) {
        el.textContent = status;
        el.style.color = status.includes('Error') || status.includes('failed') ? '#f38ba8' : '#a6e3a1';
    }
}
