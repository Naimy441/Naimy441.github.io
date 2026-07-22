import { CalendarDays, Home, UtensilsCrossed, type LucideIcon } from "lucide-react";

export interface NavLink {
  href: string;
  label: string;
  icon: LucideIcon;
}

export const navLinks: NavLink[] = [
  { href: "/", label: "Home", icon: Home },
  { href: "/food", label: "Halal Food", icon: UtensilsCrossed },
  { href: "/events", label: "Events", icon: CalendarDays },
];
