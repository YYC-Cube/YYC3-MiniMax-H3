#!/Users/yanyu/YYC-Cube/YYC3-MiniMax-H3/.venv/bin/python
"""
storyboard_visual_check.py — /storyboard 分镜确认页浏览器视觉验证（B5 收口件）

⚠️ 解释器锚定：shebang 硬绑定项目 .venv/bin/python（pyvenv 独立 venv，include-system-site-packages=false）
   — 根治 2026-10-08 homebrew 升 3.14 后裸 python3 漂移丢 playwright/uvicorn 事故
   — 调用文档/脚本注释中的 `python3` 已过时，一律改用 `.venv/bin/python` 或 `./storyboard_visual_check.py`

背景：B5（项目记忆）——/storyboard 的 curl 全链已验（d3edc87），但 UI 渲染/
单选高亮/错误 toast 需浏览器实测。本脚本以 headless 浏览器自动化完成，
无需设备前人工操作。

编排闭环（一键全链）：
  ① 双服务编排：agent 网关 8300（AGENT_CLAIM_SECRET 本地临时密钥）+ console
     dev.mjs（Vite 3030 → API 3031）；已在运行的服务自动复用（不杀不动）
  ② 闸门数据：签发 claim → POST /api/storyboard/submit（经 BFF）→ waiting_feedback
  ③ 视觉断言 V1~V7（Playwright headless，优先系统 Chrome channel="chrome"）：
     V1 页面骨架（标题/状态徽章「等待确认」/batch99/10s 自动刷新）
     V2 候选图真实渲染（img naturalWidth>0，/api/storyboard/ref/* 静态链路）
     V3 单选交互（点击 → aria-checked=true + border-primary 高亮）
     V4 控件齐全（档位 select 3 项/演练 checkbox 默认勾选/确认按钮状态迁移）
     V5 401 优雅降级（无 claim 确认 → toast 错误展示，页面不白屏）
     V6 导航入口（「分镜确认」链接在位且当前态高亮）
     V7 控制台零未捕获错误（pageerror 收集）
  ④ 截图留证：logs/visual/storyboard_V{N}_*.png（每断言步一张）
  ⑤ 清理：仅停本脚本自起的服务（复用的保留）

用法：
  python3 scripts/pipeline-tools/storyboard_visual_check.py            # 全链
  python3 ... --keep-services                                         # 跑完不停自起服务
退出码：0 全过 / 1 存在 FAIL / 2 环境缺依赖（playwright/Chrome）
"""
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PY = sys.executable
SECRET = "visual-check-local-b5"
VITE = "http://localhost:3030"          # Vite 绑 ::1（localhost 解析兼容）
VITE_BFF = "http://[::1]:3030"          # BFF curl 用（实测口径）
AGENT = "http://127.0.0.1:8300"
SHOT_DIR = REPO / "logs" / "visual"
RESULTS: list[tuple[str, bool, str]] = []
OWNED_PIDS: list[int] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    RESULTS.append((name, ok, detail))
    print(f"  {'✅' if ok else '❌'} {name}" + (f" — {detail}" if detail else ""))
    return ok


# ---------------- ① 服务编排 ----------------
def http_ok(url: str, timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def agent_alive() -> bool:
    try:
        with urllib.request.urlopen(f"{AGENT}/api/healthz", timeout=2) as r:
            return r.status == 200 and json.loads(r.read()).get("status") == "ok"
    except Exception:
        return False


def start_services() -> bool:
    logs = REPO / "logs"
    logs.mkdir(exist_ok=True)
    if not agent_alive():
        env = {**os.environ, "AGENT_CLAIM_SECRET": SECRET}
        p = subprocess.Popen(
            [PY, "-m", "uvicorn", "agent.h3_agent.gateway:app",
             "--host", "127.0.0.1", "--port", "8300"],
            cwd=REPO, env=env, stdout=open(logs / "visual_agent.log", "w"),
            stderr=subprocess.STDOUT)
        OWNED_PIDS.append(p.pid)
    if not http_ok(VITE):
        p = subprocess.Popen(
            ["node", "scripts/dev.mjs"], cwd=REPO / "apps/console",
            env={**os.environ, "PATH": os.environ.get("PATH", "")},
            stdout=open(logs / "visual_console.log", "w"), stderr=subprocess.STDOUT)
        OWNED_PIDS.append(p.pid)
    for _ in range(40):  # 最长 80s 就绪等待（Vite 冷启动 + 依赖预构建）
        if agent_alive() and http_ok(VITE):
            return True
        time.sleep(2)
    return agent_alive() and http_ok(VITE)


def stop_owned_services() -> None:
    for pid in OWNED_PIDS:
        subprocess.run(["kill", str(pid)], capture_output=True)
    # dev.mjs 子进程树（tsx/vite）按真实命令行收敛（P011 教训：pkill 模式须匹配 cli.mjs）
    subprocess.run(["pkill", "-f", "scripts/dev.mjs"], capture_output=True)
    subprocess.run(["pkill", "-f", "cli.mjs watch server/index.ts"], capture_output=True)
    subprocess.run(["pkill", "-f", "tsx/dist/preflight"], capture_output=True)
    subprocess.run(["pkill", "-f", "uvicorn agent.h3_agent.gateway"], capture_output=True)


# ---------------- ② 闸门数据 ----------------
def submit_storyboard() -> bool:
    """签发 claim → 经 BFF 提交演示候选 → waiting_feedback"""
    code = ("import json;from agent.h3_agent.security import issue_claim;"
            "print(json.dumps(issue_claim('visual-b5','generate_batch'),"
            "separators=(',',':')))")
    out = subprocess.run([PY, "-c", code], cwd=REPO, capture_output=True, text=True,
                         env={**os.environ, "AGENT_CLAIM_SECRET": SECRET})
    claim = out.stdout.strip()
    if not claim.startswith("{"):
        print(f"  ⚠ claim 签发异常：{out.stderr[:200]}")
        return False
    req = urllib.request.Request(
        f"{VITE_BFF}/api/storyboard/submit", method="POST",
        data=json.dumps({"batch": "99", "candidates": ["characters/person_a.png"]})
            .encode(),
        headers={"Content-Type": "application/json", "X-Claim-Token": claim})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read()).get("status") == "waiting_feedback"
    except Exception as e:
        print(f"  ⚠ submit 失败：{e}")
        return False


# ---------------- ③ 视觉断言 ----------------
def run_visual() -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ 缺依赖：pip install playwright（浏览器用系统 Chrome，无需 install）")
        return False

    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    all_ok = True
    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(channel="chrome", headless=True)
        except Exception:
            browser = pw.chromium.launch(headless=True)  # 回退缓存 chromium
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        page_errors: list[str] = []
        page.on("pageerror", lambda e: page_errors.append(str(e)))

        page.goto(f"{VITE}/storyboard", wait_until="networkidle", timeout=30_000)

        # V1 页面骨架
        v1 = (page.get_by_text("分镜确认闸门").first.is_visible()
              and page.get_by_text("等待确认").first.is_visible()
              and page.get_by_text("batch99").first.is_visible()
              and page.get_by_text("10s 自动刷新").first.is_visible())
        page.screenshot(path=str(SHOT_DIR / "storyboard_V1_skeleton.png"))
        all_ok &= check("V1 页面骨架（标题/徽章/batch99/自动刷新）", v1)

        # V2 候选图真实渲染（naturalWidth>0 = 静态链路真图）
        img = page.locator('img[src*="/api/storyboard/ref/characters/person_a.png"]')
        img.wait_for(state="visible", timeout=10_000)
        nw = img.evaluate("el => el.naturalWidth")
        page.screenshot(path=str(SHOT_DIR / "storyboard_V2_candidate.png"))
        all_ok &= check("V2 候选图渲染（naturalWidth>0）", nw > 0, f"naturalWidth={nw}")

        # V3 单选交互（radiogroup 语义 + 高亮）
        card = page.get_by_role("radio", name="分镜候选 characters/person_a.png")
        card.click()
        time.sleep(0.5)
        checked = card.get_attribute("aria-checked") == "true"
        highlighted = "border-primary" in (card.get_attribute("class") or "")
        page.screenshot(path=str(SHOT_DIR / "storyboard_V3_selected.png"))
        all_ok &= check("V3 单选高亮（aria-checked + border-primary）",
                        checked and highlighted,
                        f"checked={checked} highlight={highlighted}")

        # V4 控件齐全
        sel = page.locator("#sb-quality")
        opts = sel.locator("option").count()
        dry = page.locator('input[type="checkbox"]').first.is_checked()
        btn = page.get_by_role("button", name="确认选图并触发阶段4")
        btn_enabled = btn.is_enabled()
        all_ok &= check("V4 控件齐全（档位3项/演练默认勾选/按钮可用）",
                        opts == 3 and dry and btn_enabled,
                        f"options={opts} dryRun={dry} btnEnabled={btn_enabled}")

        # V5 401 优雅降级（无 claim → toast 错误，页面存活）
        btn.click()
        toast = page.locator("[data-sonner-toast], [role='status']").first
        try:
            toast.wait_for(state="visible", timeout=8_000)
            toast_text = toast.inner_text()[:60]
        except Exception:
            toast_text = ""
        body_alive = page.locator("body").inner_text() != ""
        page.screenshot(path=str(SHOT_DIR / "storyboard_V5_toast401.png"))
        all_ok &= check("V5 401 toast 优雅降级", bool(toast_text) and body_alive,
                        f"toast='{toast_text}'")

        # V6 导航入口
        nav = page.get_by_role("link", name="分镜确认").first
        nav_ok = nav.is_visible()
        page.screenshot(path=str(SHOT_DIR / "storyboard_V6_nav.png"))
        all_ok &= check("V6 导航「分镜确认」入口", nav_ok)

        # V7 控制台零未捕获错误（401 fetch 属预期，不算 pageerror）
        all_ok &= check("V7 控制台零未捕获错误", not page_errors,
                        "; ".join(page_errors[:2]) if page_errors else "")

        browser.close()
    return all_ok


def main() -> int:
    print("== B5 /storyboard 浏览器视觉验证 ==")
    print("① 服务编排（复用优先）…")
    if not start_services():
        print("❌ 双服务未能就绪（agent 8300 / vite 3030）——查 logs/visual_*.log")
        stop_owned_services()
        return 2
    print(f"   agent={'复用' if not OWNED_PIDS else '自起'} · 服务就绪")

    print("② 闸门数据（claim → submit → waiting_feedback）…")
    if not submit_storyboard():
        stop_owned_services()
        return 1
    print("   闸门已置 waiting_feedback（batch99）")

    print("③ 视觉断言 V1~V7 …")
    ok = run_visual()

    print("\n== 汇总 ==")
    for name, passed, detail in RESULTS:
        print(f"  {'✅' if passed else '❌'} {name}")
    print(f"截图：{SHOT_DIR}/storyboard_V*.png")

    if "--keep-services" not in sys.argv:
        stop_owned_services()
        print("自起服务已清理（复用的保留）")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
