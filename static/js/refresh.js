// Palette: Auto-refresh and manual refresh logic
document.addEventListener('DOMContentLoaded', () => {
    // Auto-refresh every 30 seconds
    const AUTO_REFRESH_INTERVAL = 30000;
    setTimeout(() => window.location.reload(), AUTO_REFRESH_INTERVAL);

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
});
