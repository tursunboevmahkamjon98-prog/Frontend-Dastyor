"use client";

import { magicSfx } from "./sounds";


export interface BoxTheme {
  
  lid: string;
  lidEdge: string;
  body: string;
  bodyShade: string;
  glow: string;
  ribbon: string;
}

export const BOX_THEME: BoxTheme = {
  lid: "linear-gradient(160deg,#d8b4fe 0%,#a855f7 45%,#7e22ce 100%)",
  lidEdge: "#581c87",
  body: "linear-gradient(165deg,#c084fc 0%,#9333ea 40%,#6b21a8 100%)",
  bodyShade: "#4c1d95",
  glow: "#a855f7",
  ribbon: "#fde68a",
};


export default function MagicBox({
  x,
  swapMs,
  absorbing,
  lidUp,
  lidClosing,
  shuffling,
  dimmed,
  opening,
  opened,
  clickable,
  showPrize,
  lidDelayMs,
  onPick,
  label,
}: {
  
  x: number;
  
  swapMs: number;
  
  absorbing: boolean;
  
  lidUp: boolean;
  
  lidClosing: boolean;
  
  shuffling: boolean;
  
  dimmed: boolean;
  
  opening: boolean;
  
  opened: boolean;
  clickable: boolean;
  
  showPrize: boolean;
  
  lidDelayMs: number;
  onPick: () => void;
  label: string;
}) {
  const theme = BOX_THEME;
  const lidOff = opening || opened || lidUp;

  return (
    <button
      type="button"
      disabled={!clickable}
      onClick={onPick}
      onMouseEnter={() => clickable && magicSfx.hover()}
      aria-label={label}
      
      
      
      
      
      className={`absolute bottom-0 left-0 h-[132px] w-[104px] origin-bottom transition-[transform,opacity,filter] ${
        clickable ? "cursor-pointer" : "cursor-default"
      }`}
      style={{
        
        
        
        transform: `translateX(${x}px)`,
        transitionDuration: `${swapMs}ms`,
        transitionTimingFunction: "cubic-bezier(0.34, 1.3, 0.64, 1)",
        opacity: dimmed ? 0.35 : 1,
        filter: dimmed ? "saturate(0.5) brightness(0.7)" : undefined,
        zIndex: opening || opened || absorbing ? 30 : shuffling ? 20 - x / 1000 : 10,
      }}
    >
      {}
      <div
        className="relative h-full w-full"
        style={{
          animation: absorbing
            ? "mbox-absorb 0.5s ease-out"
            : opening
              ? "mbox-shake 0.45s ease-in-out"
              : shuffling
                ? `mbox-swap-hop ${swapMs}ms ease-in-out infinite`
                : 
                  
                  
                  "mbox-float 3s ease-in-out infinite",
        }}
      >
        {}
        <span
          className="pointer-events-none absolute -bottom-2 left-1/2 h-3 w-[86px] -translate-x-1/2 rounded-[50%] bg-black/45 blur-[6px]"
          aria-hidden
        />

        {}
        <span
          className="pointer-events-none absolute inset-x-1 bottom-2 top-6 rounded-[26px] blur-xl"
          style={{
            background: theme.glow,
            animation: `mbox-glow ${absorbing ? "0.5s" : "2.4s"} ease-in-out infinite`,
          }}
          aria-hidden
        />

        {}
        {}
        {(showPrize || lidUp) && lidOff && (
          <>
            <span
              className="pointer-events-none absolute bottom-[62px] left-1/2 h-24 w-16 origin-bottom -translate-x-1/2"
              style={{
                background: `linear-gradient(to top, ${theme.glow}, transparent)`,
                clipPath: "polygon(30% 100%, 70% 100%, 100% 0, 0 0)",
                animation: "mbox-lightbeam 1.2s ease-out forwards",
              }}
              aria-hidden
            />
            {[
              { sx: -34, sy: -78 },
              { sx: 30, sy: -88 },
              { sx: -8, sy: -104 },
              { sx: 46, sy: -58 },
              { sx: -50, sy: -50 },
            ].map((s, i) => (
              <span
                key={i}
                className="pointer-events-none absolute bottom-[68px] left-1/2 text-lg"
                style={{
                  ["--sx" as string]: `${s.sx}px`,
                  ["--sy" as string]: `${s.sy}px`,
                  animation: `mbox-starfly 0.9s ease-out ${i * 0.07}s forwards`,
                }}
                aria-hidden
              >
                ⭐
              </span>
            ))}
          </>
        )}

        {}
        <span
          className="absolute inset-x-0 bottom-0 h-[92px] rounded-b-2xl rounded-t-md shadow-[0_10px_0_rgba(0,0,0,0.25),0_18px_28px_rgba(0,0,0,0.4)]"
          style={{ background: theme.body, border: `2px solid ${theme.bodyShade}` }}
          aria-hidden
        >
          {}
          <span className="absolute inset-y-0 left-1/2 w-4 -translate-x-1/2 opacity-90" style={{ background: theme.ribbon }} />
          {}
          <span className="absolute inset-y-1 left-2 w-4 rounded-full bg-white/30 blur-[2px]" />
          {}
          <span
            className="absolute inset-0 flex items-center justify-center text-4xl font-black text-white"
            style={{ textShadow: "0 2px 0 rgba(0,0,0,0.35), 0 0 14px rgba(255,255,255,0.6)" }}
          >
            ?
          </span>
        </span>

        {}
        <span
          className="absolute inset-x-[-6px] bottom-[86px] h-[30px] rounded-lg shadow-[0_5px_0_rgba(0,0,0,0.25)]"
          style={{
            background: theme.lid,
            border: `2px solid ${theme.lidEdge}`,
            transformOrigin: "center bottom",
            animation: lidOff
              ? "mbox-lid-open 0.55s cubic-bezier(0.3,1.2,0.6,1) forwards"
              : lidClosing
                ? "mbox-lid-close 0.5s cubic-bezier(0.4,0,0.6,1) backwards"
                : undefined,
            animationDelay: opening ? "0.4s" : `${lidDelayMs}ms`,
          }}
          aria-hidden
        >
          <span className="absolute inset-x-0 top-1 h-1.5 bg-white/25" />
          <span className="absolute left-1/2 top-[-10px] h-3 w-8 -translate-x-1/2 rounded-t-full" style={{ background: theme.ribbon }} />
        </span>
      </div>
    </button>
  );
}
