// src/components/tasks/TaskForm.tsx — 任务提交表单（prompt/档位/seed/参考图 base64）
import { useState } from "react";
import { Loader2, Send } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useTasksStore } from "@/stores/tasksSlice";

const MAX_REF_MB = 8;

export function TaskForm() {
  const submitting = useTasksStore((s) => s.submitting);
  const submit = useTasksStore((s) => s.submit);
  const load = useTasksStore((s) => s.load);

  const [prompt, setPrompt] = useState("");
  const [quality, setQuality] = useState<"preview" | "full">("preview");
  const [seed, setSeed] = useState("");
  const [file, setFile] = useState<File | null>(null);

  const handleSubmit = async () => {
    if (file && file.size > MAX_REF_MB * 1024 * 1024) {
      toast.error(`参考图超过 ${MAX_REF_MB}MB 上限（解码后须 ≤8MB）`);
      return;
    }
    let refImageB64: string | undefined;
    if (file) {
      try {
        refImageB64 = await new Promise<string>((resolve, reject) => {
          const r = new FileReader();
          r.onload = () => resolve(String(r.result).split(",")[1] ?? "");
          r.onerror = () => reject(new Error("参考图读取失败"));
          r.readAsDataURL(file);
        });
      } catch (e) {
        toast.error(e instanceof Error ? e.message : String(e));
        return;
      }
    }

    const res = await submit({
      prompt: prompt.trim() || undefined,
      quality,
      seed: seed ? Number(seed) : undefined,
      refImageB64,
      refImageName: file?.name,
    });

    if (res.ok) {
      toast.success(`已创建任务 ${res.id}（夜间窗口由 Mac runner 领取生成）`);
      setPrompt("");
      setSeed("");
      setFile(null);
      void load();
    } else {
      toast.error(res.error ?? "提交失败");
    }
  };

  return (
    <Card>
      <CardContent className="flex flex-col gap-3 pt-5">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="task-prompt">生成提示词（≤4000 字符）</Label>
          <Textarea
            id="task-prompt"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="留空 = runner 默认数字人模板"
            rows={3}
          />
        </div>
        <div className="flex flex-wrap items-end gap-4 text-sm">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="task-quality">档位</Label>
            <select
              id="task-quality"
              value={quality}
              onChange={(e) => setQuality(e.target.value as "preview" | "full")}
              className="h-9 rounded-md border border-input bg-transparent px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <option value="preview" className="bg-card">
                preview 快预览（夜间后白天迭代）
              </option>
              <option value="full" className="bg-card">
                full 全质量（约 4h/seed）
              </option>
            </select>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="task-seed">Seed</Label>
            <Input
              id="task-seed"
              value={seed}
              onChange={(e) => setSeed(e.target.value.replace(/\D/g, ""))}
              placeholder="留空默认 42"
              className="w-28"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="task-ref">参考图（可选）</Label>
            <Input
              id="task-ref"
              type="file"
              accept="image/*"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="max-w-56 text-xs"
            />
          </div>
          <Button onClick={() => void handleSubmit()} disabled={submitting} className="ml-auto">
            {submitting ? (
              <>
                <Loader2 className="animate-spin" />
                提交中…
              </>
            ) : (
              <>
                <Send />
                提交任务
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
