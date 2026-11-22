import crypto from 'node:crypto';

export const COOKIE_NAME = 'hirelume_openai';

function secretKey() {
  const secret = process.env.CHAT_COOKIE_SECRET;
  if (!secret || secret.length < 32) {
    throw new Error('CHAT_COOKIE_SECRET is missing or too short (use at least 32 characters).');
  }
  return crypto.createHash('sha256').update(secret).digest();
}

/** AES-256-GCM: the API key is unreadable even if the cookie leaks. */
export function seal(plain) {
  const iv = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv('aes-256-gcm', secretKey(), iv);
  const encrypted = Buffer.concat([cipher.update(plain, 'utf8'), cipher.final()]);
  return Buffer.concat([iv, cipher.getAuthTag(), encrypted]).toString('base64url');
}

export function unseal(token) {
  try {
    const buf = Buffer.from(token, 'base64url');
    const decipher = crypto.createDecipheriv('aes-256-gcm', secretKey(), buf.subarray(0, 12));
    decipher.setAuthTag(buf.subarray(12, 28));
    return Buffer.concat([decipher.update(buf.subarray(28)), decipher.final()]).toString('utf8');
  } catch {
    return null;
  }
}

/** Basic CSRF defence for cookie-authenticated endpoints. */
export function sameOrigin(request) {
  if (request.headers.get('sec-fetch-site') === 'cross-site') return false;
  const origin = request.headers.get('origin');
  if (!origin) return true;
  const host = request.headers.get('x-forwarded-host') || request.headers.get('host');
  try {
    return new URL(origin).host === host;
  } catch {
    return false;
  }
}
