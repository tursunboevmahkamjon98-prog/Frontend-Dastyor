import type { ReactNode } from "react";
import Link from "next/link";
import { BILLING_ENABLED } from "@/lib/features";

export default function BillingLink({ children, className }: {
  children: ReactNode;
  className: string;
}) {
  if (!BILLING_ENABLED) {
    return (
      <div className={`${className} pointer-events-none`} aria-disabled="true">
        {children}
      </div>
    );
  }

  return <Link href="/dashboard/billing" className={className}>{children}</Link>;
}
