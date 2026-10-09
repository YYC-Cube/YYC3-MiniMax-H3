// src/components/motion/tokens.ts — 全局动效令牌唯一真源（Master Prompt §3.2）
// 纪律：组件内禁止随手写时长/缓动/位移魔法数，一律引用本文件；
//       所有动效必须经 useMotionCfg() 消费——系统开启「减弱动态效果」时 duration 归零、位移清零。
import { useReducedMotion } from "motion/react";
import type { Transition, Variants } from "motion/react";

/** 时长（秒）——语义：micro=颜色反馈 / quick=小件进退场 / base=卡片 / page=路由页 / overlay=浮层 */
export const DURATION = {
  micro: 0.12,
  quick: 0.2,
  base: 0.25,
  page: 0.32,
  overlay: 0.28,
} as const;

/** 贝塞尔缓动——四元组显式类型，兼容 motion 的 BezierDefinition */
export const EASE: Record<"out" | "in", [number, number, number, number]> = {
  out: [0.22, 1, 0.36, 1],
  in: [0.4, 0, 1, 1],
};

/** layout/手势专用弹簧（仅这一组，禁止随手调） */
export const SPRING = { stiffness: 260, damping: 30, mass: 0.8 } as const;

/** 序列编排间隔——grid=卡片网格 / list=列表行（长列表 ≤12 行后停止追加 stagger） */
export const STAGGER = { grid: 0.05, list: 0.035 } as const;

/** 位移尺度（px）——微反馈 4 / 卡片 8 / 页面 12；禁止 >16 的漂移 */
export const MOVE = { micro: 4, card: 8, page: 12 } as const;

// ---- 共享 Variants（搭配 motion 组件的 initial/animate/exit 使用） ----

/** 标准进退场：y 位移 + opacity（卡片/区块） */
export const fadeUp: Variants = {
  hidden: { opacity: 0, y: MOVE.card },
  visible: { opacity: 1, y: 0, transition: { duration: DURATION.base, ease: EASE.out } },
  exit: { opacity: 0, y: MOVE.micro, transition: { duration: DURATION.quick, ease: EASE.in } },
};

/** 纯透明度进退场（日志新行、不希望引发布局位移处） */
export const fadeIn: Variants = {
  hidden: { opacity: 0, y: MOVE.micro },
  visible: { opacity: 1, y: 0, transition: { duration: DURATION.quick, ease: EASE.out } },
  exit: { opacity: 0, transition: { duration: DURATION.quick, ease: EASE.in } },
};

/** 父容器 stagger（子项复用 fadeUp/fadeIn；长列表截断见 Master Prompt §3.4） */
export const staggerParent: Variants = {
  hidden: {},
  visible: { transition: { staggerChildren: STAGGER.grid } },
};

/** 横幅类浮层：自顶部滑入（断连横幅等） */
export const slideDown: Variants = {
  hidden: { opacity: 0, y: MOVE.micro * -1 },
  visible: { opacity: 1, y: 0, transition: { duration: DURATION.overlay, ease: EASE.out } },
  exit: { opacity: 0, y: MOVE.micro * -1, transition: { duration: DURATION.micro, ease: EASE.in } },
};

// ---- reduced-motion 合规消费层 ----

export interface MotionCfg {
  /** 系统是否开启减弱动态效果（null 安全为 false） */
  reduced: boolean;
  /** 进场 transition（reduced 时归零） */
  enter: (kind?: keyof typeof DURATION) => Transition;
  /** 退场 transition（reduced 时归零） */
  exit: Transition;
  /** layout/手势弹簧（reduced 时归零） */
  spring: Transition;
  /** 允许的 y 位移（reduced 时恒 0） */
  y: (kind?: keyof typeof MOVE) => number;
}

/** 所有运动组件的统一入口：根据系统 prefers-reduced-motion 收敛时长与位移 */
export function useMotionCfg(): MotionCfg {
  const reduced = useReducedMotion() ?? false;
  return {
    reduced,
    enter: (kind = "base") =>
      reduced ? { duration: 0 } : { duration: DURATION[kind], ease: EASE.out },
    exit: reduced ? { duration: 0 } : { duration: DURATION.quick, ease: EASE.in },
    spring: reduced ? { duration: 0 } : { type: "spring", ...SPRING },
    y: (kind = "card") => (reduced ? 0 : MOVE[kind]),
  };
}

/** 仅需「是否允许做动效」布尔判断处使用（如无限循环动画的卸载） */
export function useMotionAllowed(): boolean {
  return !(useReducedMotion() ?? false);
}
