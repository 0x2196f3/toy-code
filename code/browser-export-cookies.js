(function exportCookies() {
  // Read cookies string
  const raw = document.cookie || '';
  // Parse into array of {name, value}
  const cookies = raw.split('; ').filter(Boolean).map(pair => {
    const eq = pair.indexOf('=');
    return {
      name: eq > -1 ? pair.slice(0, eq) : pair,
      value: eq > -1 ? pair.slice(eq + 1) : ''
    };
  });

  // Pack metadata for clarity
  const payload = {
    exportedAt: new Date().toISOString(),
    origin: location.origin,
    cookies
  };

  // Create blob and trigger download
  const blob = new Blob([JSON.stringify(payload, null, 2)], {type: 'application/json'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = (location.hostname || 'site') + '-cookies.json';
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);

  console.log('Exported', cookies.length, 'cookies');
})();
