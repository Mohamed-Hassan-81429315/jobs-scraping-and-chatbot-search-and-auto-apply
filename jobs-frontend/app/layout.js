import './globals.css';
import Link from 'next/link';
import { Suspense } from 'react';
import { Inter, Space_Grotesk } from 'next/font/google';
import { BRAND } from '../lib/brand';
import { getUser } from '../lib/auth';
import Image from 'next/image';
import { BRAND as APPLYRA } from '../lib/applyra-brand';
import UserMenu from '../components/UserMenu';
import ChatBootstrap from '../components/chat/ChatBootstrap';
import ChatWidget from '../components/chat/ChatWidget';

const body = Inter({ subsets: ['latin'], variable: '--font-body', display: 'swap' });
const display = Space_Grotesk({ subsets: ['latin'], variable: '--font-display', display: 'swap' });

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'http://localhost:3000';
const DEFAULT_TITLE = `${BRAND.name}: ${BRAND.tagline} Search jobs from every platform`;

export const metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: DEFAULT_TITLE,
    template: `%s | ${BRAND.name}`,
  },
  description: BRAND.description,
  applicationName: BRAND.name,
  openGraph: {
    type: 'website',
    siteName: BRAND.name,
    title: DEFAULT_TITLE,
    description: BRAND.description,
    url: '/',
  },
  twitter: { card: 'summary_large_image' },
  robots: { index: true, follow: true },
};

export const viewport = { themeColor: '#080c1a', colorScheme: 'dark' };

const organization = {
  '@context': 'https://schema.org',
  '@type': 'Organization',
  name: BRAND.name,
  url: SITE_URL,
  logo: `${SITE_URL}/applyra-logo.png`,
  description: BRAND.description,
};

export default async function RootLayout({ children }) {
  const user = await getUser(); // cached per request: UserMenu shares this call

  return (
    <html lang="en">
      <body className={`${body.variable} ${display.variable}`}>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(organization).replace(/</g, '\\u003c') }}
        />
        <a className="skip" href="#main">Skip to content</a>

        <header className="site-header">
          <div className="wrap">
            <Link href="/" className="brand" aria-label={`${APPLYRA.name} home`}>
              <Image src="/applyra-logo.png" alt="" width={32} height={32} priority style={{ width: 32, height: 'auto' }} />
              <span>{APPLYRA.name}</span>
            </Link>
            {user && (
              <nav className="nav" aria-label="Main">
                <Link href="/?remote=1" prefetch={false}>Remote jobs</Link>
                <Link href="/?posted=24h" prefetch={false}>New today</Link>
              </nav>
            )}
            <UserMenu />
            <ChatBootstrap />
          </div>
        </header>

        {children}

        <Suspense fallback={null}>
          <ChatWidget loggedIn={Boolean(user)} />
        </Suspense>

        <footer className="site-footer">
          <div className="wrap">
            <p>
              © {new Date().getFullYear()} {BRAND.name}. Listings are collected from public sources and licensed
              data providers; you apply on the original site.
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}