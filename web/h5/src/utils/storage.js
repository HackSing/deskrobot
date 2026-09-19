// 本地存储工具
const STORAGE_KEY = 'meeting_host_data';

export function saveMeetingData(data) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      ...data,
      savedAt: new Date().toISOString()
    }));
    return true;
  } catch (error) {
    console.error('保存失败:', error);
    return false;
  }
}

export function loadMeetingData() {
  try {
    const data = localStorage.getItem(STORAGE_KEY);
    return data ? JSON.parse(data) : null;
  } catch (error) {
    console.error('加载失败:', error);
    return null;
  }
}

export function clearMeetingData() {
  try {
    localStorage.removeItem(STORAGE_KEY);
    return true;
  } catch (error) {
    console.error('清除失败:', error);
    return false;
  }
}

export function exportToJSON(data, filename = 'meeting-summary.json') {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
