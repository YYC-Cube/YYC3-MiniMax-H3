// src/components/pipeline/ConnectionBanner.tsx — SSE 连接状态横幅（L1 呈现智能）
// 断连：warning 横幅常驻提示「3s 自动重连」+ 最后更新时间；重连成功：success 提示 3s 自收起
// 动效：AnimatePresence + slideDown（D2 退场/D9 数据事件）；aria-live=polite 不打断
import { slideDown, useMotionCfg } from "@/components/motion/tokens";
import { CheckCircle2, WifiOff } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useRef, useState } from "react";

type BannerState = "connecting" | "offline" | "recovered" | null;

export function ConnectionBanner({
  connected,
  lastUpdated,
}: {
  connected: boolean;
  /** 最后一条日志/状态的时间戳（ms）；无则 null */
  lastUpdated: number | null;
}) {
  const [banner, setBanner] = useState<BannerState>(connected ? null : "connecting");
  const everConnected = useRef(connected);
  const motionCfg = useMotionCfg();

  useEffect(() => {
    if (connected) {
      // 首次连通：不弹任何横幅；仅「断 → 通」才展示已恢复 3s 自收起
      if (!everConnected.current) {
        everConnected.current = true;
        setBanner(null);
        return;
      }
      setBanner("recovered");
      const t = setTimeout(() => setBanner(null), 3000);
      return () => clearTimeout(t);
    }
    // 初次未通=连接中；曾经通过=断连
    setBanner(everConnected.current ? "offline" : "connecting");
  }, [connected]);

  const lastText = lastUpdated ? new Date(lastUpdated).toLocaleTimeString() : null;

  return (
    <AnimatePresence>
      {banner ? (
        <motion.div
          variants={slideDown}
          initial="hidden"
          animate="visible"
          exit="hidden"
          transition={motionCfg.enter("overlay")}
          role="status"
          aria-live="polite"
          className={
            banner === "recovered"
              ? "flex items-center gap-2 rounded-md border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-400"
              : "flex items-center gap-2 rounded-md border border-yellow-500/40 bg-yellow-500/10 px-3 py-2 text-xs text-yellow-400"
          }
        >
          {banner === "recovered" ? <CheckCircle2 className="size-4" /> : <WifiOff className="size-4" />}
          {banner === "connecting" ? "正在建立实时日志通道…" : null}
          {banner === "offline" ? "实时连接断开，每 3s 自动重连…" : null}
          {banner === "recovered" ? "连接已恢复，实时日志继续" : null}
          {banner !== "recovered" && lastText ? <span className="text-yellow-400/70">最后更新 {lastText}</span> : null}
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
