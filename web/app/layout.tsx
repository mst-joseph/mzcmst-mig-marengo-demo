import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});
const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "AI Migration · Semantic Video Search",
  description:
    "MZC AI Migration PoC — natural-language semantic search over video embeddings stored in S3 Vectors.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body
        className={`${geistSans.variable} ${geistMono.variable} font-sans antialiased flex min-h-screen flex-col bg-background text-foreground`}
      >
        {children}
        <footer className="border-t border-border py-6 text-center text-xs text-muted-foreground">
          © 2026 Megazone Cloud Media Service Team · Author: Joseph Kim
          &lt;josephkim@megazone.com&gt;
        </footer>
      </body>
    </html>
  );
}
