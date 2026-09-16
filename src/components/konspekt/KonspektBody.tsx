import { useRef } from "react";
import { ImageDown, Loader2, RotateCw, Upload } from "lucide-react";
import { KONSPEKT_SECTION_ORDER } from "@/lib/konspekt-labels";
import { API_ORIGIN } from "@/lib/api";
import MathText from "./MathText";
import ImportantNoteCard from "./ImportantNoteCard";
import QuickCheckCard from "./QuickCheckCard";
import VisualBlockRenderer, { VisualBlock } from "./VisualBlockRenderer";
import { FormulaCards, ConceptCardGrid } from "./ConceptCardGrid";
import CodeBlock from "./CodeBlock";


export default function KonspektBody({
  content,
  onRegenerate,
  regenerating,
  onFetchImage,
  fetchingImage,
  onReplaceLessonImage,
  replacingLessonImage,
  onUploadLessonImage,
  uploadingLessonImage,
}: {
  content: Record<string, unknown>;
  onRegenerate?: (section: string) => void;
  regenerating?: string | null;
  
  onFetchImage?: () => void;
  fetchingImage?: boolean;
  
  onReplaceLessonImage?: (index: number) => void;
  replacingLessonImage?: number | null;
  
  onUploadLessonImage?: (index: number, file: File) => void;
  uploadingLessonImage?: number | null;
}) {
  const fileInputs = useRef<Record<number, HTMLInputElement | null>>({});
  const subtitle = content.subtitle as string | undefined;
  const importantNotes = (content.important_notes as string[] | undefined) ?? [];
  const rawBlocks = (content.visual_blocks as VisualBlock[] | undefined) ?? [];
  
  
  
  
  
  
  
  const formulas = (content.formulas as (string | { formula: string; explanation?: string })[] | undefined) ?? [];
  const conceptCards =
    (content.concept_cards as { title: string; tag?: string; table?: string[][]; formula?: string; note?: string }[] | undefined) ?? [];
  const mapImage = content.map_image as string | undefined;
  const mapLocations = (content.map_locations as string[] | undefined) ?? [];
  
  
  
  
  
  const realImage = content.real_image as { path: string; caption?: string } | undefined;
  
  
  
  
  
  const missingRealImage = Boolean(content.real_image_query) && !realImage?.path;
  const missingMapImage = mapLocations.length > 0 && !mapImage;
  
  
  
  const codeBlocks = (content.code_blocks as { language?: string; code: string; explanation?: string }[] | undefined) ?? [];
  
  
  
  const quickCheck = (content.quick_check as { question: string; answer?: string }[] | undefined) ?? [];
  
  
  
  
  
  
  const lessonImages =
    (content.lesson_images as { path: string; caption?: string; credit?: string; explanation?: string; position_after?: string }[] | undefined) ?? [];

  const knownKeys = new Set(KONSPEKT_SECTION_ORDER.map(([k]) => k));
  const blocksByAnchor = new Map<string, VisualBlock[]>();
  for (const block of rawBlocks) {
    if (!block || typeof block !== "object") continue;
    const anchor = block.position_after && knownKeys.has(block.position_after) ? block.position_after : "main_content";
    if (!blocksByAnchor.has(anchor)) blocksByAnchor.set(anchor, []);
    blocksByAnchor.get(anchor)!.push(block);
  }
  const lessonImagesByAnchor = new Map<string, { index: number; image: (typeof lessonImages)[number] }[]>();
  lessonImages.forEach((image, index) => {
    if (!image?.path) return;
    const anchor = image.position_after && knownKeys.has(image.position_after) ? image.position_after : "main_content";
    if (!lessonImagesByAnchor.has(anchor)) lessonImagesByAnchor.set(anchor, []);
    lessonImagesByAnchor.get(anchor)!.push({ index, image });
  });

  
  
  const hasHomework = Boolean(content.homework);

  return (
    <div>
      {subtitle && <p className="mb-6 text-sm italic text-text-secondary">{subtitle}</p>}
      {KONSPEKT_SECTION_ORDER.map(([key, label]) => {
        const value = content[key];
        const blocksHere = blocksByAnchor.get(key) ?? [];
        const lessonImagesHere = lessonImagesByAnchor.get(key) ?? [];
        const showNotesHere = key === "homework" && importantNotes.length > 0;
        const showCodeHere = key === "key_terms" && codeBlocks.length > 0;
        const showQuickCheckHere = key === "consolidation" && quickCheck.length > 0;

        if (!value && blocksHere.length === 0 && lessonImagesHere.length === 0 && !showNotesHere && !showCodeHere && !showQuickCheckHere) return null;

        return (
          <div key={key}>
            {showNotesHere && importantNotes.map((note, i) => <ImportantNoteCard key={i} text={note} />)}
            {value ? (
              <Section
                title={label}
                onRegenerate={onRegenerate ? () => onRegenerate(key) : undefined}
                regenerating={regenerating === key}
              >
                <SectionValue value={value} />
              </Section>
            ) : null}
            {key === "key_concepts" && (
              <>
                <FormulaCards formulas={formulas} />
                <ConceptCardGrid cards={conceptCards} />
              </>
            )}
            {key === "key_terms" &&
              codeBlocks.map((cb, i) => (
                <CodeBlock key={i} code={cb.code} language={cb.language} explanation={cb.explanation} />
              ))}
            {key === "real_life_examples" && mapImage && (
              <div className="mb-5 overflow-hidden rounded-2xl border border-border-light bg-surface">
                <img src={`${API_ORIGIN}${mapImage}`} alt={mapLocations.join(", ")} className="w-full" />
                {mapLocations.length > 0 && (
                  <p className="px-4 py-2 text-center text-xs text-text-tertiary">
                    {mapLocations.join(", ")} · © OpenStreetMap contributors
                  </p>
                )}
              </div>
            )}
            {key === "real_life_examples" && realImage?.path && (
              <div className="mb-5 flex flex-col items-center rounded-2xl border border-border-light bg-surface p-4">
                <img
                  src={`${API_ORIGIN}${realImage.path}`}
                  alt={realImage.caption ?? ""}
                  className="max-h-64 w-auto max-w-full object-contain"
                />
                {realImage.caption && (
                  <p className="mt-2 text-center text-xs text-text-tertiary">{realImage.caption} · Wikipedia</p>
                )}
              </div>
            )}
            {key === "real_life_examples" && onFetchImage && (missingRealImage || missingMapImage) && (
              <button
                onClick={onFetchImage}
                disabled={fetchingImage}
                className="mb-5 flex w-full items-center justify-center gap-2 rounded-2xl border border-dashed border-border-light bg-surface-muted py-3 text-sm font-medium text-text-secondary transition hover:border-primary hover:text-primary disabled:opacity-60"
              >
                {fetchingImage ? <Loader2 className="h-4 w-4 animate-spin" /> : <ImageDown className="h-4 w-4" />}
                {fetchingImage ? "Загружаем фото…" : "Загрузить фото"}
              </button>
            )}
            {blocksHere.map((block, i) => (
              <VisualBlockRenderer key={i} block={block} />
            ))}
            {lessonImagesHere.map(({ index, image }) => (
              <div key={index} className="mb-5 overflow-hidden rounded-2xl border border-border-light bg-surface">
                <img src={`${API_ORIGIN}${image.path}`} alt={image.caption ?? ""} className="w-full" />
                {(image.explanation || image.caption || image.credit) && (
                  <div className="px-4 py-2 text-center text-xs text-text-tertiary">
                    {image.explanation || image.caption}
                    {image.credit ? ` · ${image.credit}` : ""}
                  </div>
                )}
                {(onReplaceLessonImage || onUploadLessonImage) && (
                  <div className="flex border-t border-border-light">
                    {onReplaceLessonImage && (
                      <button
                        onClick={() => onReplaceLessonImage(index)}
                        disabled={replacingLessonImage === index || uploadingLessonImage === index}
                        className="flex flex-1 items-center justify-center gap-2 py-2 text-xs font-medium text-text-secondary transition hover:bg-surface-muted hover:text-primary disabled:opacity-60"
                      >
                        {replacingLessonImage === index ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <RotateCw className="h-3.5 w-3.5" />
                        )}
                        {replacingLessonImage === index ? "Ищем другое фото…" : "Заменить фото"}
                      </button>
                    )}
                    {onReplaceLessonImage && onUploadLessonImage && (
                      <div className="w-px bg-border-light" />
                    )}
                    {onUploadLessonImage && (
                      <>
                        <input
                          ref={(el) => { fileInputs.current[index] = el; }}
                          type="file"
                          accept="image/*"
                          className="hidden"
                          onChange={(e) => {
                            const file = e.target.files?.[0];
                            if (file) onUploadLessonImage(index, file);
                            e.target.value = "";
                          }}
                        />
                        <button
                          onClick={() => fileInputs.current[index]?.click()}
                          disabled={uploadingLessonImage === index || replacingLessonImage === index}
                          className="flex flex-1 items-center justify-center gap-2 py-2 text-xs font-medium text-text-secondary transition hover:bg-surface-muted hover:text-primary disabled:opacity-60"
                        >
                          {uploadingLessonImage === index ? (
                            <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          ) : (
                            <Upload className="h-3.5 w-3.5" />
                          )}
                          {uploadingLessonImage === index ? "Загружаем…" : "Своё фото"}
                        </button>
                      </>
                    )}
                  </div>
                )}
              </div>
            ))}
            {key === "consolidation" &&
              quickCheck.map((qc, i) => <QuickCheckCard key={i} question={qc.question} answer={qc.answer} />)}
          </div>
        );
      })}
      {!hasHomework && importantNotes.length > 0 && importantNotes.map((note, i) => <ImportantNoteCard key={i} text={note} />)}
    </div>
  );
}

function Section({
  title,
  children,
  onRegenerate,
  regenerating,
}: {
  title: string;
  children: React.ReactNode;
  onRegenerate?: () => void;
  regenerating?: boolean;
}) {
  return (
    <div className="mb-5 rounded-2xl border border-border-light bg-surface p-4">
      <div className="mb-2 flex items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-primary">{title}</h3>
        {onRegenerate && (
          <button
            onClick={onRegenerate}
            disabled={regenerating}
            title="Пересоздать этот раздел заново"
            className="shrink-0 rounded-lg p-1 text-text-tertiary hover:bg-surface-muted hover:text-primary disabled:opacity-50"
          >
            <RotateCw className={`h-3.5 w-3.5 ${regenerating ? "animate-spin" : ""}`} />
          </button>
        )}
      </div>
      <div className="text-sm leading-relaxed text-text-primary">{children}</div>
    </div>
  );
}

function SectionValue({ value }: { value: unknown }) {
  if (Array.isArray(value)) {
    return (
      <ul className="list-disc space-y-1.5 pl-4">
        {value.map((v, i) => (
          <li key={i}>
            <MathText text={String(v)} />
          </li>
        ))}
      </ul>
    );
  }
  return (
    <p className="whitespace-pre-line">
      <MathText text={String(value)} />
    </p>
  );
}
