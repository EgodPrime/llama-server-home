import { Modal } from 'ant-design-vue';

/**
 * Composable for showing confirmation dialogs using Ant Design Modal.
 * Replaces native window.confirm() with consistent UI.
 */
export function useConfirm() {
  /**
   * Show a confirmation dialog and execute callback if confirmed.
   * @param options - Configuration options
   * @param options.title - Dialog title
   * @param options.content - Dialog content/message
   * @param options.okText - Text for confirm button (default: '确定')
   * @param options.cancelText - Text for cancel button (default: '取消')
   * @param onConfirm - Callback to execute when confirmed
   */
  const confirm = (options: {
    title: string;
    content: string;
    okText?: string;
    cancelText?: string;
    onConfirm: () => void | Promise<void>;
  }) => {
    const { title, content, okText = '确定', cancelText = '取消', onConfirm } = options;

    Modal.confirm({
      title,
      content,
      okText,
      cancelText,
      async onOk() {
        await onConfirm();
      },
    });
  };

  return { confirm };
}
