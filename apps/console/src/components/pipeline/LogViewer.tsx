// src/components/pipeline/LogViewer.tsx — SSE 日志台
// 能力：自动跟随（用户上翻自动暂停）· 暂停时新日志角标计数 · 文本关键字过滤（LogLine 无 level 契约）
// 动效：仅新行 fadeIn 淡入（quick，reduced-motion 归零）；过滤态不播入场；role=log 供 AT 增量播报
import { memo, useEffect, useRef, useState } from "react";
import { motion } from "motion/react";
import { ArrowDown, Search, Sparkles, Trash2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { fadeIn, useMotionCfg } from "@/components/motion/tokens";
import { cn } from "@/lib/utils";
import type { LogLine } from "@/lib/validators";

const Line = memo(function Line({ line }: { line: LogLine }) {
  return (
    <div className="whitespace-pre-wrap text-foreground">
      <span className="mr-2 text-muted-foreground">{new Date(line.ts).toLocaleTimeString()}</span>
      {line.text}
    </div>
  );
});

export function LogViewer({
  logs,
  onClear,
  onAskAi,
}: {
  logs: LogLine[];
  onClear: () => void;
  onAskAi: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const prevLen = useRef(logs.length);
  const [follow, setFollow] = useState(true);
  const [newCount, setNewCount] = useState(0);
  const [keyword, setKeyword] = useState("");
  const motionCfg = useMotionCfg();

  const kw = keyword.trim();
  const visible = kw ? logs.filter((l) => l.text.includes(kw)) : logs;

  const scrollToBottom = (smooth: boolean) => {
    const el = ref.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: smooth ? "smooth" : "auto" });
  };

  // 新日志到达：跟随态即时吸底；暂停态累计角标（清屏/重置归零）
  useEffect(() => {
    const delta = logs.length - prevLen.current;
    prevLen.current = logs.length;
    if (delta <= 0) {
      setNewCount(0);
      return;
    }
    if (follow) requestAnimationFrame(() => scrollToBottom(false));
    else setNewCount((n) => n + delta);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [logs.length, follow]);

  const handleScroll = () => {
    const el = ref.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 48;
    setFollow(atBottom);
  };

  const jumpToLatest = () => {
    setFollow(true);
    setNewCount(0);
    scrollToBottom(true);
  };

  return (
    <Card>
      <CardContent className="flex flex-wrap items-center justify-between gap-2 pt-5 pb-3">
        <CardDescription>
          实时输出（回填最近 300 行 · 心跳保活）· 共 <span className="mono">{logs.length}</span> 行
          {kw ? (
            <>
              {" "}
              · 匹配 <span className="mono text-primary">{visible.length}</span> 行
            </>
          ) : null}
        </CardDescription>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="pointer-events-none absolute top-1/2 left-2 size-3.5 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              placeholder="过滤日志文本…"
              aria-label="过滤日志文本"
              className="h-8 w-52 pl-7 text-xs"
            />
            {kw ? (
              <button
                type="button"
                onClick={() => setKeyword("")}
                aria-label="清除过滤"
                className="absolute top-1/2 right-2 -translate-y-1/2 text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                <X className="size-3.5" />
              </button>
            ) : null}
          </div>
          <Button variant="ghost" size="sm" onClick={onAskAi} aria-label="携带日志末 20 行向 AI 提问排障">
            <Sparkles />
            问 AI 排障
          </Button>
          <Button variant="ghost" size="sm" onClick={onClear}>
            <Trash2 />
            清屏
          </Button>
        </div>
      </CardContent>
      <CardContent className="pt-0">
        <div className="relative">
          <ScrollArea
            ref={ref}
            onScroll={handleScroll}
            role="log"
            aria-label="流水线实时日志"
            className="mono h-[28rem] rounded-md border border-border bg-background p-3 text-xs leading-5"
          >
            {logs.length === 0 ? (
              <span className="text-muted-foreground">暂无输出 —— 触发流水线或等待运行事件…</span>
            ) : visible.length === 0 ? (
              <span className="text-muted-foreground">无匹配「{kw}」的日志行</span>
            ) : (
              visible.map((l, i) =>
                !kw && follow && i === visible.length - 1 ? (
                  <motion.div
                    key={`${l.ts}-${i}`}
                    variants={fadeIn}
                    initial="hidden"
                    animate="visible"
                    transition={motionCfg.enter("quick")}
                  >
                    <Line line={l} />
                  </motion.div>
                ) : (
                  <Line key={`${l.ts}-${i}`} line={l} />
                )
              )
            )}
          </ScrollArea>

          {/* 暂停跟随期间的新日志角标 */}
          {!follow && newCount > 0 ? (
            <Button
              variant="outline"
              size="sm"
              onClick={jumpToLatest}
              className={cn("absolute bottom-3 left-1/2 -translate-x-1/2 border-primary/40 bg-card/95 text-primary backdrop-blur hover:bg-primary/10 hover:text-primary")}
              aria-label={`回到底部，读取 ${newCount} 条新日志`}
            >
              <ArrowDown />
              {newCount} 条新日志
            </Button>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}
