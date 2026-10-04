// src/components/dashboard/StatCard.tsx — KPI 卡（Motion 数值淡入）
import { motion } from "motion/react";
import { Card, CardContent } from "@/components/ui/card";

export interface StatCardProps {
  label: string;
  value: string;
  hint?: string;
  icon?: React.ReactNode;
}

export function StatCard({ label, value, hint, icon }: StatCardProps) {
  return (
    <Card>
      <CardContent className="pt-5">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>{label}</span>
          {icon}
        </div>
        <motion.div
          key={value}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25 }}
          className="mono mt-1 text-2xl font-bold text-primary"
        >
          {value}
        </motion.div>
        {hint ? <div className="mt-1 text-xs text-muted-foreground">{hint}</div> : null}
      </CardContent>
    </Card>
  );
}
