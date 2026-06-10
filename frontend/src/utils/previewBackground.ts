export type PreviewBackground = "checkerboard" | "white" | "green" | "magenta";

export const previewBackgroundModes: Array<{ value: PreviewBackground; label: string }> = [
  { value: "checkerboard", label: "棋盘格" },
  { value: "white", label: "白底" },
  { value: "green", label: "绿底" },
  { value: "magenta", label: "品红底" }
];
