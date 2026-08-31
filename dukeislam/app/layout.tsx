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
    default: "DukeIslam — Halal Food & Muslim Life Events",
    template: "%s · DukeIslam",
  },
  description:
    "Today's prayer times, halal food on campus, and Muslim Life events at Duke University.",
  openGraph: {
    title: "DukeIslam",
    description:
      "Today's prayer times, halal food on campus, and Muslim Life events at Duke.",
    url: "https://dukeislam.org",
    siteName: "DukeIslam",
    locale: "en_US",
    type: "website",
  },
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
