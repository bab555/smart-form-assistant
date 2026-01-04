/**
 * 数据转换工具
 * 处理 snake_case (后端) ↔ camelCase (前端) 转换
 */

/**
 * 将 snake_case 转换为 camelCase
 */
function snakeToCamel(str: string): string {
  return str.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase())
}

/**
 * 将 camelCase 转换为 snake_case
 */
function camelToSnake(str: string): string {
  return str.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`)
}

/**
 * 递归转换对象的键名：snake_case -> camelCase
 */
export function keysToCamel<T = any>(obj: any): T {
  if (obj === null || obj === undefined) return obj
  if (typeof obj !== 'object') return obj
  if (obj instanceof Date) return obj as T
  if (Array.isArray(obj)) return obj.map(keysToCamel) as any

  return Object.keys(obj).reduce((acc, key) => {
    const camelKey = snakeToCamel(key)
    acc[camelKey] = keysToCamel(obj[key])
    return acc
  }, {} as any)
}

/**
 * 递归转换对象的键名：camelCase -> snake_case
 */
export function keysToSnake<T = any>(obj: any): T {
  if (obj === null || obj === undefined) return obj
  if (typeof obj !== 'object') return obj
  if (obj instanceof Date) return obj as T
  if (Array.isArray(obj)) return obj.map(keysToSnake) as any

  return Object.keys(obj).reduce((acc, key) => {
    const snakeKey = camelToSnake(key)
    acc[snakeKey] = keysToSnake(obj[key])
    return acc
  }, {} as any)
}

/**
 * 转换单个 FormItem（从后端格式到前端格式）
 */
export function transformFormItemFromAPI(item: any): any {
  return {
    key: item.key,
    label: item.label,
    value: item.value,
    originalText: item.original_text,
    confidence: item.confidence,
    isAmbiguous: item.is_ambiguous,
    candidates: item.candidates,
    dataType: item.data_type,
  }
}

/**
 * 转换单个 FormItem（从前端格式到后端格式）
 */
export function transformFormItemToAPI(item: any): any {
  return {
    key: item.key,
    label: item.label,
    value: item.value,
    original_text: item.originalText,
    confidence: item.confidence,
    is_ambiguous: item.isAmbiguous,
    candidates: item.candidates,
    data_type: item.dataType,
  }
}

