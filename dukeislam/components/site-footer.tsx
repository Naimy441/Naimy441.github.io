import Link from "next/link";
import { StarMark } from "@/components/site-header";

const explore = [
  { href: "/", label: "Home" },
  { href: "/food", label: "Food" },
  { href: "/events", label: "Events" },
];

const downloads = [
  {
    href: "https://github.com/Naimy441/Naimy441.github.io/raw/main/docs/outputs/halal_menus.pdf",
    label: "Menus PDF",
  },
  {
    href: "https://github.com/Naimy441/Naimy441.github.io/raw/main/docs/outputs/muslim_calendar.pdf",
    label: "Events PDF",
  },
];

export function SiteFooter() {
  return (
    <footer className="border-t border-border/50 bg-muted/30">
      <div className="mx-auto grid max-w-5xl gap-10 px-4 py-10 sm:px-6 md:grid-cols-[1.4fr_1fr_1fr]">
        <div className="space-y-3">
          <Link href="/" className="inline-flex items-center gap-2.5">
            <span className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <StarMark className="size-4.5" />
            </span>
            <span className="text-[15px] font-semibold tracking-tight">
              Duke<span className="font-display italic text-primary">Islam</span>
            </span>
          </Link>
          <p className="max-w-xs text-sm leading-relaxed text-muted-foreground">
            Not an official university
            website.
          </p>
        </div>

        <div className="space-y-3">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Explore
          </p>
          <ul className="space-y-2 text-sm">
            {explore.map((item) => (
              <li key={item.href}>
                <Link href={item.href} className="hover:text-primary">
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </div>

        <div className="space-y-3">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            More
          </p>
          <ul className="space-y-2 text-sm">
            {downloads.map((item) => (
              <li key={item.href}>
                <a
                  href={item.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-primary"
                >
                  {item.label}
                </a>
              </li>
            ))}
            <li>
              <a
                href="https://github.com/Naimy441/Naimy441.github.io"
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-primary"
              >
                GitHub
              </a>
            </li>
          </ul>
        </div>
      </div>
      <div className="border-t border-border/50">
        <p className="mx-auto max-w-5xl px-4 py-4 pb-[calc(1rem+3.5rem+env(safe-area-inset-bottom))] text-xs text-muted-foreground sm:px-6 md:pb-4">
          © {new Date().getFullYear()} DukeIslam. All rights reserved.
        </p>
      </div>
    </footer>
  );
}
