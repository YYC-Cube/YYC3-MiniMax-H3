// src/components/dashboard/BatchesTable.tsx — 批次明细表
import { Link } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { batchRows, type BatchRow } from "@/lib/dashboard-selectors";
import type { Manifest } from "@yyc3/manifest-schema";

const TONE: Record<BatchRow["badge"]["tone"], { label: string; variant: "success" | "warning" | "destructive" | "running" }> = {
  done: { label: "完成", variant: "success" },
  partial: { label: "部分完成", variant: "warning" },
  failed: { label: "失败", variant: "destructive" },
  running: { label: "运行中", variant: "running" },
};

export function BatchesTable({ manifests }: { manifests: Manifest[] }) {
  const rows = batchRows(manifests);

  return (
    <Card>
      <CardContent className="pt-5">
        <Table>
          <TableHeader>
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
          <TableBody>
            {rows.map((r) => {
              const tone = TONE[r.badge.tone];
              return (
                <TableRow key={r.batch}>
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
            {rows.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="py-6 text-center text-muted-foreground">
                  未发现 output_batch*/manifest.json — 先运行 pipeline_auto.py
                </TableCell>
              </TableRow>
            ) : null}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
