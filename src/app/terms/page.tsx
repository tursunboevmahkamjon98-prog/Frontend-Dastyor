"use client";

import LegalPage from "@/components/LegalPage";
import { TERMS } from "@/lib/legal";

export default function TermsPage() {
  return <LegalPage docs={TERMS} />;
}
