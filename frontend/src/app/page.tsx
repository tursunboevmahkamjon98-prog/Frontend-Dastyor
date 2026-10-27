import fs from "node:fs";
import path from "node:path";
import LandingPage from "@/components/LandingPage";




function apkSizeMb(): string | null {
  try {
    const { size } = fs.statSync(path.join(process.cwd(), "public", "dastyor.apk"));
    return (size / (1024 * 1024)).toFixed(1);
  } catch {
    return null;
  }
}


export default function Home() {
  return <LandingPage apkSize={apkSizeMb()} />;
}
