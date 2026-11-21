export default function AuthShell({ title, lead, footer, children }) {
  return (
    <main id="main" className="auth-wrap">
      <div className="auth-card">
        <h1>{title}</h1>
        <p className="lead">{lead}</p>
        {children}
        {footer && <p className="auth-foot">{footer}</p>}
      </div>
    </main>
  );
}
