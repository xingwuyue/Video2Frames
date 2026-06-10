type PlaybackFrame = {
  id: string;
};

export type PlaybackAdvance = {
  frameId: string | null;
  shouldStop: boolean;
};

export function playbackFrameIds(
  frames: PlaybackFrame[],
  enabledFrameIds: Set<string>,
  hiddenFrameIds: Set<string>,
  deletedFrameIds: Set<string>
): string[] {
  return frames
    .filter((frame) => enabledFrameIds.has(frame.id) && !hiddenFrameIds.has(frame.id) && !deletedFrameIds.has(frame.id))
    .map((frame) => frame.id);
}

export function advancePlaybackFrame(frameIds: string[], currentFrameId: string | null, loop: boolean): PlaybackAdvance {
  if (frameIds.length === 0) {
    return { frameId: null, shouldStop: true };
  }

  const currentIndex = currentFrameId ? frameIds.indexOf(currentFrameId) : -1;
  if (currentIndex < 0) {
    return { frameId: frameIds[0], shouldStop: false };
  }
  if (currentIndex < frameIds.length - 1) {
    return { frameId: frameIds[currentIndex + 1], shouldStop: false };
  }
  if (loop) {
    return { frameId: frameIds[0], shouldStop: false };
  }
  return { frameId: currentFrameId, shouldStop: true };
}

export function previousPlaybackFrame(frameIds: string[], currentFrameId: string | null, loop: boolean): string | null {
  if (frameIds.length === 0) {
    return null;
  }

  const currentIndex = currentFrameId ? frameIds.indexOf(currentFrameId) : -1;
  if (currentIndex < 0) {
    return frameIds[0];
  }
  if (currentIndex > 0) {
    return frameIds[currentIndex - 1];
  }
  return loop ? frameIds[frameIds.length - 1] : currentFrameId;
}
