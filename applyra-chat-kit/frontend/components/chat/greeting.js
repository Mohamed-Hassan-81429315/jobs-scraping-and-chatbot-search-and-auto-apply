/**
 * Time-of-day greeting, based on the visitor's local clock.
 *   06:00-10:59  Good Morning
 *   11:00-17:59  Good Afternoon  (11-16 per spec; 16-18 was not specified, so it stays Afternoon)
 *   18:00-19:59  Good Evening
 *   20:00-05:59  Good Night
 */
export function greetingFor(date = new Date()) {
  const h = date.getHours();
  if (h >= 6 && h < 11) return 'Good Morning';
  if (h >= 11 && h < 18) return 'Good Afternoon';
  if (h >= 18 && h < 20) return 'Good Evening';
  return 'Good Night';
}
