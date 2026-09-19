// 验证工具
export function validateMeetingName(name) {
  if (!name || name.trim().length === 0) {
    return { valid: false, error: '会议名称不能为空' };
  }
  if (name.length > 50) {
    return { valid: false, error: '会议名称不能超过 50 个字符' };
  }
  return { valid: true };
}

export function validateAgenda(agenda) {
  if (!agenda || agenda.trim().length === 0) {
    return { valid: false, error: '会议目标不能为空' };
  }
  if (agenda.length > 500) {
    return { valid: false, error: '会议目标不能超过 500 个字符' };
  }
  return { valid: true };
}

export function validateDuration(duration) {
  if (!duration || duration <= 0) {
    return { valid: false, error: '请选择有效的会议时长' };
  }
  if (duration > 240) {
    return { valid: false, error: '会议时长不能超过 4 小时' };
  }
  return { valid: true };
}

export function validateFile(file) {
  const maxSize = 10 * 1024 * 1024; // 10MB
  const allowedTypes = [
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'image/png',
    'image/jpeg',
    'text/plain',
  ];

  if (file.size > maxSize) {
    return { valid: false, error: `文件 ${file.name} 超过 10MB 限制` };
  }

  if (!allowedTypes.includes(file.type) && !file.name.match(/\.(pdf|doc|docx|ppt|pptx|png|jpe?g|txt)$/i)) {
    return { valid: false, error: `文件 ${file.name} 格式不支持` };
  }

  return { valid: true };
}

// 格式化工具
export function formatTime(seconds) {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

export function formatDate(date) {
  if (!(date instanceof Date)) {
    date = new Date(date);
  }

  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const weekdays = ['日', '一', '二', '三', '四', '五', '六'];
  const weekday = weekdays[date.getDay()];

  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');

  return {
    full: `${year}年${month}月${day}日 周${weekday}　${hours}:${minutes}`,
    date: `${year}-${month}-${day}`,
    time: `${hours}:${minutes}`,
    weekday: `周${weekday}`,
  };
}

export function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

// 防抖函数
export function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// 节流函数
export function throttle(func, limit) {
  let inThrottle;
  return function executedFunction(...args) {
    if (!inThrottle) {
      func(...args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
}
