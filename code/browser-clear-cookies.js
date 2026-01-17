(function clearAllCookies() {
  const expire = 'Thu, 01 Jan 1970 00:00:00 GMT';
  const cookies = document.cookie ? document.cookie.split(';') : [];

  // Helper to set expired cookie with optional domain/path
  function expireCookie(name, domain, path) {
    let cookie = `${name}=; Expires=${expire};`;
    if (path) cookie += ` Path=${path};`;
    if (domain) cookie += ` Domain=${domain};`;
    // Secure and SameSite aren't needed for deletion; avoid HttpOnly (can't be set from JS)
    document.cookie = cookie;
  }

  // Gather candidate domains (current + parent domains)
  const hostParts = location.hostname.split('.');
  const domains = [];
  for (let i = 0; i < hostParts.length - 0; i++) {
    domains.push(hostParts.slice(i).join('.'));
  }

  // Common paths to try
  const paths = (() => {
    const p = new Set(['/']);
    let segs = location.pathname.split('/');
    let cur = '';
    for (let i = 0; i < segs.length; i++) {
      if (!segs[i]) continue;
      cur += '/' + segs[i];
      p.add(cur);
    }
    return Array.from(p);
  })();

  cookies.forEach(cookie => {
    const name = cookie.split('=')[0].trim();
    // Try without domain/path first
    expireCookie(name);
    // Try all domain + path combinations
    domains.forEach(d => paths.forEach(path => expireCookie(name, d, path)));
  });

  // Also clear storage
  try { localStorage.clear(); } catch (e) {}
  try { sessionStorage.clear(); } catch (e) {}

  console.info('clearAllCookies: attempted to remove', cookies.map(c => c.split('=')[0].trim()));
})();
