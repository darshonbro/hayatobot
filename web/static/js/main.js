/**
 * Hayato On Fire — Frontend Interactions
 */

document.addEventListener('DOMContentLoaded', () => {
  // Dynamic current year in footer
  const yearEl = document.getElementById('current-year');
  if (yearEl) {
    yearEl.textContent = new Date().getFullYear();
  }

  // Copy bot invite button
  const copyBtn = document.getElementById('btn-copy-invite');
  if (copyBtn) {
    copyBtn.addEventListener('click', (e) => {
      e.preventDefault();
      const inviteUrl = copyBtn.getAttribute('data-url') || window.location.origin;
      navigator.clipboard.writeText(inviteUrl).then(() => {
        const originalText = copyBtn.innerHTML;
        copyBtn.innerHTML = '✓ Copied Link!';
        setTimeout(() => {
          copyBtn.innerHTML = originalText;
        }, 2000);
      });
    });
  }

  // Smooth command filter (if search input is present)
  const searchInput = document.getElementById('command-search');
  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      const query = e.target.value.toLowerCase().trim();
      const rows = document.querySelectorAll('.command-table tbody tr');
      rows.forEach(row => {
        const text = row.textContent.toLowerCase();
        row.style.display = text.includes(query) ? '' : 'none';
      });
    });
  }
});
