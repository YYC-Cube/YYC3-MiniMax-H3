// src/landing/App.tsx — 落地页/文档站（GitHub Pages 快照：曝光 + 预期管理 + 文档价值）
import { motion } from "motion/react";
import {
  ArrowRight,
  BarChart3,
  BookOpen,
  Bot,
  Boxes,
  CheckCircle2,
  FileVideo,
  Github,
  Layers,
  ListTodo,
  Radio,
  ShieldCheck,
  Workflow,
} from "lucide-react";

const FEATURES = [
  {
    icon: BarChart3,
    title: "仪表盘 KPI",
    desc: "manifest 单一事实源直读：批次聚合、加权均分、Top 缺陷、SVG 趋势图。",
  },
  {
    icon: Radio,
    title: "流水线 SSE 实时日志",
    desc: "spawn 白名单触发 + 回填 300 行 + 心跳保活 + 断线自动重连，逐行实时回传。",
  },
  {
    icon: ListTodo,
    title: "任务中心",
    desc: "0379-World 网关队列直连：提交/轮询/预览/下载，X-Claim-Token 鉴权闭环。",
  },
  {
    icon: FileVideo,
    title: "批次详情与人工精评",
    desc: "视频卡片网格 + 1~10 滑条评分 + 缺陷标签写回 report，驱动 Seed 迭代闭环。",
  },
  {
    icon: Bot,
    title: "AI 提示词助手",
    desc: "Vercel AI SDK 流式输出 H3 结构化提示词（描述/声景/配乐/参数建议）。",
  },
  {
    icon: ShieldCheck,
    title: "契约与安全",
    desc: "zod 双端单一真源 + CI 门禁；密钥仅服务端持有，写操作 fail-closed。",
  },
];

const STACK = [
  ["React 19", "函数式 + Hooks"],
  ["Vite 6", "SPA 构建"],
  ["TypeScript strict", "类型安全"],
  ["Tailwind CSS 4", "原子样式"],
  ["shadcn/ui", "组件基座"],
  ["Zustand", "slice 状态"],
  ["Lucide + Motion", "图标与动画"],
  ["Vercel AI SDK v7", "流式响应"],
];

const DOCS = [
  { href: "https://github.com/YYC-Cube/YYC3-MiniMax-H3/blob/main/README.md", label: "项目总览 README" },
  { href: "https://github.com/YYC-Cube/YYC3-MiniMax-H3/blob/main/docs/01-环境部署指南.md", label: "环境部署指南" },
  { href: "https://github.com/YYC-Cube/YYC3-MiniMax-H3/blob/main/docs/03-批量迭代流水线说明.md", label: "批量迭代流水线" },
  { href: "https://github.com/YYC-Cube/YYC3-MiniMax-H3/blob/main/docs/08-开发者文档.md", label: "开发者文档 / API 参考" },
  { href: "https://github.com/YYC-Cube/YYC3-MiniMax-H3/blob/main/docs/16-前端技术选型与可视化建议.md", label: "前端技术选型论证" },
  { href: "https://github.com/YYC-Cube/YYC3-MiniMax-H3/blob/main/CHANGELOG.md", label: "CHANGELOG" },
];

export default function LandingApp() {
  return (
    <div className="min-h-screen">
      {/* 顶栏 */}
      <header className="sticky top-0 z-40 border-b border-border bg-background/80 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-6xl items-center gap-4 px-6">
          <img src="/yyc3-icons/Web App/favicon-32.png" alt="YYC³" width={24} height={24} className="rounded" />
          <span className="text-sm font-bold text-primary">YYC³ MiniMax-H3</span>
          <nav aria-label="页面导航" className="ml-auto flex gap-5 text-sm text-muted-foreground">
            <a href="#features" className="hover:text-foreground">能力</a>
            <a href="#stack" className="hover:text-foreground">技术栈</a>
            <a href="#docs" className="hover:text-foreground">文档</a>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="mx-auto max-w-6xl px-6 pb-16 pt-20 text-center">
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
          <img
            src="/yyc3-icons/Web App/android-chrome-512.png"
            alt="YYC³ 品牌图标"
            width={96}
            height={96}
            className="mx-auto mb-6 rounded-2xl shadow-lg shadow-primary/10"
          />
          <h1 className="mx-auto max-w-3xl text-4xl font-bold leading-tight md:text-5xl">
            Apple M4 Max 本地
            <span className="text-primary"> AI 数字人生产线</span>
          </h1>
          <p className="mx-auto mt-4 max-w-2xl text-base text-muted-foreground">
            MiniMax-H3 视频/数字人生成 · 闭环流水线（生成 → 口型评分 → 人工精评 → Seed 写回）
            · 实时控制台与任务中心 · AI 提示词助手
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <a
              href="https://github.com/YYC-Cube/YYC3-MiniMax-H3"
              target="_blank"
              rel="noreferrer"
              className="inline-flex h-10 items-center gap-2 rounded-md bg-primary px-5 text-sm font-semibold text-primary-foreground shadow hover:bg-primary/90"
            >
              <Github className="size-4" />
              GitHub 仓库
            </a>
            <a
              href="#expectation"
              className="inline-flex h-10 items-center gap-2 rounded-md border border-border px-5 text-sm font-medium hover:bg-secondary/60"
            >
              工作台接入方式
              <ArrowRight className="size-4" />
            </a>
          </div>
        </motion.div>
      </section>

      {/* 能力 */}
      <section id="features" className="border-t border-border bg-card/40 py-16">
        <div className="mx-auto max-w-6xl px-6">
          <h2 className="mb-8 text-center text-2xl font-bold">工作台能力</h2>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {FEATURES.map((f) => (
              <div key={f.title} className="rounded-xl border border-border bg-card p-5">
                <f.icon className="mb-3 size-6 text-primary" />
                <h3 className="font-semibold">{f.title}</h3>
                <p className="mt-1 text-sm text-muted-foreground">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 技术栈 */}
      <section id="stack" className="mx-auto max-w-6xl px-6 py-16">
        <h2 className="mb-8 text-center text-2xl font-bold">技术栈</h2>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {STACK.map(([name, desc]) => (
            <div key={name} className="flex items-center gap-3 rounded-lg border border-border px-4 py-3">
              <CheckCircle2 className="size-4 shrink-0 text-primary" />
              <div>
                <div className="text-sm font-semibold">{name}</div>
                <div className="text-xs text-muted-foreground">{desc}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* 文档 */}
      <section id="docs" className="border-t border-border bg-card/40 py-16">
        <div className="mx-auto max-w-6xl px-6">
          <h2 className="mb-8 text-center text-2xl font-bold">文档体系</h2>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
            {DOCS.map((d) => (
              <a
                key={d.href}
                href={d.href}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-3 rounded-lg border border-border px-4 py-3 text-sm transition-colors hover:bg-secondary/60"
              >
                <BookOpen className="size-4 shrink-0 text-primary" />
                {d.label}
              </a>
            ))}
          </div>
        </div>
      </section>

      {/* 预期管理 */}
      <section id="expectation" className="mx-auto max-w-6xl px-6 py-16">
        <div className="rounded-xl border border-primary/30 bg-primary/5 p-8">
          <div className="flex items-center gap-3">
            <Layers className="size-6 text-primary" />
            <h2 className="text-xl font-bold">本页定位：落地页 / 文档站（静态快照）</h2>
          </div>
          <p className="mt-3 text-sm leading-6 text-muted-foreground">
            本页由 GitHub Pages 静态托管，用于对外曝光、预期管理与文档入口——不含交互式 API。
          </p>
          <ul className="mt-4 grid gap-2 text-sm md:grid-cols-2">
            <li className="flex items-center gap-2">
              <Workflow className="size-4 text-primary" />
              流水线触发 / SSE 实时日志：工作台（本地/私网 3030）
            </li>
            <li className="flex items-center gap-2">
              <ListTodo className="size-4 text-primary" />
              任务中心：需接入 0379-World 网关的部署环境
            </li>
            <li className="flex items-center gap-2">
              <Boxes className="size-4 text-primary" />
              数据快照：dashboard/data/batches.json（入库即随本页发布）
            </li>
            <li className="flex items-center gap-2">
              <Radio className="size-4 text-primary" />
              实时状态请访问部署侧控制台（Tailscale / LAN）
            </li>
          </ul>
          <div className="mt-6 rounded-lg border border-border bg-background p-4 font-mono text-xs leading-6">
            <div className="text-muted-foreground"># 本地启动工作台（开发）</div>
            <div>pnpm --filter console dev</div>
            <div className="text-muted-foreground"># 生产单端口（API + 静态资源）</div>
            <div>NODE_ENV=production pnpm --filter console start</div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border py-8 text-center text-xs text-muted-foreground">
        <div>YanYuCloudCube · Words Initiate Quadrants, Language Serves as Core for Future</div>
        <div className="mt-1">© 2025-2026 YanYuCloudCube™. All Rights Reserved.</div>
      </footer>
    </div>
  );
}
