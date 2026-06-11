// ==================== Token Metrics Functions ====================

function updateTokenMetrics(usage) {
    if (!usage) return;
    
    const promptTokens = usage.prompt_tokens || 0;
    const completionTokens = usage.completion_tokens || 0;
    const totalTokens = usage.total_tokens || 0;
    const tokensPerSecond = usage.tokens_per_second || 0;
    const totalTime = usage.total_time || 0;
    
    const promptEl = document.getElementById('promptTokens');
    const completionEl = document.getElementById('completionTokens');
    const totalEl = document.getElementById('totalTokens');
    const tpsEl = document.getElementById('tokensPerSecond');
    const timeEl = document.getElementById('totalTime');
    const statusEl = document.getElementById('tokenStatus');
    
    if (promptEl) promptEl.textContent = promptTokens.toLocaleString();
    if (completionEl) completionEl.textContent = completionTokens.toLocaleString();
    if (totalEl) totalEl.textContent = totalTokens.toLocaleString();
    if (tpsEl) tpsEl.textContent = tokensPerSecond > 0 ? `${tokensPerSecond} tok/s` : '-';
    if (timeEl) timeEl.textContent = totalTime > 0 ? `${totalTime}s` : '-';
    
    if (statusEl) {
        statusEl.className = 'token-metric-value status-done';
        statusEl.textContent = '✅ Complete';
    }
    
    if (typeof state !== 'undefined') state.lastTokenUsage = usage;
}

function setTokenGenerating() {
    const statusEl = document.getElementById('tokenStatus');
    if (statusEl) {
        statusEl.className = 'token-metric-value status-generating';
        statusEl.textContent = '⏳ Generating...';
    }
    
    const els = ['promptTokens', 'completionTokens', 'totalTokens', 'tokensPerSecond', 'totalTime'];
    els.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = '...';
    });
}

function setTokenIdle() {
    const statusEl = document.getElementById('tokenStatus');
    if (statusEl) {
        statusEl.className = 'token-metric-value status-idle';
        statusEl.textContent = 'Idle';
    }
    
    const els = ['promptTokens', 'completionTokens', 'totalTokens', 'tokensPerSecond', 'totalTime'];
    els.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = '-';
    });
}

function appendTokenStream(text) {
    if (typeof state === 'undefined') return;
    
    state.currentTokenStream += text;
    
    const container = document.getElementById('tokenStreamContent');
    if (!container) return;
    
    const placeholder = container.querySelector('.token-stream-placeholder');
    if (placeholder) placeholder.remove();
    
    container.innerHTML = '';
    
    const textDiv = document.createElement('div');
    textDiv.className = 'token-stream-text';
    textDiv.innerHTML = `<span>${escapeHtml(state.currentTokenStream)}</span>`;
    container.appendChild(textDiv);
    
    container.scrollTop = container.scrollHeight;
}

function showTokenUsageSummary(usage) {
    if (!usage) return;
    
    const container = document.getElementById('tokenStreamContent');
    if (!container) return;
    
    const usageDiv = document.createElement('div');
    usageDiv.className = 'token-stream-usage';
    usageDiv.textContent = `Tokens: ${usage.prompt_tokens} prompt + ${usage.completion_tokens} completion = ${usage.total_tokens} total | ${usage.tokens_per_second} tok/s | ${usage.total_time}s`;
    container.appendChild(usageDiv);
    container.scrollTop = container.scrollHeight;
}

function resetTokenMetrics() {
    setTokenIdle();
    if (typeof state !== 'undefined') {
        state.currentTokenStream = '';
        state.lastTokenUsage = null;
    }
    const container = document.getElementById('tokenStreamContent');
    if (container) {
        container.innerHTML = '<div class="token-stream-placeholder">Send a message in the Chat tab to see real-time token generation...</div>';
    }
}

async function loadLastTokenUsage() {
    try {
        const response = await fetch('/api/tokens/last');
        const data = await response.json();
        if (data.success && data.usage) {
            updateTokenMetrics(data.usage);
        }
    } catch (e) {
        console.error('Failed to load token usage:', e);
    }
}