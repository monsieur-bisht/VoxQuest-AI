import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'VoxQuest AI — Voice-Driven RPG',
  description:
    'An AI-powered voice-driven RPG experience. Speak your choices and shape the story.',
  keywords: ['RPG', 'voice', 'AI', 'speech recognition', 'adventure'],
  authors: [{ name: 'VoxQuest AI Team' }],
  viewport: 'width=device-width, initial-scale=1',
  themeColor: '#0a0a0f',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="icon" href="/favicon.ico" sizes="any" />
      </head>
      <body className="bg-rpg-dark text-rpg-text antialiased min-h-screen font-sans">
        {children}
      </body>
    </html>
  );
}
