// Palette: Auto-refresh and manual refresh logic
document.addEventListener('DOMContentLoaded', () => {
    // Auto-refresh every 30 seconds
    const AUTO_REFRESH_INTERVAL = 30000;
    let refreshTimer = setTimeout(() => window.location.reload(), AUTO_REFRESH_INTERVAL);

    // Manual refresh button
    const refreshBtn = document.getElementById('refresh-btn');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            // Slight delay so the click interaction is perceptible before reload
            setTimeout(() => {
                window.location.reload();
            }, 100);
        });
    }

    // Retrieve More Data logic
    const retrieveBtn = document.getElementById('retrieve-btn');
    const statusContainer = document.getElementById('fetch-status-container');

    if (retrieveBtn) {
        retrieveBtn.addEventListener('click', async () => {
            try {
                retrieveBtn.disabled = true;
                const response = await fetch('/retrieve_more', { method: 'POST' });
                const data = await response.json();

                if (response.ok) {
                    startPolling();
                } else {
                    showError(data.message || 'Failed to start retrieval');
                    retrieveBtn.disabled = false;
                }
            } catch (err) {
                showError('Network error');
                retrieveBtn.disabled = false;
            }
        });
    }

    function showError(msg) {
        if (statusContainer) {
            statusContainer.innerHTML = `<div class="fetch-status-error">Error: ${msg}</div>`;
        }
    }

    function showStatus(msg) {
        if (statusContainer) {
            statusContainer.innerHTML = `<div class="fetch-status-msg">${msg}</div>`;
        }
    }

    async function checkStatus() {
        try {
            const response = await fetch('/fetch_status');
            const state = await response.json();

            if (state.in_progress) {
                if (retrieveBtn) retrieveBtn.disabled = true;
                showStatus('🔄 Retrieving and processing 7 more days of data... Please wait.');
                // Disable auto-refresh while fetching
                clearTimeout(refreshTimer);
                return true;
            } else {
                if (state.error) {
                    showError(state.error);
                    if (retrieveBtn) retrieveBtn.disabled = false;
                    return false;
                }
                // If it was in progress but now isn't, and no error, reload
                return false;
            }
        } catch (err) {
            console.error('Error checking status:', err);
            return true; // Keep polling on network error
        }
    }

    let pollingInterval;
    function startPolling() {
        if (pollingInterval) return;

        pollingInterval = setInterval(async () => {
            const inProgress = await checkStatus();
            if (!inProgress) {
                clearInterval(pollingInterval);
                showStatus('✅ Done! Refreshing...');
                setTimeout(() => window.location.reload(), 1000);
            }
        }, 3000);
    }

    // Check on page load if a fetch is already happening
    checkStatus().then(inProgress => {
        if (inProgress) startPolling();
    });
});
