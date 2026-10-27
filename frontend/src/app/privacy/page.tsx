"use client";

import LegalPage from "@/components/LegalPage";
import { PRIVACY } from "@/lib/legal";

export default function PrivacyPage() {
  return <LegalPage docs={PRIVACY} />;
}
