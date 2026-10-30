import SubjectsCarousel from "@/components/SubjectsCarousel";
import Header from "@/components/landing/Header";
import Hero from "@/components/landing/Hero";
import Features from "@/components/landing/Features";
import HowItWorks from "@/components/landing/HowItWorks";
import Trust from "@/components/landing/Trust";
import Faq from "@/components/landing/Faq";
import FinalCta from "@/components/landing/FinalCta";
import Footer from "@/components/landing/Footer";

export default function LandingPage() {
  return (
    <main className="flex min-h-screen flex-col overflow-x-clip bg-background">
      <Header />
      <Hero />
      <Features />
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
