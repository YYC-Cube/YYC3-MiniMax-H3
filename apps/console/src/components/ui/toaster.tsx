import { Toaster as Sonner } from "sonner";

type ToasterProps = React.ComponentProps<typeof Sonner>;

/** 全局通知（sonner，深色主题对齐品牌） */
export function Toaster(props: ToasterProps) {
  return (
    <Sonner
      theme="dark"
      position="bottom-right"
      richColors
      closeButton
      toastOptions={{
        classNames: {
          toast: "border border-border",
        },
      }}
      {...props}
    />
  );
}
