import BrandLogo from './BrandLogo';

export default function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="site-footer__inner">
        <BrandLogo />
        <p>© {new Date().getFullYear()} Applyra. Job listings are collected from public company career pages.</p>
      </div>
    </footer>
  );
}
