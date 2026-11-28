import { api, getToken } from './auth';

/** The signed-in user's full profile (server side), or null. */
export async function getProfile() {
  const token = await getToken();
  if (!token) return null;
  const res = await api('/profile', { token });
  return res.ok ? res.data?.profile ?? null : null;
}

export { formatDate, initials } from './profile-format';
