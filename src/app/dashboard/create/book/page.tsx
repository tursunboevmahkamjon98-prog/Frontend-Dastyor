import { redirect } from "next/navigation";

export default function BookCreateRedirect() {
  redirect("/dashboard/create");
}
