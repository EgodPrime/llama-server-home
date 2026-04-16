import { onUnmounted, type Ref } from 'vue';

/**
 * Composable for polling data at regular intervals.
 * Automatically cleans up the interval on component unmount.
 */
export function usePolling(
  callback: () => void | Promise<void>,
  interval: number,
  options: { immediate?: boolean } = {}
) {
  const { immediate = false } = options;
  let timer: ReturnType<typeof setInterval> | null = null;

  const start = () => {
    if (immediate) {
      callback();
    }
    timer = setInterval(callback, interval);
  };

  const stop = () => {
    if (timer) {
      clearInterval(timer);
      timer = null;
    }
  };

  onUnmounted(() => {
    stop();
  });

  return { start, stop };
}
