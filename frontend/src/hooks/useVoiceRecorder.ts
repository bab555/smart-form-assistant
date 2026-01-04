/**
 * 语音录制 Hook
 */

import { useState, useRef, useCallback } from 'react'
import RecordRTC, { StereoAudioRecorder } from 'recordrtc'
import type { RecordingState } from '@types'
import { AUDIO_CONFIG } from '@utils/constants'

export function useVoiceRecorder() {
  const [recordingState, setRecordingState] = useState<RecordingState>({
    isRecording: false,
    audioBlob: null,
    duration: 0,
    status: 'idle',
  })

  const recorderRef = useRef<RecordRTC | null>(null)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const startTimeRef = useRef<number>(0)

  /**
   * 开始录音
   */
  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })

      const recorder = new RecordRTC(stream, {
        type: 'audio',
        mimeType: AUDIO_CONFIG.mimeType,
        recorderType: StereoAudioRecorder,
        numberOfAudioChannels: AUDIO_CONFIG.numberOfAudioChannels,
        desiredSampRate: AUDIO_CONFIG.sampleRate,
        timeSlice: AUDIO_CONFIG.timeSlice,
      })

      recorder.startRecording()
      recorderRef.current = recorder
      startTimeRef.current = Date.now()

      setRecordingState({
        isRecording: true,
        audioBlob: null,
        duration: 0,
        status: 'recording',
      })

      // 启动计时器
      timerRef.current = setInterval(() => {
        const duration = Math.floor((Date.now() - startTimeRef.current) / 1000)
        setRecordingState((prev: any) => ({ ...prev, duration }))

        // 超过最大时长自动停止
        if (duration >= AUDIO_CONFIG.maxDuration) {
          stopRecording()
        }
      }, 100)
    } catch (error) {
      console.error('启动录音失败:', error)
      setRecordingState((prev: any) => ({
        ...prev,
        status: 'error',
      }))
    }
  }, [])

  /**
   * 停止录音
   */
  const stopRecording = useCallback(async () => {
    return new Promise<Blob | null>((resolve) => {
      if (!recorderRef.current) {
        resolve(null)
        return
      }

      const recorder = recorderRef.current

      recorder.stopRecording(() => {
        const blob = recorder.getBlob()

        // 停止所有音频轨道
        recorder.stream.getTracks().forEach((track: any) => track.stop())

        // 清除计时器
        if (timerRef.current) {
          clearInterval(timerRef.current)
          timerRef.current = null
        }

        setRecordingState((prev: any) => ({
          ...prev,
          isRecording: false,
          audioBlob: blob,
          status: 'success',
        }))

        recorderRef.current = null
        resolve(blob)
      })
    })
  }, [])

  /**
   * 取消录音
   */
  const cancelRecording = useCallback(() => {
    if (recorderRef.current) {
      recorderRef.current.stopRecording(() => {
        recorderRef.current?.stream.getTracks().forEach((track: any) => track.stop())
        recorderRef.current = null
      })
    }

    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }

    setRecordingState({
      isRecording: false,
      audioBlob: null,
      duration: 0,
      status: 'idle',
    })
  }, [])

  /**
   * 重置状态
   */
  const reset = useCallback(() => {
    setRecordingState({
      isRecording: false,
      audioBlob: null,
      duration: 0,
      status: 'idle',
    })
  }, [])

  return {
    recordingState,
    startRecording,
    stopRecording,
    cancelRecording,
    reset,
  }
}

