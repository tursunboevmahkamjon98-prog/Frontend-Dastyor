import { BookMarked, ClipboardCheck, CreditCard, Home, Layers, User } from "lucide-react";
import type { MessageKey } from "./messages";

/* One definition of the dashboard's navigation, read by the sidebar, the
 * mobile tab bar and the top bar's title.
 *
 * It used to live inside layout.tsx as three separate literals — a sidebar
 * group list, a tab list, and nothing at all for the title, because the
 * desktop layout had no title. Keeping them apart meant a route could be
 * added to the sidebar and quietly missing from the tabs, which is what
 * had happened to Balance.
 */

export type NavItem = {
  href: string;
  labelKey: MessageKey;
  icon: typeof Home;
  /** Match the path exactly rather than by prefix. Only /dashboard needs
   *  this — every other route is a prefix of nothing. */
  exact?: boolean;
  /** Show in the mobile tab bar. The bar holds four items around the
   *  centre action; the rest stay in the sidebar and the profile page. */
  tab?: boolean;
};

export const CREATE_HREF = "/dashboard/create";

export const NAV_GROUPS: { labelKey: MessageKey; items: NavItem[] }[] = [
  {
    labelKey: "nav.groupMain",
    items: [
      { href: "/dashboard", labelKey: "nav.home", icon: Home, exact: true, tab: true },
      { href: "/dashboard/materials", labelKey: "nav.materials", icon: Layers, tab: true },
      { href: "/dashboard/materials?type=test", labelKey: "nav.tests", icon: ClipboardCheck },
      { href: "/dashboard/lessons", labelKey: "nav.lessons", icon: BookMarked, tab: true },
    ],
  },
  {
    labelKey: "nav.groupAccount",
    items: [
      { href: "/dashboard/billing", labelKey: "nav.balance", icon: CreditCard },
      { href: "/dashboard/profile", labelKey: "nav.profile", icon: User, tab: true },
    ],
  },
];

export const NAV_ITEMS: NavItem[] = NAV_GROUPS.flatMap((g) => g.items);

/** The four tabs, split around the centre create button. */
export const TAB_ITEMS = NAV_ITEMS.filter((i) => i.tab);

export function isActive(pathname: string, href: string, exact?: boolean) {
  if (href.includes("?")) return false;
  return exact ? pathname === href : pathname.startsWith(href);
}

/* Title for the top bar. Longest prefix wins so /dashboard/materials/x/y
 * still reads "Materials" rather than falling back to "Home", and the
 * create route gets its own label even though it is not a nav item. */
export function pageTitleKey(pathname: string): MessageKey {
  if (pathname.startsWith(CREATE_HREF)) return "nav.create";
  let best: NavItem | null = null;
  for (const item of NAV_ITEMS) {
    if (!isActive(pathname, item.href, item.exact)) continue;
    if (!best || item.href.length > best.href.length) best = item;
  }
  return best?.labelKey ?? "nav.home";
}
