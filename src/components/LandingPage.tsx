import SubjectsCarousel from "@/components/SubjectsCarousel";
import AnnouncementBar from "@/components/landing/AnnouncementBar";
import Header from "@/components/landing/Header";
import Hero from "@/components/landing/Hero";
import FeatureMarquee from "@/components/landing/FeatureMarquee";
import HowItWorks from "@/components/landing/HowItWorks";
import Trust from "@/components/landing/Trust";
import Faq from "@/components/landing/Faq";
import FinalCta from "@/components/landing/FinalCta";
import Footer from "@/components/landing/Footer";

export default function LandingPage({ apkSize }: { apkSize: string | null }) {
  return (
    <main className="flex min-h-screen flex-col overflow-x-clip bg-background">
      <AnnouncementBar />
      <Header />
      <Hero apkSize={apkSize} />
      <FeatureMarquee />
      <HowItWorks />
      <div id="subjects">
        <SubjectsCarousel />
      </div>
      <Trust />
      <Faq />
      <FinalCta />
      <Footer />
    </main>
  );
}
