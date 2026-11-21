import '@/app/brand.css';
import BrandLogo from './BrandLogo';

export default function AuthShell({ title, intro, children, footer }) {
  return (
    <div className="auth">
      <aside className="auth__panel" aria-hidden="false">
        <BrandLogo light />
        <div>
          <p className="auth__pitch">Your next role is already listed. Applyra finds it and helps you apply.</p>
          <ul className="auth__points">
            <li>Fresh listings pulled daily from company career pages</li>
            <li>Search by chatting, in plain language</li>
            <li>Apply faster with your details ready</li>
          </ul>
        </div>
        <p className="auth__fine">Your password is stored hashed. We never see it.</p>
      </aside>
      <section className="auth__main">
        <div className="auth__card">
          <h1>{title}</h1>
          {intro && <p className="auth__intro">{intro}</p>}
          {children}
          {footer && <p className="auth__footer">{footer}</p>}
        </div>
      </section>
    </div>
  );
}
