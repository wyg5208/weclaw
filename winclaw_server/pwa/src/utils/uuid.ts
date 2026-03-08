/**
 * 生成 UUID
 * 兼容非 HTTPS 环境（crypto.randomUUID 仅在安全上下文中可用）
 */

export function generateUUID(): string {
  // 优先使用原生 API（HTTPS 环境下可用）
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  
  // Fallback: 使用 crypto.getRandomValues 实现
  if (typeof crypto !== 'undefined' && crypto.getRandomValues) {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const array = new Uint8Array(1)
      crypto.getRandomValues(array)
      const r = array[0] % 16
      const v = c === 'x' ? r : (r & 0x3 | 0x8)
      return v.toString(16)
    })
  }
  
  // 最后的 fallback: Math.random（不推荐，但确保可用）
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = Math.random() * 16 | 0
    const v = c === 'x' ? r : (r & 0x3 | 0x8)
    return v.toString(16)
  })
}
