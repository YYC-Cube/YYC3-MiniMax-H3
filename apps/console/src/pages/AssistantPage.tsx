// src/pages/AssistantPage.tsx — AI 助手（Vercel AI SDK v7 useChat + UIMessageStream）
// 提示词优化助手：0379-World 网关 OpenAI 兼容端点（H3_LLM_BASE_URL/H3_LLM_API_KEY）
import { useEffect, useState } from "react";
import { DefaultChatTransport, type TextUIPart } from "ai";
import { useChat } from "@ai-sdk/react";
import { Bot, Eraser, Loader2, Send, Square, User } from "lucide-react";
import { PageTransition } from "@/components/layout/PageTransition";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { useChatStore } from "@/stores/chatSlice";

export default function AssistantPage() {
  const chat = useChat({ transport: new DefaultChatTransport({ api: "/api/chat" }) });
  const [input, setInput] = useState("");

  const streaming = chat.status === "streaming" || chat.status === "submitted";
  const lastError = chat.error?.message ?? null;

  // 镜像到 chatSlice（slice 模式：跨页状态单一出口）
  useEffect(() => {
    useChatStore.getState().setMessages(chat.messages);
  }, [chat.messages]);
  useEffect(() => {
    useChatStore.getState().setStreaming(streaming);
  }, [streaming]);
  useEffect(() => {
    useChatStore.getState().setLastError(lastError);
  }, [lastError]);

  const send = () => {
    if (!input.trim() || streaming) return;
    void chat.sendMessage({ text: input });
    setInput("");
  };

  const clear = () => {
    chat.setMessages([]);
    useChatStore.getState().clear();
  };

  const textOf = (message: { parts: unknown[] }) =>
    message.parts.filter((p): p is TextUIPart => (p as TextUIPart).type === "text")
      .map((p) => p.text)
      .join("");

  return (
    <PageTransition>
      <div className="mx-auto flex max-w-3xl flex-col gap-4">
        <div className="flex items-center gap-3">
          <h1 className="text-xl font-bold">AI 助手 · H3 提示词优化</h1>
          <Button variant="ghost" size="sm" onClick={clear} className="ml-auto">
            <Eraser />
            清空对话
          </Button>
        </div>

        <Card>
          <CardContent className="flex max-h-[55vh] flex-col gap-3 overflow-y-auto pt-5">
            {chat.messages.length === 0 ? (
              <p className="py-8 text-center text-sm text-muted-foreground">
                输入你的视频/数字人生成诉求，助手将输出结构化的 H3 提示词
                （integrated_multimodal_description / overall_soundscape / non_diegetic_music / 参数建议）
              </p>
            ) : (
              chat.messages.map((m) => {
                const isUser = m.role === "user";
                const text = textOf(m);
                return (
                  <div key={m.id} className={cn("flex flex-col gap-1", isUser ? "items-end" : "items-start")}>
                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                      {isUser ? (
                        <>
                          <User className="size-3.5" />
                          你
                        </>
                      ) : (
                        <>
                          <Bot className="size-3.5" />
                          H3 助手
                        </>
                      )}
                    </div>
                    <div
                      className={cn(
                        "whitespace-pre-wrap rounded-lg border px-3 py-2 text-sm",
                        isUser
                          ? "border-primary/40 bg-primary/10 text-foreground"
                          : "border-border bg-background text-foreground"
                      )}
                    >
                      {text}
                      {!isUser && streaming && m.id === chat.messages[chat.messages.length - 1]?.id ? (
                        <span className="ml-0.5 inline-block h-3.5 w-1.5 animate-pulse bg-primary align-middle" />
                      ) : null}
                    </div>
                  </div>
                );
              })
            )}
          </CardContent>
        </Card>

        {lastError ? (
          <p className="text-xs text-destructive">AI 服务错误：{lastError}（检查 H3_LLM_API_KEY / H3_LLM_BASE_URL 配置）</p>
        ) : null}

        <div className="flex items-end gap-2">
          <div className="flex flex-1 flex-col gap-1.5">
            <Label htmlFor="assistant-input" className="text-xs text-muted-foreground">
              输入诉求（Enter 发送 · Shift+Enter 换行）
            </Label>
            <Textarea
              id="assistant-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send();
                }
              }}
              placeholder="如：生成一位古风女子在雨中撑伞回眸的数字人视频，需要口型同步"
              rows={2}
              className="min-h-14"
            />
          </div>
          {streaming ? (
            <Button variant="outline" onClick={() => chat.stop()} aria-label="停止生成">
              <Square />
              停止
            </Button>
          ) : (
            <Button onClick={send} disabled={!input.trim()}>
              <Send />
              发送
            </Button>
          )}
        </div>
        {streaming ? (
          <p className="flex items-center gap-2 text-xs text-muted-foreground">
            <Loader2 className="animate-spin" />
            正在流式生成…
          </p>
        ) : null}
      </div>
    </PageTransition>
  );
}
