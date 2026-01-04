/**
 * 工具函数单元测试示例
 */

import { describe, it, expect } from 'vitest'
import {
  generateUUID,
  formatFileSize,
  getConfidenceColor,
  getConfidenceLabel,
} from '../helpers'

describe('helpers', () => {
  describe('generateUUID', () => {
    it('should generate a valid UUID v4', () => {
      const uuid = generateUUID()
      expect(uuid).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i)
    })

    it('should generate unique UUIDs', () => {
      const uuid1 = generateUUID()
      const uuid2 = generateUUID()
      expect(uuid1).not.toBe(uuid2)
    })
  })

  describe('formatFileSize', () => {
    it('should format bytes correctly', () => {
      expect(formatFileSize(0)).toBe('0 B')
      expect(formatFileSize(1024)).toBe('1 KB')
      expect(formatFileSize(1024 * 1024)).toBe('1 MB')
      expect(formatFileSize(1024 * 1024 * 1024)).toBe('1 GB')
    })

    it('should handle decimal places', () => {
      expect(formatFileSize(1536)).toBe('1.5 KB')
      expect(formatFileSize(1024 * 1024 * 1.5)).toBe('1.5 MB')
    })
  })

  describe('getConfidenceColor', () => {
    it('should return success color for high confidence', () => {
      expect(getConfidenceColor(0.95)).toBe('#52C41A')
      expect(getConfidenceColor(1.0)).toBe('#52C41A')
    })

    it('should return warning color for medium confidence', () => {
      expect(getConfidenceColor(0.8)).toBe('#FAAD14')
      expect(getConfidenceColor(0.7)).toBe('#FAAD14')
    })

    it('should return danger color for low confidence', () => {
      expect(getConfidenceColor(0.5)).toBe('#FF4D4F')
      expect(getConfidenceColor(0.0)).toBe('#FF4D4F')
    })
  })

  describe('getConfidenceLabel', () => {
    it('should return correct labels', () => {
      expect(getConfidenceLabel(0.95)).toBe('高')
      expect(getConfidenceLabel(0.8)).toBe('中')
      expect(getConfidenceLabel(0.5)).toBe('低')
    })
  })
})

