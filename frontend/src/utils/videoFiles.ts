const supportedVideoExtensions = new Set([".mp4", ".mov", ".webm", ".avi", ".mkv"]);

export function firstVideoFile(files: Iterable<File>): File | null {
  for (const file of files) {
    if (isSupportedVideoFile(file)) {
      return file;
    }
  }
  return null;
}

export function isSupportedVideoFile(file: File): boolean {
  if (file.type.startsWith("video/")) {
    return true;
  }
  const extension = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
  return supportedVideoExtensions.has(extension);
}

export const videoAccept = Array.from(supportedVideoExtensions).join(",");
