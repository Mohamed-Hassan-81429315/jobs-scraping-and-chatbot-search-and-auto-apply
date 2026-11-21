export async function fetchSuggestions(q, signal) {
  const res = await fetch(`/api/suggest?q=${encodeURIComponent(q)}`, { signal });
  if (!res.ok) throw new Error('suggest failed');
  return res.json();
}
