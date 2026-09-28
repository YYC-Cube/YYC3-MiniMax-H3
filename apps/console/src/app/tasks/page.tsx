"use client";

import { useCallback, useEffect, useState } from "react";

interface TaskView {
  id: string;
  status: "queued" | "running" | "succeeded" | "failed";
  quality: string | null;
  created_at: number | null;
  updated_at: number | null;
  attempts: number;
  error: string | null;
  result_url?: string;
  archive_path?: string | null;
  duration_seconds?: number | null;
}

const STATUS_STYLE: Record<TaskView["status"], string> = {
  queued: "text-(--muted) border-(--border)",
  running: "text-yellow-400 border-yellow-400/40",
  succeeded: "text-emerald-400 border-emerald-400/40",
  failed: "text-red-400 border-red-400/40",
};

const STATUS_TEXT: Record<TaskView["status"], string> = {
  queued: "排队中",
  running: "生成中",
  succeeded: "已完成",
  failed: "失败",
};

function fmtTime(ts: number | null): string {
  return ts ? new Date(ts * 1000).toLocaleString("zh-CN", { hour12: false }) : "-";
}

export default function TasksPage() {
  const [tasks, setTasks] = useState<TaskView[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [prompt, setPrompt] = useState("");
  const [quality, setQuality] = useState<"preview" | "full">("preview");
  const [seed, setSeed] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await fetch("/api/tasks", { cache: "no-store" });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.error ?? `HTTP ${res.status}`);
      setTasks(data?.tasks ?? []);
      setLoadError(null);
    } catch (e) {
      setLoadError(String(e));
    } finally {
      setLoaded(true);
    }
  }, []);

  // 10s 轮询（夜间 runner 领取后 queued→running→succeeded 自动上屏）
  useEffect(() => {
    load();
    const t = setInterval(load, 10_000);
    return () => clearInterval(t);
  }, [load]);

  const submit = useCallback(async () => {
    setSubmitting(true);
    setNotice(null);
    try {
      let refImageB64: string | undefined;
      if (file) {
        refImageB64 = await new Promise<string>((resolve, reject) => {
          const r = new FileReader();
          r.onload = () => resolve(String(r.result).split(",")[1] ?? "");
          r.onerror = () => reject(new Error("参考图读取失败"));
          r.readAsDataURL(file);
        });
      }
      const res = await fetch("/api/tasks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: prompt || undefined,
          quality,
          seed: seed ? Number(seed) : undefined,
          refImageB64,
          refImageName: file?.name,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data?.error ?? `HTTP ${res.status}`);
      setNotice(`✅ 已创建任务 ${data.id}（队列位置 #${data.queue_position}），夜间窗口由 Mac runner 领取生成`);
      setPrompt("");
      setSeed("");
      setFile(null);
      load();
    } catch (e) {
      setNotice(`❌ ${e}`);
    } finally {
      setSubmitting(false);
    }
  }, [prompt, quality, seed, file, load]);

  const running = tasks.filter((t) => t.status === "running").length;
  const queued = tasks.filter((t) => t.status === "queued").length;

  return (
    <div className="max-w-4xl mx-auto flex flex-col gap-6">
      <div className="flex items-baseline gap-3">
        <h1 className="text-xl font-bold">任务中心</h1>
        <span className="text-sm text-(--muted)">
          网关队列直连 · 排队 {queued} / 生成中 {running}
        </span>
        <span className="text-xs text-(--muted) ml-auto">10s 自动刷新</span>
      </div>

      {/* 提交表单 */}
      <section className="border border-(--border) rounded-lg p-4 flex flex-col gap-3">
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="生成提示词（留空 = runner 默认数字人模板；≤4000 字符）"
          rows={3}
          className="w-full bg-transparent border border-(--border) rounded p-2 text-sm"
        />
        <div className="flex flex-wrap items-center gap-3 text-sm">
          <label className="flex items-center gap-2">
            档位
            <select
              value={quality}
              onChange={(e) => setQuality(e.target.value as "preview" | "full")}
              className="bg-transparent border border-(--border) rounded px-2 py-1"
            >
              <option value="preview">preview 快预览（夜间后白天迭代）</option>
              <option value="full">full 全质量（约 4h/seed）</option>
            </select>
          </label>
          <label className="flex items-center gap-2">
            Seed
            <input
              value={seed}
              onChange={(e) => setSeed(e.target.value.replace(/\D/g, ""))}
              placeholder="留空默认 42"
              className="w-28 bg-transparent border border-(--border) rounded px-2 py-1"
            />
          </label>
          <label className="flex items-center gap-2">
            参考图
            <input
              type="file"
              accept="image/*"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="text-xs"
            />
          </label>
          <button
            onClick={submit}
            disabled={submitting}
            className="ml-auto px-4 py-1.5 rounded border border-(--border) hover:opacity-80 disabled:opacity-40"
          >
            {submitting ? "提交中…" : "提交任务"}
          </button>
        </div>
        {notice && <p className="text-sm text-(--muted)">{notice}</p>}
      </section>

      {/* 任务列表 */}
      <section className="flex flex-col gap-2">
        {loadError && (
          <p className="text-sm text-red-400">
            网关队列不可达：{loadError}
            （本地需 H3_GATEWAY_URL/H3_GATEWAY_API_KEY；Pages 静态版无 API 层）
          </p>
        )}
        {loaded && !loadError && tasks.length === 0 && (
          <p className="text-sm text-(--muted)">队列为空 — 提交第一个任务吧</p>
        )}
        {tasks.map((t) => (
          <div key={t.id} className="border border-(--border) rounded-lg p-3 text-sm">
            <div className="flex flex-wrap items-center gap-3">
              <span className={`px-2 py-0.5 rounded border text-xs ${STATUS_STYLE[t.status]}`}>
                {STATUS_TEXT[t.status]}
              </span>
              <code className="text-xs">{t.id}</code>
              <span className="text-xs text-(--muted)">{t.quality}</span>
              <span className="text-xs text-(--muted)">创建 {fmtTime(t.created_at)}</span>
              {t.attempts > 0 && (
                <span className="text-xs text-yellow-400">重试 ×{t.attempts}</span>
              )}
              {t.status === "succeeded" && (
                <button
                  onClick={() => setExpanded(expanded === t.id ? null : t.id)}
                  className="ml-auto text-xs underline"
                >
                  {expanded === t.id ? "收起" : "预览/下载"}
                </button>
              )}
            </div>
            {t.error && <p className="mt-2 text-xs text-red-400">{t.error}</p>}
            {t.status === "succeeded" && expanded === t.id && (
              <div className="mt-3 flex flex-col gap-2">
                {/* eslint-disable-next-line jsx-a11y/media-has-caption -- 生成短视频无字幕轨道 */}
                <video src={`/api/tasks/${t.id}/result`} controls preload="none" className="w-72 rounded" />
                <a
                  href={`/api/tasks/${t.id}/result`}
                  download={`yyc3_video_${t.id}.mp4`}
                  className="text-xs underline"
                >
                  下载 mp4{t.duration_seconds ? `（生成耗时 ${Math.round(t.duration_seconds / 60)}min）` : ""}
                </a>
                {t.archive_path && (
                  <span className="text-xs text-(--muted)">NAS 持久副本：{t.archive_path}</span>
                )}
              </div>
            )}
          </div>
        ))}
      </section>
    </div>
  );
}
