// 模拟实时转写功能
export class TranscriptSimulator {
  constructor(lines) {
    this.allLines = lines;
    this.currentLines = [];
    this.currentIndex = 0;
    this.listeners = [];
  }

  start(intervalMs = 3000) {
    this.stop();
    this.currentLines = [];
    this.currentIndex = 0;

    this.interval = setInterval(() => {
      if (this.currentIndex < this.allLines.length) {
        this.currentLines.push(this.allLines[this.currentIndex]);
        this.currentIndex++;
        this.notifyListeners();
      } else {
        this.stop();
      }
    }, intervalMs);
  }

  stop() {
    if (this.interval) {
      clearInterval(this.interval);
      this.interval = null;
    }
  }

  reset() {
    this.stop();
    this.currentLines = [];
    this.currentIndex = 0;
    this.notifyListeners();
  }

  getCurrentLines() {
    return this.currentLines;
  }

  addListener(callback) {
    this.listeners.push(callback);
    return () => {
      this.listeners = this.listeners.filter(cb => cb !== callback);
    };
  }

  notifyListeners() {
    this.listeners.forEach(callback => callback(this.currentLines));
  }

  isComplete() {
    return this.currentIndex >= this.allLines.length;
  }
}

// 生成更多模拟对话数据
export function generateMoreTranscriptLines(topic) {
  const templates = {
    '回顾上周重点进展': [
      ['14:11', '刘明', '上周用户量增长了 15%，超出预期目标。'],
      ['14:12', '张涛', '数据很不错，我们继续保持这个势头。'],
    ],
    '对齐本周工作计划': [
      ['14:13', '王强', '本周主要聚焦在性能优化和 bug 修复上。'],
      ['14:14', '李娜', '我这边会跟进前端的响应速度问题。'],
    ],
    '讨论当前的关键问题': [
      ['14:15', '陈晨', '目前最大的问题是服务器负载有点高。'],
      ['14:16', '张涛', '这个问题我们需要尽快解决，王强你来跟进一下。'],
    ],
    '明确下一步行动项': [
      ['14:17', '李娜', '那我整理一下待办事项，明天发给大家。'],
      ['14:18', '张涛', '好的，大家还有其他问题吗？'],
    ],
  };

  return templates[topic] || [];
}
