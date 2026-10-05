# ==============================================================
# H3 多Agent 框架 · 离线冒烟测试 v1.0
# @file agent/tests/test_smoke.py
# @author Intelligent Application Implementation Expert <admin@0379.email>
# @version v1.0.0
# @created 2026-09-26
#
# 零外部依赖（无 Redis/无 GPU/无网络）：InMemory 传输 + dry-run 执行器
# 运行：python3 -m unittest discover -s agent/tests -v   （仓库根目录）
# ==============================================================
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]   # agent/tests/ → 仓库根
sys.path.insert(0, str(REPO_ROOT))

from agent.h3_agent import config                 # noqa: E402
from agent.h3_agent.orchestrator import H3StageOrchestrator, StageStatus  # noqa: E402
from agent.h3_agent.protocol import (AgentRegistry, InMemoryTransport,  # noqa: E402
                                     MessageConsumer, MessageProducer,
                                     build_message, parse_message)
from agent.h3_agent.security import (AuditLog, issue_claim,  # noqa: E402
                                     validate_task_payload, verify_claim)


REAL_ROOT = Path(config.REPO_ROOT)                # 导入时快照（测试中会临时覆盖）


def dry_executor(script_key, argv, timeout=None):
    """dry-run 执行器：不落盘不调用 GPU，仅回放结构化档案"""
    real = (REAL_ROOT / config.SCRIPT_ALLOWLIST[script_key])   # 白名单校验照常生效
    if not real.exists():
        raise FileNotFoundError(f"白名单脚本缺失：{real}")
    return {"script_key": script_key, "argv": argv,
            "returncode": 0, "stdout_tail": "(dry-run)", "stderr_tail": "",
            "duration_s": 0.0}


def fake_manifest(tmp: Path, batch: str) -> Path:
    """构造合规 manifest（3 成功 / 0 失败，sync_norm 0.81，人工分 8+）"""
    d = tmp / f"output_batch{batch}"
    d.mkdir(parents=True, exist_ok=True)
    records = [{"status": "SUCCESS", "human": {"score": 8 + i},
                "lipsync": {"score_norm": 0.81}} for i in range(3)]
    mf = d / "manifest.json"
    mf.write_text(
        __import__("json").dumps({"batch": batch, "records": records}),
        encoding="utf-8")
    return mf


class TestProtocol(unittest.TestCase):
    def test_message_roundtrip(self):
        msg = build_message("t1", "task_request", "orch", "h3-zhiying-001",
                            "generate_batch", {"batch": "93"})
        parsed = parse_message(dict(msg, payload=msg["payload"]))
        self.assertEqual(parsed["payload"]["batch"], "93")
        for k in ("msg_id", "trace_id", "msg_type", "sender", "receiver",
                  "task_type", "priority", "timestamp", "ttl"):
            self.assertIn(k, parsed)

    def test_inmemory_transport_e2e(self):
        t = InMemoryTransport()
        t.ensure_group("s1", "g1")
        msg = build_message("t2", "task_request", "a", "b", "quality_check", {})
        t.xadd("s1", msg)
        consumer = MessageConsumer("s1", "g1", "c1", t)
        got = consumer.poll(count=1, block_ms=10)
        self.assertEqual(len(got), 1)
        consumer.ack(got[0]["stream_msg_id"])
        self.assertEqual(consumer.poll(count=1, block_ms=10), [])

    def test_registry_capability_discovery(self):
        t = InMemoryTransport()
        AgentRegistry.register({"agent_id": "x-001", "agent_name": "X",
                                "role": "r", "capabilities": ["video_generation"],
                                "endpoint": "s", "status": "online"}, t)
        found = AgentRegistry.get_agent_by_capability("video_generation", t)
        self.assertEqual([a["agent_id"] for a in found], ["x-001"])


class TestSecurity(unittest.TestCase):
    def test_claim_roundtrip_and_tamper(self):
        secret = "unit-test-secret"
        claim = issue_claim("t3", "generate_batch", secret=secret, ttl=60)
        self.assertTrue(verify_claim(claim, secret=secret))
        self.assertFalse(verify_claim(dict(claim, signature="0" * 64), secret=secret))
        self.assertFalse(verify_claim(dict(claim, ttl=99999), secret=secret))
        with self.assertRaises(PermissionError):
            issue_claim("t3", "x", secret="")            # fail-closed

    def test_payload_validation(self):
        self.assertEqual(validate_task_payload("generate_batch", {"batch": "93"}), [])
        self.assertTrue(validate_task_payload("generate_batch", {"batch": "93; rm -rf"}))
        self.assertTrue(validate_task_payload("generate_batch", {"seeds": "42,drop"}))
        self.assertTrue(validate_task_payload("hacked_type", {}))

    def test_audit_log(self):
        with tempfile.TemporaryDirectory() as td:
            audit = AuditLog(Path(td) / "audit.jsonl")
            audit.emit("unit", trace_id="t4", k=1)
            self.assertEqual(audit.tail(1)[0]["action"], "unit")


class TestGatewayPayloadMerge(unittest.TestCase):
    """B2 实测事故防回归（2026-10-05）：顶层 dry_run 曾被 pydantic 静默丢弃致真实执行"""

    def test_top_level_dry_run_merged_into_payload(self):
        from agent.h3_agent.gateway import TaskRequest, merge_task_payload
        req = TaskRequest(task_type="generate_batch", batch="99", dry_run=True)
        payload = merge_task_payload(req)
        self.assertIs(payload.get("dry_run"), True)
        self.assertEqual(payload.get("batch"), "99")

    def test_dry_run_absent_stays_untouched(self):
        from agent.h3_agent.gateway import TaskRequest, merge_task_payload
        payload = merge_task_payload(TaskRequest(task_type="quality_check", batch="91"))
        self.assertNotIn("dry_run", payload)   # 未声明不注入（保持显式）

    def test_nested_payload_not_clobbered(self):
        from agent.h3_agent.gateway import TaskRequest, merge_task_payload
        req = TaskRequest(task_type="generate_single", payload={"seeds": "42,10"},
                          batch="94", dry_run=False)
        payload = merge_task_payload(req)
        self.assertEqual(payload["seeds"], "42,10")
        self.assertIs(payload["dry_run"], False)


class TestAgents(unittest.TestCase):
    def test_production_agent_whitelist_and_dry_run(self):
        from agent.h3_agent.agents import H3ProductionAgent
        t = InMemoryTransport()
        agent = H3ProductionAgent(transport=t, executor=dry_executor,
                                  enforce_claim=False)
        result = agent.handle_direct("generate_batch", {"batch": "93", "dry_run": True})
        self.assertEqual(result["task"], "generate_batch")
        self.assertIn("--auto", result["run"]["argv"])

    def test_production_agent_rejects_non_whitelist(self):
        from agent.h3_agent.agents import H3ProductionAgent
        agent = H3ProductionAgent(transport=InMemoryTransport(),
                                  executor=dry_executor, enforce_claim=False)
        with self.assertRaises(ValueError):
            agent.handle_direct("hack", {})

    def test_quality_agent_pass(self):
        from agent.h3_agent.agents import H3QualityAgent
        with tempfile.TemporaryDirectory() as td:
            fake_manifest(Path(td), "91")
            orig = config.REPO_ROOT
            config.REPO_ROOT = Path(td)       # manifest 隔离到临时目录
            try:
                agent = H3QualityAgent(transport=InMemoryTransport(),
                                       enforce_claim=False)
                good = agent.handle_direct("quality_check", {"batch": "91"})
                self.assertEqual(good["verdict"], "passed")
                self.assertGreaterEqual(good["qc_score"], 6.0)
            finally:
                config.REPO_ROOT = orig

    def test_quality_core_records(self):
        from agent.h3_agent.agents.quality_agent import H3QualityAgent
        bad = H3QualityAgent.check_records(
            {"records": [{"status": "FAILED", "error": "oom"},
                         {"status": "SUCCESS", "lipsync": {"score_norm": 0.5}}]})
        self.assertEqual(bad["verdict"], "rework")
        self.assertGreater(len(bad["suggestions"]), 0)

    def test_security_agent_audit(self):
        from agent.h3_agent.agents import H3SecurityAgent
        with tempfile.TemporaryDirectory() as td:
            import agent.h3_agent.security as sec
            orig = sec.config.AUDIT_LOG_PATH
            sec.config.AUDIT_LOG_PATH = Path(td) / "a.jsonl"
            try:
                agent = H3SecurityAgent(transport=InMemoryTransport(),
                                        enforce_claim=False)
                report = agent.handle_direct("security_audit", {"scan_glob": "docs/*.md"})
                self.assertIn(report["verdict"], ("passed", "blocked"))
                self.assertIn("claim_system", report)
            finally:
                sec.config.AUDIT_LOG_PATH = orig


class TestOrchestrator(unittest.TestCase):
    def test_stage4_closed_loop_with_snapshot(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            fake_manifest(tdp, "93")
            orig_root = config.REPO_ROOT
            config.REPO_ROOT = tdp            # manifest/快照隔离到临时目录
            try:
                orch = H3StageOrchestrator("unit_proj", transport=InMemoryTransport())
                orch.production._executor = dry_executor   # dry-run 不真跑 GPU
                result = orch.run_audiovisual_stage(batch="93")
                self.assertEqual(result["verdict"], "passed")
                self.assertEqual(StageStatus(result["state"]["status"]),
                                 StageStatus.PASSED)
                snap = orch.snapshot()
                self.assertEqual(snap["stage"], "04_audiovisual_gen")
                self.assertTrue(
                    (tdp / "projects/unit_proj/state/audiovisual_state.json").exists())
            finally:
                config.REPO_ROOT = orig_root


class TestStoryboardGate(unittest.TestCase):
    """P1-1 分镜确认闸门（docs/18，2026-10-05）：第六态 + submit/confirm 闭环"""

    def _orch(self, tdp: Path):
        fake_manifest(tdp, "95")
        orch = H3StageOrchestrator("sb_proj", transport=InMemoryTransport())
        orch.production._executor = dry_executor  # 生成侧 dry；质检官直读 fake_manifest
        return orch

    def test_gate_full_flow_and_sixth_state(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            cand_dir = tdp / "ref_images" / "characters"
            cand_dir.mkdir(parents=True)
            for n in ("g1_c1.png", "g1_c2.png"):
                (cand_dir / n).write_bytes(b"x")
            orig_root = config.REPO_ROOT
            config.REPO_ROOT = tdp
            try:
                orch = self._orch(tdp)
                # 未提交就确认 → 拒绝
                with self.assertRaises(ValueError):
                    orch.confirm_storyboard("characters/g1_c1.png")
                # 提交 → 第六态
                sb = orch.submit_storyboard("95", ["characters/g1_c1.png",
                                                   "characters/g1_c2.png"])
                self.assertEqual(sb["status"], "waiting_feedback")
                self.assertEqual(orch.storyboard_status()["status"],
                                 "waiting_feedback")
                # 非法选定 → 拒绝
                with self.assertRaises(ValueError):
                    orch.confirm_storyboard("characters/other.png")
                # 确认 → 阶段4 闭环（dry executor → passed）
                result = orch.confirm_storyboard("characters/g1_c1.png",
                                                 quality="preview", dry_run=True)
                self.assertEqual(result["verdict"], "passed")
                self.assertEqual(result["storyboard"]["asset_ref"],
                                 "characters/g1_c1.png")
                # quality=preview 透传 argv（P2-2）
                argv = result["generate"]["run"]["argv"]
                self.assertIn("--preview", argv)
                self.assertIn("--dry-run", argv)
            finally:
                config.REPO_ROOT = orig_root

    def test_gate_candidate_constraints(self):
        with tempfile.TemporaryDirectory() as td:
            tdp = Path(td)
            d = tdp / "ref_images" / "characters"
            d.mkdir(parents=True)
            (d / "a.png").write_bytes(b"x")
            orig_root = config.REPO_ROOT
            config.REPO_ROOT = tdp
            try:
                orch = self._orch(tdp)
                # 越界路径（路径穿越防护）
                with self.assertRaises(ValueError):
                    orch.submit_storyboard("95", ["../../etc/hosts"])
                # 不存在候选
                with self.assertRaises(ValueError):
                    orch.submit_storyboard("95", ["characters/ghost.png"])
                # 超 4 张
                with self.assertRaises(ValueError):
                    orch.submit_storyboard("95", [f"characters/a.png"] * 5)
                # 批次名违规
                with self.assertRaises(ValueError):
                    orch.submit_storyboard("../evil", ["characters/a.png"])
            finally:
                config.REPO_ROOT = orig_root


if __name__ == "__main__":
    unittest.main(verbosity=2)
