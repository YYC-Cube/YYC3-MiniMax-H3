// src/components/batches/RefineDrawer.tsx — 人工精评抽屉（1~10 滑条 + 缺陷标签 → /api/score）
import { useState } from "react";
import { Loader2, PencilLine } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { saveScore } from "@/lib/api";

const TAG_OPTIONS = ["口型错位", "抖动", "变脸", "手崩", "模糊", "肢体异常"];

export interface RefineDrawerProps {
  batch: string;
  refImg: string;
  seed: number;
  initialScore: number | null;
  initialTags: string;
}

export function RefineDrawer({ batch, refImg, seed, initialScore, initialTags }: RefineDrawerProps) {
  const [open, setOpen] = useState(false);
  const [score, setScore] = useState<number>(initialScore ?? 5);
  const [tags, setTags] = useState<string[]>(
    initialTags ? initialTags.split(",").map((t) => t.trim()).filter(Boolean) : []
  );
  const [saving, setSaving] = useState(false);

  const toggleTag = (t: string) =>
    setTags((prev) => (prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]));

  const save = async () => {
    setSaving(true);
    try {
      await saveScore({ batch, ref: refImg, seed, score, tags: tags.join(",") });
      toast.success(`已写回 report_batch${batch}.md（seed ${seed} · ${score}/10）`);
      setOpen(false);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="pt-1">
      <Button
        variant="outline"
        size="sm"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
      >
        <PencilLine />
        {open ? "收起精评" : "人工精评"}
      </Button>

      {open ? (
        <div className="mt-3 space-y-3 rounded-md border border-border bg-background p-3">
          <div>
            <label htmlFor={`score-${seed}`} className="mb-1 block text-xs text-muted-foreground">
              评分：{score}/10
            </label>
            <input
              id={`score-${seed}`}
              type="range"
              min={1}
              max={10}
              step={1}
              value={score}
              onChange={(e) => setScore(Number(e.target.value))}
              className="w-full"
            />
          </div>
          <div className="flex flex-wrap gap-2" role="group" aria-label="缺陷标签">
            {TAG_OPTIONS.map((t) => (
              <button
                key={t}
                onClick={() => toggleTag(t)}
                className={cn(
                  "rounded-full border px-2.5 py-0.5 text-xs transition-colors",
                  tags.includes(t)
                    ? "border-primary text-primary"
                    : "border-border text-muted-foreground hover:text-foreground"
                )}
              >
                {t}
              </button>
            ))}
          </div>
          <Button onClick={() => void save()} disabled={saving} className="w-full">
            {saving ? (
              <>
                <Loader2 className="animate-spin" />
                写回中…
              </>
            ) : (
              "保存并写回 report"
            )}
          </Button>
        </div>
      ) : null}
    </div>
  );
}
