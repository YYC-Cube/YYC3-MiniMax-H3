# ==============================================================
# H3 视听生成阶段编排引擎 v1.0（六阶段闭环 · 阶段4 落地段）
# @file agent/h3_agent/orchestrator.py
# @author Intelligent Application Implementation Expert <admin@0379.email>
# @version v1.0.0
# @created 2026-09-26
# @status stable
#
# 对齐：99-编排引擎/drama_stage_adapter.py
#   - StageStatus 五态枚举（pending/running/passed/rework/blocked）逐值兼容，
#     H3 作为漫剧 Stage.AUDIOVISUAL_GEN 的执行层，状态可被上游 DramaStageAdapter 消费
#   - 质量闭环：qc 打回 → 重生成（≤QC_MAX_REWORK 次）→ 仍败则 rework 停机
#   - 状态快照：projects/{project_id}/state/audiovisual_state.json（NAS 六环节落位）
# 差异：H3 侧为执行层编排（进程内直连三 Agent），非 LLM 九步闭环
# ==============================================================
import json
import time
from enum import Enum
from pathlib import Path

from . import config
from .agents.production_agent import H3ProductionAgent
from .agents.quality_agent import H3QualityAgent
from .protocol import get_transport
from .security import AuditLog, issue_claim


class StageStatus(str, Enum):
    """与漫剧 DramaStageAdapter.StageStatus 逐值兼容

    H3 侧扩展（docs/18 P1-1，2026-10-05）：WAITING_FEEDBACK 第六态——分镜确认闸门
    （MiraFrame Human-in-the-Loop 对位）。上游五态语义不变；未识别新值的消费端
    按 unknown 容错即可（漫剧 DramaStageAdapter 契约未动）。
    """
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    REWORK = "rework"
    BLOCKED = "blocked"
    WAITING_FEEDBACK = "waiting_feedback"


# 分镜闸门候选数约束（OnlyShot：每 grid 1-4 张候选关键帧）
STORYBOARD_CANDIDATES_MAX = 4


class H3StageOrchestrator:
    """阶段4 视听生成编排： shots[] → [质检→(打回重做)*] → 状态机 + 快照落盘

    transport 可注入（InMemory 离线演示/单测）；claim 密钥未配置时以
    require_claim=False 运行（本地演示），生产环境必须配置（网关强制签发）。
    """

    def __init__(self, project_id: str, transport=None, require_claim: bool = False):
        self.project_id = project_id
        self.mode = (transport and "injected") or get_transport()[1]
        self.production = H3ProductionAgent(transport=transport,
                                            enforce_claim=require_claim)
        self.quality = H3QualityAgent(transport=transport,
                                      enforce_claim=require_claim)
        self.require_claim = require_claim
        self.audit = AuditLog()
        self.stage_state = {
            "04_audiovisual_gen": {"status": StageStatus.PENDING.value,
                                   "qc_score": None, "attempts": 0,
                                   "updated_at": None}}
        # 分镜确认闸门（P1-1）：候选暂存（submit → waiting_feedback → confirm → 阶段4）
        self.storyboard: dict = {"batch": None, "candidates": [],
                                 "selected": None, "asset_ref": None}

    # ---------------- 状态机 ----------------
    def _update(self, status: StageStatus, qc_score: float | None = None):
        st = self.stage_state["04_audiovisual_gen"]
        st.update({"status": status.value,
                   "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                   "attempts": st["attempts"] + 1})
        if qc_score is not None:
            st["qc_score"] = qc_score
        print(f"[状态机] 04_audiovisual_gen → {status.value}"
              + (f"（qc={qc_score}）" if qc_score is not None else ""))

    # ---------------- 分镜确认闸门（P1-1，docs/18） ----------------
    def submit_storyboard(self, batch: str, candidates: list[str]) -> dict:
        """漫剧侧提交分镜候选 → 进入 waiting_feedback（人工闸门）

        :param batch: 批次号（白名单校验）
        :param candidates: 候选关键帧相对 ref_images/ 的路径（1-4 张，OnlyShot 规范）
        """
        from .security import valid_batch_name
        if not valid_batch_name(batch):
            raise ValueError(f"批次名违规：{batch!r}")
        if not candidates or len(candidates) > STORYBOARD_CANDIDATES_MAX:
            raise ValueError(f"候选须为 1-{STORYBOARD_CANDIDATES_MAX} 张，收到 {len(candidates or [])}")
        base = config.REPO_ROOT / "ref_images"
        for c in candidates:
            p = (base / c).resolve()
            if base.resolve() not in p.parents or not p.is_file():
                raise ValueError(f"候选不存在或越界：{c}")
        self.storyboard = {"batch": batch, "candidates": list(candidates),
                           "selected": None, "asset_ref": None}
        self._update(StageStatus.WAITING_FEEDBACK)
        self.audit.emit("storyboard_submit", project=self.project_id,
                        batch=batch, candidates=candidates)
        return {"batch": batch, "status": StageStatus.WAITING_FEEDBACK.value,
                "candidates": candidates}

    def storyboard_status(self) -> dict:
        """当前闸门状态（console 轮询/拉取）"""
        return {"batch": self.storyboard["batch"],
                "status": self.stage_state["04_audiovisual_gen"]["status"],
                "candidates": self.storyboard["candidates"],
                "selected": self.storyboard["selected"]}

    def confirm_storyboard(self, selected: str, asset_ref: str | None = None,
                           quality: str | None = None, dry_run: bool = False) -> dict:
        """人工选定候选 → 关联资产 → 触发阶段4（复用既有闭环）

        :param selected: 选定候选（须 ∈ 提交的候选集）
        :param asset_ref: 资产库关联路径（P0-2 清单对位，入快照供追溯）
        :param quality: 分级档位 preview/full（P2-2 pacing 驱动；None=引擎默认）
        """
        sb = self.storyboard
        if not sb["batch"]:
            raise ValueError("尚未提交分镜候选（先 submit_storyboard）")
        if self.stage_state["04_audiovisual_gen"]["status"] != StageStatus.WAITING_FEEDBACK.value:
            raise ValueError("闸门不在 waiting_feedback 态，无法确认")
        if selected not in sb["candidates"]:
            raise ValueError(f"选定项不在候选集：{selected!r}")
        sb["selected"] = selected
        sb["asset_ref"] = asset_ref or selected
        self.audit.emit("storyboard_confirm", project=self.project_id,
                        batch=sb["batch"], selected=selected,
                        asset_ref=sb["asset_ref"], quality=quality, dry_run=dry_run)
        # 确认后进入阶段4 既有闭环（RUNNING → 质检 → passed/rework）
        result = self.run_audiovisual_stage(batch=sb["batch"], dry_run=dry_run,
                                            quality=quality)
        result["storyboard"] = dict(sb)
        return result

    # ---------------- 阶段执行 ----------------
    def run_audiovisual_stage(self, batch: str, shots: list[dict] | None = None,
                              dry_run: bool = False,
                              quality: str | None = None) -> dict:
        """执行阶段4：批次生成 → 质检 → 打回重做闭环

        :param batch: 批次号（白名单校验）
        :param shots: 可选任务式单条列表 [{seeds, prompt_file?, variant?, preview?}]
        :param dry_run: 演练（pipeline_auto --dry-run）
        :param quality: 分级档位 preview/full（P2-2：pacing 驱动爆点 full / 常规 preview）
        """
        from .security import valid_batch_name
        if not valid_batch_name(batch):
            raise ValueError(f"批次名违规：{batch!r}")
        if quality is not None and quality not in ("preview", "full"):
            raise ValueError(f"quality 须为 preview/full，收到 {quality!r}")

        self._update(StageStatus.RUNNING)
        self.audit.emit("stage_start", project=self.project_id, batch=batch)

        # 1) 生成（批次闭环；可选追加任务式单条）
        gen = self._call(self.production, "generate_batch",
                         {"batch": batch, "dry_run": dry_run, "quality": quality})
        for shot in (shots or []):
            self._call(self.production, "generate_single",
                       {"batch": batch, **shot})

        # 2) 质检 + 打回重做闭环（≤ QC_MAX_REWORK）
        qc = self._call(self.quality, "quality_check", {"batch": batch})
        reworks = 0
        while (not qc["passed"] and reworks < config.QC_MAX_REWORK
               and qc["detail"]["failed"] > 0):
            reworks += 1
            print(f"[编排] 质检未过（qc={qc['qc_score']}），打回重做 {reworks}/{config.QC_MAX_REWORK}")
            self._call(self.production, "score_lipsync", {"batch": batch})
            gen = self._call(self.production, "generate_batch",
                             {"batch": batch, "dry_run": dry_run,
                              "quality": quality})  # 打回重做同样保留分级档位
            qc = self._call(self.quality, "quality_check", {"batch": batch})

        # 3) 面板数据桥刷新（静默，失败不阻断）
        try:
            self._call(self.production, "export_dashboard", {})
        except Exception as e:
            print(f"[编排] 面板刷新失败（不阻断）：{e}")

        # 4) 状态机落位
        verdict = ("blocked" if qc.get("verdict") == "blocked" else
                   "passed" if qc["passed"] else "rework")
        self._update(StageStatus(verdict), qc_score=qc["qc_score"])
        self.audit.emit("stage_end", project=self.project_id, batch=batch,
                        verdict=verdict, qc_score=qc["qc_score"], reworks=reworks)

        return {"project_id": self.project_id, "stage": "04_audiovisual_gen",
                "batch": batch, "verdict": verdict, "qc": qc,
                "reworks": reworks, "generate": gen,
                "state": self.stage_state["04_audiovisual_gen"]}

    # ---------------- 基础设施 ----------------
    def _call(self, agent, task_type: str, payload: dict) -> dict:
        """进程内直连调用（自动附 claim，若启用）"""
        if self.require_claim:
            payload = {**payload, "claim": issue_claim(
                f"orch-{int(time.time()*1000)}", task_type)}
        return agent.handle_direct(task_type, payload)

    def snapshot(self) -> dict:
        """项目状态快照 → projects/{project_id}/state/audiovisual_state.json"""
        snap = {"project_id": self.project_id,
                "stage": "04_audiovisual_gen",
                "state": self.stage_state["04_audiovisual_gen"],
                "transport": self.mode,
                "snapshot_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
        out = (config.REPO_ROOT / "projects" / self.project_id / "state")
        out.mkdir(parents=True, exist_ok=True)
        (out / "audiovisual_state.json").write_text(
            json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")
        return snap
