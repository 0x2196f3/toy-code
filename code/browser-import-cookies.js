// Example cookieJson string format:
// var cookieJson = '[{"name":"session","value":"abc123","path":"/","domain":"example.com","expires":"2026-12-31T23:59:59Z","secure":false,"sameSite":"Lax"}]';

(function loadCookiesFromJson() {
  if (typeof cookieJson !== 'string') {
    console.error('cookieJson must be a JSON string assigned to a global variable.');
    return;
  }

  let cookies;
  try {
    cookies = JSON.parse(cookieJson);
    if (!Array.isArray(cookies)) throw new Error('Parsed JSON is not an array.');
  } catch (e) {
    console.error('Failed to parse cookieJson:', e);
    return;
  }

  const now = Date.now();
  const setCount = {ok:0, skippedHttpOnly:0, failed:0};

  cookies.forEach(c => {
    try {
      if (!c || !c.name) throw new Error('Cookie object missing name.');

      // Skip HttpOnly cookies: cannot be set via document.cookie
      if (c.httpOnly) {
        setCount.skippedHttpOnly++;
        return;
      }

      const name = encodeURIComponent(String(c.name));
      const value = encodeURIComponent('value' in c ? String(c.value) : '');

      let cookieStr = name + '=' + value;

      // Path
      if (c.path) cookieStr += '; Path=' + c.path;
      // Domain: only set if it matches current host rules; setting cross-site domain may be ignored
      if (c.domain) cookieStr += '; Domain=' + c.domain;
      // Expires or Max-Age
      if (c.expires) {
        // Accept ISO string or numeric epoch seconds
        let exp;
        if (typeof c.expires === 'number') {
          // epoch seconds or ms? assume seconds if < 1e12
          exp = c.expires < 1e12 ? new Date(c.expires * 1000) : new Date(c.expires);
        } else {
          exp = new Date(c.expires);
        }
        if (!isNaN(exp.getTime())) cookieStr += '; Expires=' + exp.toUTCString();
      } else if (c.maxAge || c.max_age) {
        const max = Number(c.maxAge || c.max_age);
        if (!Number.isNaN(max)) cookieStr += '; Max-Age=' + Math.floor(max);
      }

      // Secure
      if (c.secure) cookieStr += '; Secure';
      // SameSite (Note: some browsers may require capitalization)
      if (c.sameSite) cookieStr += '; SameSite=' + c.sameSite;

      // Set the cookie
      document.cookie = cookieStr;
      setCount.ok++;
    } catch (err) {
      console.error('Failed to set cookie', c, err);
      setCount.failed++;
    }
  });

  console.log('Cookies processed:', setCount);
})();
