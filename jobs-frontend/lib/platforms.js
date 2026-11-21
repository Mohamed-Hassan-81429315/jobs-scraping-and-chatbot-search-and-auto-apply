export const PLATFORMS = [
  { key: 'linkedin', label: 'LinkedIn' },
  { key: 'indeed', label: 'Indeed' },
  { key: 'glassdoor', label: 'Glassdoor' },
  { key: 'odoo', label: 'Odoo' },
  { key: 'smartrecruiters', label: 'SmartRecruiters' },
  { key: 'epam', label: 'EPAM' },
  { key: 'remoteok', label: 'RemoteOK' },
  { key: 'remotive', label: 'Remotive' },
  { key: 'arbeitnow', label: 'Arbeitnow' },
];

const LABELS = Object.fromEntries(PLATFORMS.map((p) => [p.key, p.label]));

export function platformLabel(key) {
  return LABELS[key] || key;
}
