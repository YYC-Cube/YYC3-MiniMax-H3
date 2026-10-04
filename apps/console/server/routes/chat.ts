// server/routes/chat.ts — /api/chat：AI 助手（Vercel AI SDK streamText → UIMessageStream）
// 提供商：0379-World 网关 OpenAI 兼容端点（2026-10-05 Phase 2B 实测通过）：
//   - GET /v1/models 200（X-API-Key 与 Bearer 双通道，16 模型：glm-4-flash/glm-4-plus/deepseek-* 等）
//   - POST /v1/chat/completions 非流式/流式（OpenAI SSE + yyc3-flush 哨兵）契约达标
// 默认模型 glm-4-flash（128k 上下文）；H3_LLM_API_KEY 缺省复用 H3_GATEWAY_API_KEY（同一业务键）。
import { Hono } from "hono";
import { convertToModelMessages, streamText, type UIMessage } from "ai";
import { createOpenAICompatible } from "@ai-sdk/openai-compatible";
import { authorizePipeline } from "../lib/api-auth.js";
import { GATEWAY_URL } from "../lib/gateway.js";

export const chatRoutes = new Hono();

const DEFAULT_MODEL = "glm-4-flash";

const SYSTEM_PROMPT = `你是 YYC3-MiniMax-H3 的提示词优化助手。
项目背景：MiniMax-H3 本地视频/数字人生成生产线（Ref2VA 参考图口型同步 / FL2VA 文生音视频）。
用户输入原始生成诉求时，请输出结构化的 H3 提示词：
- integrated_multimodal_description（主体/动作/镜头/氛围分句）
- overall_soundscape（环境声与情绪声景）
- non_diegetic_music（配乐风格）
- 关键参数建议（分辨率/帧数/步数等，参考 480×832 / num_frames%17==5 / 50 步）
回答保持简洁，用中文，分节输出。`;

function makeProvider() {
  const baseURL = (process.env.H3_LLM_BASE_URL ?? `${GATEWAY_URL}/v1`).replace(/\/$/, "");
  const apiKey = process.env.H3_LLM_API_KEY ?? process.env.H3_GATEWAY_API_KEY ?? "";
  if (!apiKey) throw new Error("H3_LLM_API_KEY/H3_GATEWAY_API_KEY 未配置（LLM 走 0379-World 网关 OpenAI 兼容端点）");
  return createOpenAICompatible({ name: "h3-gateway", baseURL, apiKey });
}

chatRoutes.post("/", async (c) => {
  if (!authorizePipeline(c)) return c.json({ error: "unauthorized" }, 401);

  let body: { messages?: UIMessage[] };
  try {
    body = await c.req.json();
  } catch {
    return c.json({ error: "invalid json" }, 400);
  }
  const messages = Array.isArray(body.messages) ? body.messages : [];
  if (messages.length === 0) return c.json({ error: "messages 必填" }, 400);

  try {
    const provider = makeProvider();
    const modelId = process.env.H3_LLM_MODEL ?? DEFAULT_MODEL;
    const result = streamText({
      model: provider.chatModel(modelId),
      system: SYSTEM_PROMPT,
      messages: await convertToModelMessages(messages),
    });
    // UIMessageStream 协议（AI SDK v7 useChat 默认传输）
    return result.toUIMessageStreamResponse();
  } catch (e) {
    return c.json({ error: `AI 服务不可用: ${String(e)}` }, 502);
  }
});
