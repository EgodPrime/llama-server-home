/**
 * Composable for mapping status strings to colors.
 * Provides consistent color coding across the application.
 */
export function useStatusColor() {
  const statusColors: Record<string, string> = {
    // Node statuses
    ONLINE: '#52c41a',
    OFFLINE: '#ff4d4f',
    // Instance statuses
    RUNNING: '#52c41a',
    STOPPED: '#faad14',
    ERROR: '#ff4d4f',
    RESTARTING: '#faad14',
    NOT_FOUND: '#ff4d4f',
    UNKNOWN: '#595959',
    // Task statuses
    INIT: '#1890ff',
    PROCESSING: '#faad14',
    FINISHED: '#52c41a',
    FAILED: '#ff4d4f',
  };

  const getColor = (status: string | undefined): string => {
    if (!status) return '#595959';
    return statusColors[status.toUpperCase()] || '#595959';
  };

  return { getColor };
}
