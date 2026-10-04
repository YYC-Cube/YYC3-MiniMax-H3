import * as React from "react";
import { cn } from "@/lib/utils";

/** 轻量滚动容器（日志台/长列表用；纯 CSS 滚动 + 细滚动条全局样式） */
const ScrollArea = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, children, ...props }, ref) => (
    <div ref={ref} className={cn("overflow-y-auto", className)} {...props}>
      {children}
    </div>
  )
);
ScrollArea.displayName = "ScrollArea";

export { ScrollArea };
