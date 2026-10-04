// src/stores/chatSlice.ts — AI 助手（useChat 状态镜像 + 输入态）
import { create } from "zustand";
import type { UIMessage } from "ai";

interface ChatState {
  messages: UIMessage[];
  streaming: boolean;
  lastError: string | null;
  setMessages: (messages: UIMessage[]) => void;
  setStreaming: (v: boolean) => void;
  setLastError: (e: string | null) => void;
  clear: () => void;
}

export const useChatStore = create<ChatState>()((set) => ({
  messages: [],
  streaming: false,
  lastError: null,
  setMessages: (messages) => set({ messages }),
  setStreaming: (v) => set({ streaming: v }),
  setLastError: (e) => set({ lastError: e }),
  clear: () => set({ messages: [], lastError: null, streaming: false }),
}));
