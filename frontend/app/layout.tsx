import type { Metadata, Viewport } from 'next';
import React from 'react';
import './globals.css';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import SWRegister from './components/SWRegister';

export const metadata: Metadata = {
  title: 'ConstructionOS - AI Site Operations Cockpit',
  description: 'Real-time multi-agent safety compliance, financial exposure calculation, and trade-off orchestration platform.',
  manifest: '/manifest.json',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'black-translucent',
    title: 'ConstructionOS',
  },
  icons: {
    icon: [
      { url: '/icons/icon-192x192.png', sizes: '192x192', type: 'image/png' },
      { url: '/icons/icon-512x512.png', sizes: '512x512', type: 'image/png' },
    ],
    apple: [
      { url: '/icons/apple-touch-icon.png', sizes: '180x180', type: 'image/png' },
    ],
  },
};

export const viewport: Viewport = {
  themeColor: '#020617',
  width: 'device-width',
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-slate-950 text-slate-100 antialiased selection:bg-sky-500/30 selection:text-sky-200 flex flex-col font-sans">
        <SWRegister />
        <Navbar />
        <div className="flex-1">
          {children}
        </div>
        <Footer />
      </body>
    </html>
  );
}

