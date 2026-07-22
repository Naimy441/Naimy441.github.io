import Link from "next/link";

const groups = [
  "Center for Muslim Life",
  "Muslim Students Association",
  "Grad & Professional MSA",
  "Black Muslim Coalition",
  "Students for Justice in Palestine",
  "One for All",
];

export function SiteFooter() {
  return (
    <footer className="border-t border-border/60 bg-muted/40">
      <div className="mx-auto grid max-w-5xl gap-8 px-4 py-10 sm:px-6 md:grid-cols-3">
        <div className="space-y-2">
          <p className="text-sm font-semibold">Islam @ Duke</p>
          <p className="text-sm leading-relaxed text-muted-foreground">
            A student-built guide to halal dining and Muslim Life events at Duke
            University. Menus refresh twice daily from Duke NetNutrition.
          </p>
        </div>
        <div className="space-y-2">
          <p className="text-sm font-semibold">Explore</p>
          <ul className="space-y-1.5 text-sm text-muted-foreground">
            <li>
              <Link href="/food" className="hover:text-foreground">
                Halal food on campus
              </Link>
            </li>
            <li>
              <Link href="/events" className="hover:text-foreground">
                Events calendar
              </Link>
            </li>
            <li>
              <a
                href="https://github.com/Naimy441/duke_halal"
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-foreground"
              >
                Source on GitHub
              </a>
            </li>
          </ul>
        </div>
        <div className="space-y-2">
          <p className="text-sm font-semibold">Communities</p>
          <ul className="space-y-1.5 text-sm text-muted-foreground">
            {groups.map((g) => (
              <li key={g}>{g}</li>
            ))}
          </ul>
        </div>
      </div>
      <div className="border-t border-border/60 py-4 text-center text-xs text-muted-foreground">
        dukeislam.org · Not an official Duke University website
      </div>
    </footer>
  );
}
