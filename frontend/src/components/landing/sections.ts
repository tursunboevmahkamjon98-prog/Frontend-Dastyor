import {
  BookOpen, ClipboardCheck, ClipboardList, Gamepad2, Lightbulb, Presentation,
} from "lucide-react";
import type { MessageKey } from "@/lib/messages";

/* Section ids and the nav that points at them, in one place so the header,
 * the mobile panel and the footer cannot drift apart — which they had,
 * the footer listing a set of links the header no longer matched. */

export const NAV_LINKS: { href: string; labelKey: MessageKey }[] = [
  { href: "#preview", labelKey: "landing.nav.preview" },
  { href: "#how", labelKey: "landing.nav.how" },
  { href: "#features", labelKey: "landing.nav.features" },
  { href: "#samples", labelKey: "landing.nav.samples" },
  { href: "#faq", labelKey: "landing.nav.faq" },
];

/* The six material types the product actually generates. Order is the one
 * the create screen offers them in, and the two that lead each row are the
 * two a teacher most often comes for. */
export const FEATURES = [
  { id: "konspekt", icon: BookOpen, bg: "bg-note-bg", color: "text-note-icon" },
  { id: "lektsiya", icon: Lightbulb, bg: "bg-lecture-bg", color: "text-lecture-icon" },
  { id: "test", icon: ClipboardCheck, bg: "bg-test-bg", color: "text-test-icon" },
  { id: "prezentatsiya", icon: Presentation, bg: "bg-pres-bg", color: "text-pres-icon" },
  { id: "amaliy", icon: ClipboardList, bg: "bg-amaliy-bg", color: "text-amaliy-icon" },
  { id: "igra", icon: Gamepad2, bg: "bg-igra-bg", color: "text-igra-icon" },
] as const;

export const featureTitleKey = (id: string) => `landing.feature.${id}.title` as MessageKey;
export const featureDescKey = (id: string) => `landing.feature.${id}.desc` as MessageKey;
