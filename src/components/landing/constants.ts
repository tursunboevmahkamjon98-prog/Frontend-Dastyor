import {
  BookOpen, Presentation, ClipboardCheck, Lightbulb, ClipboardList, Gamepad2,
  Sparkles, Zap, ShieldCheck, Clock, FileDown, Languages, Wand2, Wallet, Pencil,
} from "lucide-react";
import type { MessageKey } from "@/lib/messages";

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

export const FACTS = [
  { icon: Zap, key: "landing.fact.fast" },
  { icon: ShieldCheck, key: "landing.fact.clean" },
  { icon: Clock, key: "landing.fact.plan" },
] as const;

export const STEPS = [
  { n: "01", icon: Wand2, title: "landing.step1.title", desc: "landing.step1.desc" },
  { n: "02", icon: Sparkles, title: "landing.step2.title", desc: "landing.step2.desc" },
  { n: "03", icon: FileDown, title: "landing.step3.title", desc: "landing.step3.desc" },
] as const;

export const ALL_AT_ONCE_POINTS = [
  "landing.all.point1",
  "landing.all.point2",
  "landing.all.point3",
] as const;

export const TRUST = [
  { icon: Wallet, title: "landing.trust1.title", desc: "landing.trust1.desc" },
  { icon: Pencil, title: "landing.trust2.title", desc: "landing.trust2.desc" },
  { icon: FileDown, title: "landing.trust3.title", desc: "landing.trust3.desc" },
  { icon: Languages, title: "landing.trust4.title", desc: "landing.trust4.desc" },
] as const;

export const NAV_LINKS = [
  { href: "#features", label: "landing.nav.features" },
  { href: "#how", label: "landing.nav.how" },
  { href: "#samples", label: "landing.nav.samples" },
  { href: "#subjects", label: "landing.nav.subjects" },
  { href: "#faq", label: "landing.nav.faq" },
] as const;
