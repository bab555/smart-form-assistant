/**
 * 表单数据状态管理（Zustand）
 */

import { create } from 'zustand'
import type { FormRow, FormItem, AgentStep } from '@types'

interface FormState {
  // 数据
  rows: FormRow[]
  currentStep: AgentStep
  isThinking: boolean
  selectedCellIndex: { row: number; col: number } | null

  // Actions
  setRows: (rows: FormRow[]) => void
  addRow: (row: FormRow) => void
  updateCell: (rowIndex: number, key: string, value: any) => void
  updateCellByIndex: (rowIndex: number, colIndex: number, updates: Partial<FormItem>) => void
  removeRow: (rowIndex: number) => void
  clearRows: () => void
  setCurrentStep: (step: AgentStep) => void
  setThinking: (isThinking: boolean) => void
  setSelectedCell: (index: { row: number; col: number } | null) => void
  setAmbiguous: (rowIndex: number, key: string, candidates: string[]) => void
  resolveAmbiguity: (rowIndex: number, key: string, selectedValue: string) => void
  markCellAsModified: (rowIndex: number, key: string) => void

  // Computed
  hasAmbiguousCells: () => boolean
  getCell: (rowIndex: number, key: string) => FormItem | undefined
}

export const useFormStore = create<FormState>((set, get) => ({
  rows: [],
  currentStep: 'idle',
  isThinking: false,
  selectedCellIndex: null,

  setRows: (rows) => set({ rows }),

  addRow: (row) =>
    set((state) => ({
      rows: [...state.rows, row],
    })),

  updateCell: (rowIndex, key, value) =>
    set((state) => {
      const newRows = [...state.rows]
      const row = newRows[rowIndex]
      if (!row) return state

      const cellIndex = row.findIndex((item: any) => item.key === key)
      if (cellIndex === -1) return state

      newRows[rowIndex] = [...row]
      newRows[rowIndex][cellIndex] = {
        ...row[cellIndex],
        value,
        isAmbiguous: false,
        candidates: undefined,
      }

      return { rows: newRows }
    }),

  updateCellByIndex: (rowIndex, colIndex, updates) =>
    set((state) => {
      const newRows = [...state.rows]
      const row = newRows[rowIndex]
      if (!row || !row[colIndex]) return state

      newRows[rowIndex] = [...row]
      newRows[rowIndex][colIndex] = {
        ...row[colIndex],
        ...updates,
      }

      return { rows: newRows }
    }),

  removeRow: (rowIndex) =>
    set((state) => ({
      rows: state.rows.filter((_, index) => index !== rowIndex),
    })),

  clearRows: () => set({ rows: [], currentStep: 'idle', isThinking: false }),

  setCurrentStep: (step) => set({ currentStep: step }),

  setThinking: (isThinking) => set({ isThinking }),

  setSelectedCell: (index) => set({ selectedCellIndex: index }),

  setAmbiguous: (rowIndex, key, candidates) =>
    set((state) => {
      const newRows = [...state.rows]
      const row = newRows[rowIndex]
      if (!row) return state

      const cellIndex = row.findIndex((item: any) => item.key === key)
      if (cellIndex === -1) return state

      newRows[rowIndex] = [...row]
      newRows[rowIndex][cellIndex] = {
        ...row[cellIndex],
        isAmbiguous: true,
        candidates,
      }

      return { rows: newRows }
    }),

  resolveAmbiguity: (rowIndex, key, selectedValue) =>
    set((state) => {
      const newRows = [...state.rows]
      const row = newRows[rowIndex]
      if (!row) return state

      const cellIndex = row.findIndex((item: any) => item.key === key)
      if (cellIndex === -1) return state

      newRows[rowIndex] = [...row]
      newRows[rowIndex][cellIndex] = {
        ...row[cellIndex],
        value: selectedValue,
        isAmbiguous: false,
        candidates: undefined,
        confidence: 1.0, // 人工确认后置信度为 1.0
      }

      return { rows: newRows }
    }),

  markCellAsModified: (rowIndex, key) =>
    set((state) => {
      const newRows = [...state.rows]
      const row = newRows[rowIndex]
      if (!row) return state

      const cellIndex = row.findIndex((item: any) => item.key === key)
      if (cellIndex === -1) return state

      // 可以添加一个 isModified 标记（需要扩展 FormItem 类型）
      // 这里暂时通过 confidence = 1.0 来标识
      newRows[rowIndex] = [...row]
      newRows[rowIndex][cellIndex] = {
        ...row[cellIndex],
        confidence: 1.0,
      }

      return { rows: newRows }
    }),

  hasAmbiguousCells: () => {
    const state = get()
    return state.rows.some((row) => row.some((cell: any) => cell.isAmbiguous))
  },

  getCell: (rowIndex, key) => {
    const state = get()
    const row = state.rows[rowIndex]
    if (!row) return undefined
    return row.find((item: any) => item.key === key)
  },
}))

