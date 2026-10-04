// src/components/pipeline/LogViewer.tsx — SSE 日志台（自动滚底 + 末行 Motion 淡入 + memo 行）
import { memo, useEffect, useRef } from "react";
import { motion } from "motion/react";
import { Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { LogLine } from "@/lib/validators";

const Line = memo(function Line({ line }: { line: LogLine }) {
  return (
    <div className="whitespace-pre-wrap text-foreground">
      <span className="mr-2 text-muted-foreground">{new Date(line.ts).toLocaleTimeString()}</span>
      {line.text}
    </div>
  );
});

export function LogViewer({ logs, onClear }: { logs: LogLine[]; onClear: () => void }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    ref.current?.scrollTo({ top: ref.current.scrollHeight });
  }, [logs.length]);

  return (
    <Card>
      <CardContent className="flex flex-row items-center justify-between pt-5 pb-3">
        <CardDescription>实时输出（回填最近 300 行 · 心跳保活）</CardDescription>
        <Button variant="ghost" size="sm" onClick={onClear}>
          <Trash2 />
          清屏
        </Button>
      </CardContent>
      <CardContent className="pt-0">
        <ScrollArea
          ref={ref}
          aria-label="流水线实时日志"
          className="mono h-[28rem] rounded-md border border-border bg-background p-3 text-xs leading-5"
        >
          {logs.length === 0 ? (
            <span className="text-muted-foreground">暂无输出 —— 触发流水线或等待运行事件…</span>
          ) : (
            logs.map((l, i) =>
              i === logs.length - 1 ? (
                <motion.div
                  key={i}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.2 }}
                >
                  <Line line={l} />
                </motion.div>
              ) : (
                <Line key={i} line={l} />
              )
            )
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
