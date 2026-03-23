/**
 * 语音识别工具 - 封装 Web Speech API
 * 
 * 支持 Chrome/Edge 浏览器的原生语音识别功能
 */

// SpeechRecognition 类型定义
interface IWindow extends Window {
  webkitSpeechRecognition: any
  SpeechRecognition: any
}

export type SpeechRecognitionType = any

export interface SpeechConfig {
  /** 语言，如 'zh-CN', 'en-US' */
  lang?: string
  /** 是否连续识别 */
  continuous?: boolean
  /** 是否显示中间结果 */
  interimResults?: boolean
  /** 最大录音时长（毫秒），0 表示无限制 */
  maxDuration?: number
}

export interface RecognitionResult {
  /** 最终识别结果 */
  transcript: string
  /** 置信度 (0-1) */
  confidence: number
  /** 是否是最终结果 */
  isFinal: boolean
}

export type RecognitionState = 'idle' | 'listening' | 'processing' | 'error'

export class SpeechRecognizer {
  private recognition: SpeechRecognitionType | null = null
  private config: SpeechConfig
  private state: RecognitionState = 'idle'
  private startTime: number = 0
  private timeoutId: number | null = null
  
  // 回调函数
  onResult?: (result: RecognitionResult) => void
  onError?: (error: Error) => void
  onStart?: () => void
  onEnd?: () => void

  constructor(config: SpeechConfig = {}) {
    this.config = {
      lang: config.lang || 'zh-CN',
      continuous: config.continuous ?? false,
      interimResults: config.interimResults ?? true,
      maxDuration: config.maxDuration ?? 0
    }

    this.init()
  }

  /**
   * 初始化语音识别
   */
  private init() {
    const win = window as unknown as IWindow
    
    // 检查浏览器支持
    const SpeechRecognition = win.SpeechRecognition || win.webkitSpeechRecognition
    
    if (!SpeechRecognition) {
      console.error('浏览器不支持语音识别 API')
      return
    }

    try {
      this.recognition = new SpeechRecognition()
      this.recognition.lang = this.config.lang
      this.recognition.continuous = this.config.continuous
      this.recognition.interimResults = this.config.interimResults
      
      // 绑定事件
      this.recognition.onstart = this.handleStart.bind(this)
      this.recognition.onend = this.handleEnd.bind(this)
      this.recognition.onresult = this.handleResult.bind(this)
      this.recognition.onerror = this.handleError.bind(this)
      
      this.state = 'idle'
    } catch (error) {
      console.error('初始化语音识别失败:', error)
      this.state = 'error'
    }
  }

  /**
   * 开始录音
   */
  start() {
    if (!this.recognition) {
      this.onError?.(new Error('浏览器不支持语音识别'))
      return false
    }

    if (this.state === 'listening') {
      console.warn('正在录音中...')
      return false
    }

    try {
      this.recognition.start()
      this.startTime = Date.now()
      
      // 设置最大录音时长定时器
      if (this.config.maxDuration && this.config.maxDuration > 0) {
        this.timeoutId = window.setTimeout(() => {
          this.stop()
        }, this.config.maxDuration)
      }
      
      return true
    } catch (error) {
      console.error('启动录音失败:', error)
      this.onError?.(error as Error)
      return false
    }
  }

  /**
   * 停止录音
   */
  stop() {
    if (!this.recognition || this.state !== 'listening') {
      return
    }

    try {
      this.recognition.stop()
      
      // 清除超时定时器
      if (this.timeoutId !== null) {
        clearTimeout(this.timeoutId)
        this.timeoutId = null
      }
    } catch (error) {
      console.error('停止录音失败:', error)
    }
  }

  /**
   * 取消录音
   */
  cancel() {
    if (!this.recognition) {
      return
    }

    try {
      this.recognition.cancel()
      
      // 清除超时定时器
      if (this.timeoutId !== null) {
        clearTimeout(this.timeoutId)
        this.timeoutId = null
      }
      
      this.state = 'idle'
    } catch (error) {
      console.error('取消录音失败:', error)
    }
  }

  /**
   * 更新配置
   */
  updateConfig(config: Partial<SpeechConfig>) {
    this.config = { ...this.config, ...config }
    
    if (this.recognition) {
      if (config.lang !== undefined) {
        this.recognition.lang = config.lang
      }
      if (config.continuous !== undefined) {
        this.recognition.continuous = config.continuous
      }
      if (config.interimResults !== undefined) {
        this.recognition.interimResults = config.interimResults
      }
    }
  }

  /**
   * 获取当前状态
   */
  getState(): RecognitionState {
    return this.state
  }

  /**
   * 判断是否正在录音
   */
  isListening(): boolean {
    return this.state === 'listening'
  }

  /**
   * 处理录音开始事件
   */
  private handleStart() {
    this.state = 'listening'
    this.onStart?.()
    console.log('开始录音')
  }

  /**
   * 处理录音结束事件
   */
  private handleEnd() {
    this.state = 'idle'
    this.onEnd?.()
    console.log('录音结束')
  }

  /**
   * 处理识别结果事件
   */
  private handleResult(event: any) {
    const results = event.results
    const result = results[results.length - 1]
    const transcript = result[0].transcript
    const confidence = result[0].confidence || 0
    const isFinal = result.isFinal

    if (transcript) {
      this.onResult?.({
        transcript,
        confidence,
        isFinal
      })
    }
  }

  /**
   * 处理错误事件
   */
  private handleError(event: any) {
    let errorMessage = '语音识别错误'
    
    switch (event.error) {
      case 'no-speech':
        errorMessage = '未检测到语音'
        break
      case 'audio-capture':
        errorMessage = '无法访问麦克风'
        break
      case 'not-allowed':
        errorMessage = '麦克风权限被拒绝'
        break
      case 'network':
        errorMessage = '网络错误'
        break
      case 'aborted':
        errorMessage = '录音已取消'
        break
      default:
        errorMessage = `语音识别错误：${event.error}`
    }

    this.state = 'error'
    this.onError?.(new Error(errorMessage))
    console.error('语音识别错误:', event.error)
  }
}

// 导出单例
let speechRecognizerInstance: SpeechRecognizer | null = null

export function getSpeechRecognizer(config?: SpeechConfig): SpeechRecognizer {
  if (!speechRecognizerInstance) {
    speechRecognizerInstance = new SpeechRecognizer(config)
  }
  return speechRecognizerInstance
}

export function resetSpeechRecognizer(config?: SpeechConfig): SpeechRecognizer {
  if (speechRecognizerInstance) {
    speechRecognizerInstance.cancel()
  }
  speechRecognizerInstance = new SpeechRecognizer(config)
  return speechRecognizerInstance
}
