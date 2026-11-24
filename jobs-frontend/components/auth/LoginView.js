import Link from 'next/link';
import AuthShell from './AuthShell';
import LoginForm from './LoginForm';

function safeNext(value) {
  const v = typeof value === 'string' ? value : '/';
  return v.startsWith('/') && !v.startsWith('//') && !v.includes('\\') ? v : '/';
}

/**
 * The login screen. Rendered at "/" for visitors who are not logged in,
 * and at "/login" (used by ?next= redirects). One component, so they never drift apart.
 * params = the page's searchParams: next, registered=1, reset=1
 */
export default function LoginView({ params = {} }) {
  const next = safeNext(params.next);
  const registered = params.registered === '1';
  const reset = params.reset === '1';

  const title = registered ? 'Account created' : reset ? 'Password updated' : 'Welcome back';
  const lead = registered
    ? 'Your account is ready. Log in to continue.'
    : reset
      ? 'Your password was changed. Log in with the new one.'
      : 'Log in to continue.';

  return (
    <AuthShell
      title={title}
      lead={lead}
      footer={
        <>
          New here?{' '}
          <Link href={`/register?next=${encodeURIComponent(next)}`} prefetch={false}>Create an account</Link>
        </>
      }
    >
      <LoginForm next={next} />
      {/* If LoginForm already shows a "Forgot password?" link, delete this paragraph. */}
      <p className="auth-forgot">
        <Link href="/forgot-password" prefetch={false}>Forgot your password?</Link>
      </p>
    </AuthShell>
  );
}
