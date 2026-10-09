// src/stores/chatSlice.ts — AI 助手（useChat 状态镜像 + 输入态 + 跨页上下文）
import { create } from "zustand";
import type { UIMessage } from "ai";

interface ChatState {
  messages: UIMessage[];
  streaming: boolean;
  lastError: string | null;
  /** 跨页「带上下文提问」：来源页（Pipeline/BatchDetail…）序列化好的首条提问 */
  pendingPrompt: string | null;
  setMessages: (messages: UIMessage[]) => void;
  setStreaming: (v: boolean) => void;
  setLastError: (e: string | null) => void;
  setPendingPrompt: (p: string) => void;
  /** 取出并清除 pendingPrompt（AssistantPage 挂载时消费，仅一次） */
  consumePendingPrompt: () => string | null;
  clear: () => void;
}

export const useChatStore = create<ChatState>()((set, get) => ({
  messages: [],
  streaming: false,
  lastError: null,
  pendingPrompt: null,
  setMessages: (messages) => set({ messages }),
  setStreaming: (v) => set({ streaming: v }),
  setLastError: (e) => set({ lastError: e }),
  setPendingPrompt: (p) => set({ pendingPrompt: p }),
  consumePendingPrompt: () => {
    const p = get().pendingPrompt;
    if (p !== null) set({ pendingPrompt: null });
    return p;
  },
  clear: () => set({ messages: [], lastError: null, streaming: false }),
}));
