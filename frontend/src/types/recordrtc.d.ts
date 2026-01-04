/**
 * RecordRTC 类型声明
 */

declare module 'recordrtc' {
  export interface RecordRTCOptions {
    type?: 'audio' | 'video' | 'screen' | 'canvas' | 'gif'
    mimeType?: string
    recorderType?: any
    numberOfAudioChannels?: number
    desiredSampRate?: number
    timeSlice?: number
    ondataavailable?: (blob: Blob) => void
  }

  export class StereoAudioRecorder {
    constructor(mediaStream: MediaStream, options: RecordRTCOptions)
  }

  export default class RecordRTC {
    constructor(stream: MediaStream, options: RecordRTCOptions)
    startRecording(): void
    stopRecording(callback?: () => void): void
    pauseRecording(): void
    resumeRecording(): void
    getBlob(): Blob
    toURL(): string
    getDataURL(callback: (dataURL: string) => void): void
    save(fileName?: string): void
    getFromDisk(type: string, callback: (dataURL: string, type: string) => void): void
    setRecordingDuration(milliseconds: number, callback?: () => void): void
    clearRecordedData(): void
    getState(): 'inactive' | 'recording' | 'stopped' | 'paused' | 'destroyed'
    destroy(): void
    getInternalRecorder(): any
    reset(): void
    onStateChanged(state: string): void
    getSealedBlob(): Blob
    stream: MediaStream
  }
}

