import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono, Instrument_Serif } from "next/font/google";
import { SiteHeader } from "@/components/site-header";
import { BottomNav } from "@/components/bottom-nav";
import { SiteFooter } from "@/components/site-footer";
import { TooltipProvider } from "@/components/ui/tooltip";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const instrumentSerif = Instrument_Serif({
  variable: "--font-instrument-serif",
  weight: "400",
  style: ["normal", "italic"],
  subsets: ["latin"],
});

export const metadata: Metadata = {
  metadataBase: new URL("https://dukeislam.org"),
  title: {
    default: "Duke Islam — Halal Dining, Prayer Times & Muslim Events | Duke University",
    template: "%s · Duke Islam",
  },
  description:
    "Duke Islam is the essential campus guide for Duke University: live halal dining menus, daily prayer times, Muslim Life events, and interactive campus dining map.",
  keywords: [
    "Duke Islam",
    "DukeIslam",
    "Duke University Islam",
    "Duke Muslim Students",
    "Duke MSA",
    "Duke Muslim Life",
    "Duke Halal",
    "Duke Halal Dining",
    "Duke Halal Food",
    "Duke Prayer Times",
    "Brodhead Center Halal",
    "Duke University",
  ],
  authors: [{ name: "Duke Islam", url: "https://dukeislam.org" }],
  creator: "Duke Islam",
  publisher: "Duke Islam",
  alternates: {
    canonical: "https://dukeislam.org",
  },
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "any" },
      { url: "/icon-48.png", sizes: "48x48", type: "image/png" },
      { url: "/icon-96.png", sizes: "96x96", type: "image/png" },
      { url: "/icon-192.png", sizes: "192x192", type: "image/png" },
      { url: "/icon-512.png", sizes: "512x512", type: "image/png" },
    ],
    apple: [
      { url: "/apple-touch-icon.png", sizes: "180x180", type: "image/png" },
    ],
    shortcut: "/favicon.ico",
  },
  openGraph: {
    title: "Duke Islam — Campus Halal Dining, Prayer Times & Events",
    description:
      "Duke Islam: daily campus halal menus, verified Duke prayer times, and Muslim student life events at Duke University.",
    url: "https://dukeislam.org",
    siteName: "Duke Islam",
    locale: "en_US",
    type: "website",
    images: [
      {
        url: "/icon-512.png",
        width: 512,
        height: 512,
        alt: "Duke Islam — Duke University",
      },
    ],
  },
  twitter: {
    card: "summary",
    title: "Duke Islam — Halal Dining & Muslim Life at Duke University",
    description:
      "Campus prayer times, daily halal food menus, and Muslim student events at Duke.",
    images: ["/icon-512.png"],
  },
};

const jsonLd = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "WebSite",
      "@id": "https://dukeislam.org/#website",
      "url": "https://dukeislam.org",
      "name": "Duke Islam",
      "alternateName": [
        "DukeIslam",
        "Duke University Islam",
        "Duke Muslim Students",
        "Duke Muslim Life",
        "Duke Halal Dining",
        "Duke MSA"
      ],
      "description": "Duke Islam: Campus prayer times, halal dining, and Muslim Life events at Duke University.",
      "inLanguage": "en-US"
    },
    {
      "@type": "EducationalOrganization",
      "@id": "https://dukeislam.org/#organization",
      "name": "Duke Islam",
      "alternateName": [
        "DukeIslam",
        "Duke Muslim Students Association",
        "Duke Muslim Life"
      ],
      "url": "https://dukeislam.org",
      "logo": {
        "@type": "ImageObject",
        "url": "https://dukeislam.org/icon-512.png",
        "width": 512,
        "height": 512
      }
    }
  ]
};

export const viewport: Viewport = {
  themeColor: "#012169",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} ${instrumentSerif.variable} h-full antialiased`}
    >
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      </head>
      <body className="flex min-h-dvh flex-col">
        <TooltipProvider>
          <SiteHeader />
          <main className="flex-1">{children}</main>
          <SiteFooter />
          <BottomNav />
        </TooltipProvider>
      </body>
    </html>
  );
}
