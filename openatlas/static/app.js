const form = document.querySelector('#search-form');
const query = document.querySelector('#question');
const saver = document.querySelector('#saver');
const results = document.querySelector('#results');
const status = document.querySelector('#status');
const button = document.querySelector('#search-button');
let requestNumber = 0;
let examples = {};
fetch('/api/examples').then(r => r.json()).then(data => { examples = data; }).catch(() => {});
function language() { return new FormData(form).get('language'); }
async function search() {
  if (!query.value.trim()) { query.focus(); return; }
  const thisRequest = ++requestNumber;
  results.setAttribute('aria-busy', 'true');
  button.disabled = true;
  status.textContent = 'Finding sources…';
  const params = new URLSearchParams({q: query.value, language: language(), mode: saver.checked ? 'compact' : 'expanded'});
  try {
    const response = await fetch('/api/search?' + params);
    const data = await response.json();
    if (thisRequest !== requestNumber) return;
    if (!response.ok) throw new Error(data.error || 'Search is unavailable. Try again.');
    results.replaceChildren();
    status.textContent = data.results.length ? `${data.results.length} sources · ${saver.checked ? 'Short previews' : 'Expanded previews'}` : data.message;
    data.results.forEach((item, i) => {
      const article = document.createElement('article'); article.className = 'result';
      const top = document.createElement('div'); top.className = 'result-top';
      const number = document.createElement('span'); number.className = 'result-number'; number.textContent = String(i + 1).padStart(2, '0');
      const h2 = document.createElement('h2'); h2.lang = item.language;
      const a = document.createElement('a'); a.href = item.source; a.rel = 'noreferrer'; a.textContent = item.title; h2.append(a); top.append(number, h2);
      const source = document.createElement('p'); source.className = 'source'; source.textContent = new URL(item.source).hostname + ' · Wikipedia';
      const preview = document.createElement('p'); preview.className = 'preview'; preview.lang = item.language; preview.textContent = item.preview;
      article.append(top, source, preview); results.append(article);
    });
  } catch (error) {
    if (thisRequest === requestNumber) { results.replaceChildren(); status.textContent = error.message; }
  } finally {
    if (thisRequest === requestNumber) { button.disabled = false; results.setAttribute('aria-busy', 'false'); }
  }
}
form.addEventListener('submit', event => { event.preventDefault(); search(); });
saver.addEventListener('change', () => { if (query.value.trim()) search(); });
document.querySelectorAll('input[name=language]').forEach(input => input.addEventListener('change', () => {
  requestNumber++; button.disabled = false; results.setAttribute('aria-busy', 'false');
  query.value = ''; query.lang = {english:'en',bengali:'bn',telugu:'te'}[language()];
  results.replaceChildren(); status.textContent = 'Ask a question in your selected language.'; query.focus();
}));
document.querySelector('#example').addEventListener('click', () => {
  if (examples[language()]) { query.value = examples[language()]; search(); }
});
