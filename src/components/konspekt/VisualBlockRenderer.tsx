import MathText from "./MathText";

interface TimelineEvent {
  label?: string;
  date?: string;
  description?: string;
}
interface ProcessStep {
  title?: string;
  description?: string;
}
interface ComparisonItem {
  name?: string;
  values?: string[];
}
interface ConceptNode {
  id?: string;
  label?: string;
}
interface ConceptEdge {
  from?: string;
  to?: string;
  label?: string;
}

export interface VisualBlock {
  type: "table" | "timeline" | "flowchart" | "process" | "comparison" | "concept_map";
  title?: string;
  position_after?: string;
  
  image?: string;
  data?: {
    headers?: string[];
    rows?: string[][];
    events?: TimelineEvent[];
    steps?: ProcessStep[];
    criteria?: string[];
    items?: ComparisonItem[];
    nodes?: ConceptNode[];
    edges?: ConceptEdge[];
  };
}


export default function VisualBlockRenderer({ block }: { block: VisualBlock }) {
  const body = renderBody(block);
  if (!body) return null;

  return (
    <div className="mb-5 rounded-2xl border border-border-light bg-surface p-4">
      {block.title && <p className="mb-2 text-xs italic text-text-tertiary">{block.title}</p>}
      {body}
    </div>
  );
}

function renderBody(block: VisualBlock) {
  const data = block.data ?? {};
  switch (block.type) {
    case "table": {
      const headers = data.headers ?? [];
      const rows = data.rows ?? [];
      if (headers.length === 0 || rows.length === 0) return null;
      return <DataTable headers={headers} rows={rows} />;
    }
    case "comparison": {
      const criteria = data.criteria ?? [];
      const items = data.items ?? [];
      if (items.length === 0) return null;
      const headers = ["", ...criteria];
      const rows = items.map((it) => [it.name ?? "", ...(it.values ?? [])]);
      return <DataTable headers={headers} rows={rows} />;
    }
    case "timeline": {
      
      
      
      
      
      
      
      const events = data.events ?? [];
      if (events.length === 0) return null;
      return (
        <ol className="space-y-3 border-l-2 border-primary/30 pl-4">
          {events.map((ev, i) => (
            <li key={i} className="relative">
              <span className="absolute -left-[21px] top-1 h-2.5 w-2.5 rounded-full bg-primary" />
              <p className="text-sm font-semibold text-text-primary">
                {[ev.date, ev.label].filter(Boolean).join(" — ")}
              </p>
              {ev.description && <p className="mt-0.5 text-sm text-text-secondary">{ev.description}</p>}
            </li>
          ))}
        </ol>
      );
    }
    case "flowchart":
    case "process": {
      
      
      
      
      
      
      
      const steps = data.steps ?? [];
      if (steps.length === 0) return null;
      return (
        <ol className="space-y-2.5">
          {steps.map((step, i) => (
            <li key={i} className="flex gap-2">
              <span className="w-5 shrink-0 text-sm font-bold text-primary">{i + 1}.</span>
              <div className="min-w-0">
                {step.title && <p className="text-sm font-semibold text-text-primary">{step.title}</p>}
                {step.description && (
                  <p className="mt-0.5 text-sm leading-snug text-text-secondary">{step.description}</p>
                )}
              </div>
            </li>
          ))}
        </ol>
      );
    }
    case "concept_map": {
      
      
      
      
      
      
      const nodes = new Map((data.nodes ?? []).map((n) => [n.id ?? "", n.label ?? n.id ?? ""]));
      const edges = data.edges ?? [];
      if (edges.length === 0) return null;
      return (
        <ul className="space-y-1.5">
          {edges.map((edge, i) => (
            <li key={i} className="flex flex-wrap items-center gap-1.5 text-sm text-text-primary">
              <span className="rounded-lg bg-primary-50 px-2 py-0.5 font-medium text-primary-dark">
                {nodes.get(edge.from ?? "") ?? edge.from}
              </span>
              <span className="text-text-tertiary">→</span>
              <span className="rounded-lg bg-primary-50 px-2 py-0.5 font-medium text-primary-dark">
                {nodes.get(edge.to ?? "") ?? edge.to}
              </span>
              {edge.label && <span className="text-xs italic text-text-tertiary">({edge.label})</span>}
            </li>
          ))}
        </ul>
      );
    }
    default:
      return null;
  }
}

function DataTable({ headers, rows }: { headers: string[]; rows: string[][] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-left text-sm">
        <thead>
          <tr className="bg-primary text-white">
            {headers.map((h, i) => (
              <th key={i} className="px-3 py-2 font-semibold first:rounded-l-lg last:rounded-r-lg">
                <MathText text={h} />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, ri) => (
            <tr key={ri} className={ri % 2 === 1 ? "bg-primary-50" : ""}>
              {row.map((cell, ci) => (
                <td key={ci} className="px-3 py-2 text-text-primary">
                  <MathText text={cell} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
