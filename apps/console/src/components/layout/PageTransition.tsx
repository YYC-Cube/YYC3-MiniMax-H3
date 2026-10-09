// src/components/layout/PageTransition.tsx — 页面切换动画（Motion；D1 入场 / D10 路由）
// 动效参数全部取自 motion/tokens：page 档 .32s + y12；reduced-motion 时归零
import { motion } from "motion/react";
import type { ReactNode } from "react";
import { useMotionCfg } from "@/components/motion/tokens";

export function PageTransition({ children }: { children: ReactNode }) {
  const motionCfg = useMotionCfg();
  return (
    <motion.div
      initial={{ opacity: 0, y: motionCfg.y("page") }}
      animate={{ opacity: 1, y: 0 }}
      transition={motionCfg.enter("page")}
    >
      {children}
    </motion.div>
  );
}
