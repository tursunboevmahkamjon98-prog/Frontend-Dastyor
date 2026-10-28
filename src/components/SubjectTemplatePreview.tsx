import type { SubjectTemplate } from "@/lib/subject-templates";




function Figure({
  t, x, y, h, flip = false,
}: { t: SubjectTemplate; x: number; y: number; h: number; flip?: boolean }) {
  const a = t.accent;
  const headD = 0.23 * h;
  const torsoW = 0.3 * h;
  const torsoH = 0.34 * h;
  const torsoTop = y + 0.215 * h;
  const s = flip ? -1 : 1;
  return (
    <g>
      <rect x={x - 0.075 * h - 0.057 * h} y={torsoTop + torsoH - 0.02 * h}
        width={0.115 * h} height={0.4 * h} rx={0.057 * h} fill={a} />
      <rect x={x + 0.075 * h - 0.057 * h} y={torsoTop + torsoH - 0.02 * h}
        width={0.115 * h} height={0.4 * h} rx={0.057 * h} fill={a} />
      {}
      <rect x={x + s * (torsoW / 2) - 0.042 * h} y={torsoTop - 0.04 * h}
        width={0.085 * h} height={0.3 * h} rx={0.042 * h} fill={a}
        transform={`rotate(${s * -118} ${x + s * (torsoW / 2)} ${torsoTop + 0.02 * h})`} />
      <rect x={x - s * (torsoW / 2) - 0.042 * h} y={torsoTop - 0.02 * h}
        width={0.085 * h} height={0.3 * h} rx={0.042 * h} fill={a}
        transform={`rotate(${s * 18} ${x - s * (torsoW / 2)} ${torsoTop})`} />
      <rect x={x - torsoW / 2} y={torsoTop} width={torsoW} height={torsoH}
        rx={0.1 * h} fill={a} />
      <circle cx={x} cy={y + headD / 2} r={headD / 2} fill={a} />
    </g>
  );
}


function Composition({ t }: { t: SubjectTemplate }) {
  const a = t.accent;
  const s = t.support;
  const line = { fill: "none", stroke: s, strokeWidth: 1 } as const;

  switch (t.cover) {
    case "axis":            
      return (
        <g>
          <line x1={14} y1={44} x2={74} y2={44} stroke={s} strokeWidth={1} />
          <line x1={30} y1={14} x2={30} y2={56} stroke={s} strokeWidth={1} />
          <path d="M14 54 Q30 20 62 24" {...line} stroke={a} strokeWidth={1.6} />
          {[22, 38, 46, 54, 62].map((x) => (
            <line key={x} x1={x} y1={42} x2={x} y2={46} stroke={s} strokeWidth={0.8} />
          ))}
          <rect x={84} y={20} width={40} height={5} rx={2.5} fill={s} />
          <rect x={84} y={30} width={30} height={5} rx={2.5} fill={s} />
          <Figure t={t} x={100} y={38} h={22} />
        </g>
      );
    case "construction":    
      return (
        <g>
          <polygon points="20,54 56,54 38,20" {...line} stroke={a} strokeWidth={1.6} />
          <path d="M20 54 A36 36 0 0 1 56 54" {...line} />
          <path d="M12 58 A48 48 0 0 1 64 12" {...line} />
          <rect x={84} y={22} width={38} height={5} rx={2.5} fill={s} />
          <Figure t={t} x={100} y={36} h={22} />
        </g>
      );
    case "trajectory":      
      return (
        <g>
          {Array.from({ length: 11 }, (_, i) => {
            const p = i / 10;
            return <circle key={i} cx={14 + p * 56} cy={56 - (34 * p - 30 * p * p) * 1.6}
              r={1.5} fill={i % 3 ? s : a} />;
          })}
          <line x1={14} y1={58} x2={74} y2={58} stroke={s} strokeWidth={1} />
          <rect x={84} y={24} width={36} height={5} rx={2.5} fill={s} />
          <Figure t={t} x={100} y={36} h={22} />
        </g>
      );
    case "molecule":        
      return (
        <g>
          {[0, 1, 2].map((i) => (
            <polygon key={i} {...line} stroke={i === 1 ? a : s} strokeWidth={1.4}
              points={hex(24 + i * 20, i % 2 ? 44 : 34, 11)} />
          ))}
          <circle cx={12} cy={30} r={3.5} fill={s} />
          <rect x={84} y={24} width={38} height={5} rx={2.5} fill={s} />
          <Figure t={t} x={100} y={34} h={24} />
        </g>
      );
    case "organic":         
      return (
        <g>
          <circle cx={46} cy={38} r={20} fill={s} />
          <circle cx={46} cy={38} r={14} fill={a} />
          {[[14, 18], [80, 20], [12, 58], [80, 56]].map(([x, y], i) => (
            <g key={i}>
              <line x1={46} y1={38} x2={x + 8} y2={y + 4} stroke={s} strokeWidth={0.8} />
              <rect x={x} y={y} width={22} height={9} rx={4.5} {...line} stroke={a} />
            </g>
          ))}
          <Figure t={t} x={108} y={34} h={24} />
        </g>
      );
    case "globe":           
      return (
        <g>
          <circle cx={40} cy={38} r={22} {...line} stroke={a} strokeWidth={1.4} />
          <ellipse cx={40} cy={38} rx={8} ry={22} {...line} />
          <line x1={18} y1={38} x2={62} y2={38} stroke={s} strokeWidth={0.9} />
          <line x1={23} y1={26} x2={57} y2={26} stroke={s} strokeWidth={0.7} />
          <line x1={23} y1={50} x2={57} y2={50} stroke={s} strokeWidth={0.7} />
          <rect x={76} y={22} width={40} height={9} rx={1} strokeDasharray="3 2" {...line} stroke={a} />
          <rect x={76} y={38} width={32} height={9} rx={1} strokeDasharray="3 2" {...line} stroke={a} />
          <Figure t={t} x={112} y={36} h={22} />
        </g>
      );
    case "banner":          
      return (
        <g>
          <line x1={12} y1={38} x2={124} y2={38} stroke={a} strokeWidth={1.6} />
          {[26, 54, 82, 110].map((x, i) => (
            <g key={x}>
              <circle cx={x} cy={38} r={3} fill={a} />
              <line x1={x} y1={38} x2={x} y2={i % 2 ? 50 : 26} stroke={a} strokeWidth={1} />
              <rect x={x - 12} y={i % 2 ? 50 : 14} width={24} height={12} {...line} />
              <rect x={x - 12} y={i % 2 ? 50 : 14} width={24} height={1.6} fill={a} />
            </g>
          ))}
        </g>
      );
    case "terminal":        
      return (
        <g>
          <rect x={12} y={16} width={70} height={44} rx={4} {...line} stroke={a} />
          <line x1={12} y1={25} x2={82} y2={25} stroke={s} strokeWidth={0.9} />
          {[19, 26, 33].map((x, i) => (
            <circle key={x} cx={x} cy={20.5} r={2} fill={i ? s : a} />
          ))}
          {[32, 40, 48].map((y, i) => (
            <rect key={y} x={i === 1 ? 24 : 18} y={y} width={i === 1 ? 44 : 52}
              height={3.5} rx={1.75} fill={s} />
          ))}
          <Figure t={t} x={106} y={34} h={24} />
        </g>
      );
    case "page":            
    case "frontispiece":    
      return (
        <g>
          <rect x={16} y={14} width={54} height={48} {...line} stroke={a} />
          {t.cover === "page"
            ? <line x1={26} y1={14} x2={26} y2={62} stroke={a} strokeWidth={1} />
            : <rect x={20} y={18} width={46} height={40} {...line} />}
          {[22, 30, 38, 46, 54].map((y, i) => (
            <rect key={y} x={t.cover === "page" ? 30 : 26} y={y}
              width={i % 3 ? 34 : 22} height={2.5} rx={1.25} fill={s} />
          ))}
          <rect x={84} y={26} width={36} height={4} rx={2} fill={s} />
          <Figure t={t} x={104} y={34} h={24} />
        </g>
      );
    case "bubble":          
      return (
        <g>
          <rect x={14} y={18} width={50} height={24} rx={8} fill={s} />
          <polygon points="26,42 26,50 36,42" fill={s} />
          <rect x={48} y={38} width={44} height={22} rx={8} {...line} stroke={a} strokeWidth={1.4} />
          {[24, 34, 44].map((x) => <circle key={x} cx={x} cy={30} r={3} fill={a} />)}
          <Figure t={t} x={112} y={34} h={24} />
        </g>
      );
    case "ornament":        
      return (
        <g>
          {[0, 30, 60].map((r) => (
            <rect key={r} x={26} y={22} width={32} height={32} {...line}
              stroke={r === 30 ? a : s} transform={`rotate(${r} 42 38)`} />
          ))}
          <rect x={37} y={33} width={10} height={10} fill={a} transform="rotate(45 42 38)" />
          {[70, 80, 90, 100].map((x, i) => (
            <rect key={x} x={x} y={34} width={6} height={6} fill={i % 2 ? s : a}
              transform={`rotate(45 ${x + 3} 37)`} />
          ))}
        </g>
      );
    case "nodes":           
      return (
        <g>
          {[[24, 50], [44, 24], [68, 42], [96, 20], [88, 56]].map(([x, y], i, arr) =>
            i < arr.length - 1 ? (
              <line key={i} x1={x} y1={y} x2={arr[i + 1][0]} y2={arr[i + 1][1]}
                stroke={s} strokeWidth={1} />
            ) : null)}
          {[[24, 50, 7], [44, 24, 5], [68, 42, 6], [96, 20, 4], [88, 56, 5]].map(([x, y, r], i) => (
            <circle key={i} cx={x} cy={y} r={r} fill={i === 0 ? a : s} />
          ))}
        </g>
      );
    case "cycle":           
      return (
        <g>
          <circle cx={44} cy={38} r={20} {...line} stroke={a} strokeWidth={1.6} />
          <polygon points="44,14 49,20 39,20" fill={a} />
          <ellipse cx={44} cy={38} rx={10} ry={7} fill={s} transform="rotate(-25 44 38)" />
          <rect x={78} y={26} width={40} height={7} rx={3.5} fill={s} />
          <rect x={78} y={40} width={30} height={7} rx={3.5} fill={s} />
          <Figure t={t} x={112} y={34} h={22} />
        </g>
      );
    case "notebook":        
      return (
        <g>
          {[18, 28, 38, 48, 58].map((y) => (
            <line key={y} x1={14} y1={y} x2={92} y2={y} stroke={s} strokeWidth={0.8} />
          ))}
          <line x1={22} y1={10} x2={22} y2={64} stroke={a} strokeWidth={1} />
          <rect x={30} y={22} width={40} height={14} rx={4} fill={s} />
          <rect x={30} y={42} width={52} height={10} rx={4} fill={s} />
          <Figure t={t} x={108} y={30} h={28} />
        </g>
      );
    default:
      return (
        <g>
          <rect x={14} y={22} width={52} height={9} rx={4.5} fill={s} />
          <rect x={14} y={38} width={40} height={9} rx={4.5} fill={s} />
          <Figure t={t} x={104} y={30} h={26} />
        </g>
      );
  }
}

function hex(cx: number, cy: number, r: number): string {
  return Array.from({ length: 6 }, (_, i) => {
    const a = (Math.PI / 3) * i - Math.PI / 6;
    return `${(cx + r * Math.cos(a)).toFixed(1)},${(cy + r * Math.sin(a)).toFixed(1)}`;
  }).join(" ");
}

export function SubjectTemplatePreview({
  template,
  className = "",
}: {
  template: SubjectTemplate;
  className?: string;
}) {
  const t = template;
  const serif = t.serif ? "Georgia, 'Times New Roman', serif" : undefined;
  const banded = t.header === "band";

  return (
    <div
      className={`relative aspect-video w-full overflow-hidden rounded-lg border border-border-light ${className}`}
      style={{ background: t.bg }}
    >
      {}
      {banded && (
        <div className="absolute inset-x-0 top-0 h-[20%]" style={{ background: t.accent }} />
      )}
      {t.header === "hexband" && (
        <div className="absolute inset-x-0 top-0 h-[3px]" style={{ background: t.accent }} />
      )}
      {t.header === "index" && (
        <div className="absolute left-[4%] top-[9%] h-[18%] w-[2px]" style={{ background: t.accent }} />
      )}
      {t.header === "initial" && (
        <div className="absolute left-[3.5%] top-[14%] h-[16%] w-[3px]" style={{ background: t.accent }} />
      )}

      <div className="relative px-[7%] pt-[6%]">
        <div className="flex items-center gap-1">
          <span className="text-[6px] font-bold" style={{ color: banded ? "#fff" : t.accent }}>
            {t.header === "prompt" ? "> 02" : "02"}
          </span>
          <span className="text-[5px] font-semibold" style={{ color: banded ? "#ffffffcc" : "#9a9a9a" }}>
            · КЛЮЧЕВЫЕ ПОНЯТИЯ
          </span>
        </div>
        <div
          className="mt-[1px] text-[9px] font-bold leading-tight"
          style={{
            color: banded ? "#fff" : t.ink, fontFamily: serif,
            letterSpacing: t.header === "smallcaps" ? "0.08em" : undefined,
          }}
        >
          Заголовок слайда
        </div>

        {}
        {t.header === "rule" && <div className="mt-[2px] h-[2px] w-[14%]" style={{ background: t.accent }} />}
        {t.header === "index" && <div className="mt-[2px] h-[1.5px] w-[22%]" style={{ background: t.support }} />}
        {t.header === "lozenge" && <div className="mt-[2px] h-[3px] w-[16%] rounded-full" style={{ background: t.accent }} />}
        {t.header === "hexband" && <div className="mt-[2px] h-[2px] w-[18%]" style={{ background: t.accent }} />}
        {(t.header === "underline" || t.header === "prompt") && (
          <div className="mt-[2px] h-[1px] w-full" style={{ background: t.support }} />
        )}
        {t.header === "measure" && (
          <div className="relative mt-[2px] h-[4px] w-full">
            <div className="absolute inset-x-0 top-0 h-[1px]" style={{ background: t.support }} />
            {Array.from({ length: 9 }, (_, i) => (
              <div key={i} className="absolute top-0 w-[1px]"
                style={{ left: `${i * 12.5}%`, height: i % 2 ? 2 : 4, background: i % 2 ? t.support : t.accent }} />
            ))}
          </div>
        )}
        {t.header === "masthead" && (
          <>
            <div className="mt-[2px] h-[2px] w-full" style={{ background: t.accent }} />
            <div className="mt-[1px] h-[0.5px] w-full" style={{ background: t.support }} />
          </>
        )}
        {t.header === "ornamental" && (
          <div className="mt-[2px] flex items-center gap-[2px]">
            <div className="h-[1px] flex-1" style={{ background: t.support }} />
            <span className="h-[3px] w-[3px] rotate-45" style={{ background: t.accent }} />
            <div className="h-[1px] w-[10%]" style={{ background: t.support }} />
          </div>
        )}
      </div>

      {}
      <svg viewBox="0 0 138 72" className="absolute inset-x-0 bottom-[7%] top-[32%] h-[61%] w-full"
        preserveAspectRatio="xMidYMid meet" aria-hidden>
        <Composition t={t} />
      </svg>

      {}
      <div className="absolute inset-x-[7%] bottom-[5%] h-[1.5px]" style={{ background: `${t.ink}14` }}>
        <div className="h-full w-[35%]" style={{ background: t.accent }} />
      </div>
    </div>
  );
}

export default SubjectTemplatePreview;
