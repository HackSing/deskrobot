// 会议房间管理
const STORAGE_KEY_ROOM = 'meeting_room_data';

// 生成唯一的会议ID
export function generateMeetingId() {
  return 'meet_' + Math.random().toString(36).substr(2, 9) + Date.now().toString(36);
}

// 创建会议房间
export function createMeetingRoom(meetingData) {
  const meetingId = generateMeetingId();
  const room = {
    id: meetingId,
    name: meetingData.name,
    host: meetingData.host || '林悦',
    startTime: new Date().toISOString(),
    participants: [
      {
        id: 'host',
        name: meetingData.host || '林悦',
        role: '主持人',
        joinedAt: new Date().toISOString(),
        isHost: true,
        active: true
      }
    ],
    status: 'active'
  };

  localStorage.setItem(STORAGE_KEY_ROOM + '_' + meetingId, JSON.stringify(room));
  return { meetingId, room };
}

// 加入会议房间
export function joinMeetingRoom(meetingId, participantData) {
  const roomKey = STORAGE_KEY_ROOM + '_' + meetingId;
  const roomData = localStorage.getItem(roomKey);

  if (!roomData) {
    return { success: false, error: '会议不存在或已结束' };
  }

  const room = JSON.parse(roomData);

  // 检查是否已经加入
  const existing = room.participants.find(p => p.name === participantData.name);
  if (existing) {
    return { success: true, room, participantId: existing.id };
  }

  // 添加新参与者
  const participant = {
    id: 'user_' + Math.random().toString(36).substr(2, 9),
    name: participantData.name,
    role: participantData.role || '参会人',
    joinedAt: new Date().toISOString(),
    isHost: false,
    active: true
  };

  room.participants.push(participant);
  localStorage.setItem(roomKey, JSON.stringify(room));

  return { success: true, room, participantId: participant.id };
}

// 获取会议房间信息
export function getMeetingRoom(meetingId) {
  const roomKey = STORAGE_KEY_ROOM + '_' + meetingId;
  const roomData = localStorage.getItem(roomKey);

  if (!roomData) {
    return null;
  }

  return JSON.parse(roomData);
}

// 更新会议房间（用于实时同步参与者列表）
export function updateMeetingRoom(meetingId, updates) {
  const roomKey = STORAGE_KEY_ROOM + '_' + meetingId;
  const roomData = localStorage.getItem(roomKey);

  if (!roomData) {
    return false;
  }

  const room = JSON.parse(roomData);
  const updatedRoom = { ...room, ...updates };
  localStorage.setItem(roomKey, JSON.stringify(updatedRoom));

  return true;
}

// 结束会议
export function endMeetingRoom(meetingId) {
  const roomKey = STORAGE_KEY_ROOM + '_' + meetingId;
  const roomData = localStorage.getItem(roomKey);

  if (!roomData) {
    return false;
  }

  const room = JSON.parse(roomData);
  room.status = 'ended';
  room.endTime = new Date().toISOString();
  localStorage.setItem(roomKey, JSON.stringify(room));

  return true;
}

// 获取会议URL（包含局域网IP）
export function getMeetingUrl(meetingId) {
  const hostname = window.location.hostname;
  const port = window.location.port;
  const protocol = window.location.protocol;

  // 如果是localhost，尝试获取局域网IP（需要从Vite dev server日志中获取）
  const baseUrl = `${protocol}//${hostname}${port ? ':' + port : ''}`;
  return `${baseUrl}?join=${meetingId}`;
}

// 轮询检查会议房间更新（用于实时同步）
export function pollMeetingRoom(meetingId, callback, intervalMs = 2000) {
  const interval = setInterval(() => {
    const room = getMeetingRoom(meetingId);
    if (room) {
      callback(room);
    } else {
      clearInterval(interval);
    }
  }, intervalMs);

  return () => clearInterval(interval);
}
