// Client module: adds a "Copy page as Markdown" button to every doc page,
// fetching the raw-markdown mirror emitted by plugins/llms-markdown-plugin.js
// (docs/foo -> docs/foo.md) and copying it to the clipboard.
function injectButton() {
  const container = document.querySelector('.theme-doc-markdown, article');
  if (!container || document.getElementById('copy-md-btn')) return;

  const btn = document.createElement('button');
  btn.id = 'copy-md-btn';
  btn.type = 'button';
  btn.textContent = 'Copy page as Markdown';
  btn.className = 'button button--secondary button--sm copy-md-button';
  btn.addEventListener('click', async () => {
    const mdUrl = window.location.pathname.replace(/\/$/, '') + '.md';
    try {
      const res = await fetch(mdUrl);
      if (!res.ok) throw new Error(`${res.status}`);
      const text = await res.text();
      await navigator.clipboard.writeText(text);
      const original = btn.textContent;
      btn.textContent = 'Copied!';
      setTimeout(() => (btn.textContent = original), 1500);
    } catch (err) {
      btn.textContent = 'Copy failed';
      setTimeout(() => (btn.textContent = 'Copy page as Markdown'), 1500);
    }
  });

  container.insertBefore(btn, container.firstChild);
}

if (typeof window !== 'undefined') {
  window.addEventListener('load', injectButton);
  // Docusaurus is an SPA — re-inject on client-side route changes.
  document.addEventListener('docusaurus.routeDidUpdate', injectButton);
}
