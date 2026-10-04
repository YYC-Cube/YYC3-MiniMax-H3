// src/lib/sse.ts — 类型化 EventSource 封装（命名事件分发 + 断线重连 + 注销清理）
export interface SSEOptions {
  url: string;
  /** 命名事件 → 原始 data 字符串处理（调用方用 zod 校验） */
  handlers: Record<string, (data: string) => void>;
  onOpen?: () => void;
  onError?: () => void;
  /** 断线重连延迟（默认 3s） */
  reconnectMs?: number;
}

/** 建立 SSE 连接；返回注销函数（组件卸载/页面切换时调用） */
export function createSSE(options: SSEOptions): () => void {
  const { url, handlers, onOpen, onError, reconnectMs = 3_000 } = options;
  let es: EventSource | null = null;
  let timer: ReturnType<typeof setTimeout> | null = null;
  let disposed = false;

  const teardown = () => {
    if (timer) clearTimeout(timer);
    timer = null;
    es?.close();
    es = null;
  };

  const connect = () => {
    if (disposed) return;
    teardown();
    es = new EventSource(url);
    es.onopen = () => onOpen?.();

    for (const [event, handler] of Object.entries(handlers)) {
      es.addEventListener(event, (e) => handler((e as MessageEvent).data as string));
    }

    es.onerror = () => {
      teardown();
      onError?.();
      if (!disposed) timer = setTimeout(connect, reconnectMs);
    };
  };

  connect();

  return () => {
    disposed = true;
    teardown();
  };
}
