document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.password-toggle').forEach(button => {
        button.addEventListener('click', () => {
            const inputId = button.getAttribute('data-toggle-for');
            const input = document.getElementById(inputId);

            if (input.type === 'password') {
                input.type = 'text';
                button.textContent = '🔒';
                button.setAttribute('aria-label', 'Hide password');
                button.setAttribute('aria-pressed', 'true');
            } else {
                input.type = 'password';
                button.textContent = '👁️';
                button.setAttribute('aria-label', 'Show password');
                button.setAttribute('aria-pressed', 'false');
            }
        });
    });
});
