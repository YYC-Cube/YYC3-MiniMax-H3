// src/components/dashboard/BatchesTable.tsx — 批次明细表（虚拟化：批量扩容不拖渲染）
import { useRef } from "react";
import { Link } from "react-router-dom";
import { useVirtualizer } from "@tanstack/react-virtual";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { batchRows, type BatchRow } from "@/lib/dashboard-selectors";
import type { Manifest } from "@yyc3/manifest-schema";

const TONE: Record<BatchRow["badge"]["tone"], { label: string; variant: "success" | "warning" | "destructive" | "running" }> = {
  done: { label: "完成", variant: "success" },
  partial: { label: "部分完成", variant: "warning" },
  failed: { label: "失败", variant: "destructive" },
  running: { label: "运行中", variant: "running" },
};

// 行高估算（py-2 + 1px 边框 ≈ 44px）；overscan 提前渲染平滑滚动
const ROW_ESTIMATE = 44;
const ROW_OVERSCAN = 8;
const SCROLL_MAX_H = "max-h-[32rem]";

export function BatchesTable({ manifests }: { manifests: Manifest[] }) {
  const rows = batchRows(manifests);
  const scrollRef = useRef<HTMLDivElement>(null);

  // 行数少时虚拟化零成本（估算高度 + overscan 即可）；行数多时窗口化滚动
  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => ROW_ESTIMATE,
    overscan: ROW_OVERSCAN,
  });
  const items = virtualizer.getVirtualItems();

  return (
    <Card>
      <CardContent className="pt-5">
        {/* 单一滚动容器（垂直窗口化 + sticky 表头）：表头吸顶需与滚动容器同层，绕开内层 overflow-x 包装 */}
        <div ref={scrollRef} className={`relative overflow-auto ${SCROLL_MAX_H}`}>
          <table className="w-full table-fixed caption-bottom border-separate border-spacing-0 text-sm">
            {/* table-layout:fixed + border-separate：虚拟化行绝对定位时列对齐 + sticky 表头生效（preflight collapse 会破坏二者） */}
            <colgroup>
              <col className="w-[11%]" />
              <col className="w-[15%]" />
              <col className="w-[24%]" />
              <col className="w-[13%]" />
              <col className="w-[9%]" />
              <col className="w-[12%]" />
              <col className="w-[16%]" />
            </colgroup>
            <TableHeader className="sticky top-0 z-10 bg-card">
              <TableRow>
                <TableHead>批次</TableHead>
                <TableHead>模型</TableHead>
                <TableHead>开始时间</TableHead>
                <TableHead>成功/失败/跳过</TableHead>
                <TableHead>均分</TableHead>
                <TableHead>耗时(min)</TableHead>
                <TableHead>状态</TableHead>
              </TableRow>
            </TableHeader>
            {rows.length === 0 ? (
              <TableBody>
                <TableRow>
                  <TableCell colSpan={7} className="py-6 text-center text-muted-foreground">
                    未发现 output_batch*/manifest.json — 先运行 pipeline_auto.py
                  </TableCell>
                </TableRow>
              </TableBody>
            ) : (
              // 窗口化用「流内 spacer 行」而非绝对定位：<tr> 绝对定位会退化为 block，
              // 破坏与表头的列网格对齐——spacer 保持真实表布局（对齐 + sticky + 语义全保留）
              <TableBody aria-live="polite">
                {items.length > 0 && items[0].start > 0 ? (
                  <TableRow aria-hidden="true" style={{ height: items[0].start }} />
                ) : null}
                {items.map((vi) => {
                  const r = rows[vi.index];
                  const tone = TONE[r.badge.tone];
                  return (
                    <TableRow key={r.batch} data-index={vi.index} ref={virtualizer.measureElement}>
                      <TableCell>
                        <Link
                          to={`/batches/batch${r.batch}`}
                          className="mono font-bold text-primary hover:underline"
                        >
                          batch{r.batch}
                        </Link>
                      </TableCell>
                      <TableCell className="mono">{r.model}</TableCell>
                      <TableCell className="mono text-muted-foreground">{r.startedAt}</TableCell>
                      <TableCell className="mono">
                        {r.success}/{r.failed}/{r.skipped}
                      </TableCell>
                      <TableCell className="mono">{r.avg}</TableCell>
                      <TableCell className="mono">{r.dur}</TableCell>
                      <TableCell>
                        <Badge variant={tone.variant} title={r.badge.title}>
                          {tone.label}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  );
                })}
                {items.length > 0 && items.length < rows.length ? (
                  <TableRow
                    aria-hidden="true"
                    style={{
                      height: virtualizer.getTotalSize() - (items[items.length - 1]?.end ?? items[0].end),
                    }}
                  />
                ) : null}
              </TableBody>
            )}
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
