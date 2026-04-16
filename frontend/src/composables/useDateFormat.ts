/**
 * Composable for formatting timestamps to localized date strings.
 */
export function useDateFormat() {
  /**
   * Format a Unix timestamp (in seconds) to a locale string.
   * @param timestamp - Unix timestamp in seconds
   * @returns Formatted string like "2024/1/15 14:30:05" or empty string if invalid
   */
  const formatDate = (timestamp: number | undefined): string => {
    if (typeof timestamp !== 'number' || !timestamp) return '';
    const date = new Date(timestamp * 1000);
    return date.toLocaleString('zh-CN', { hour12: false });
  };

  return { formatDate };
}
