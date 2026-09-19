// 与机器人后端（仓库根目录 web/server.py）的对接。只做一件事：
// 订阅后端快照，会议结束后把纪要交给页面显示。其余页面逻辑不碰。
//
// 地址：默认同源。
//   - 构建产物（npm run build → ../static/h5）由后端挂在 http://<后端IP>:8766/h5/ 下，同源。
//   - npm run dev 时 vite 把 /api、/ws 代理到后端（vite.config.mjs 的 VITE_BACKEND）。
//   - 前端跑在别的机器上想直连后端，打开页面时带参数：?api=http://192.168.1.8:8766
//     或者 VITE_API_BASE=http://192.168.1.8:8766 npm run dev
const params = new URLSearchParams(window.location.search);
export const API_BASE = (params.get('api') || import.meta.env.VITE_API_BASE || '').replace(/\/+$/, '');

function wsUrl() {
  const base = API_BASE || window.location.origin;
  return base.replace(/^http/, 'ws') + '/ws';
}

// 完整快照，和 /ws 推的是同一份东西。字段见仓库 docs/前端对接_纪要推送.md
export async function getState() {
  const r = await fetch(API_BASE + '/api/state', { cache: 'no-store' });
  if (!r.ok) throw new Error('HTTP ' + r.status);
  return r.json();
}

// 订阅快照。WebSocket 连上先收一条完整快照，之后后端状态每变一次再推一条完整快照（不是增量）。
// 断了就每 3 秒拉一次 /api/state 兜底，同时不断重连。
// onStatus 收到：'ok' 已连接 | 'poll' 轮询兜底中 | 'off' 连不上
// 返回一个函数，调用即退订。
export function connect(onSnapshot, onStatus = () => {}) {
  let ws = null;
  let closed = false;
  let retry = null;
  let poll = null;

  const handle = snap => {
    try {
      onSnapshot(snap);
    } catch (e) {
      console.error('处理后端快照失败', e);
    }
  };
  const startPoll = () => {
    if (poll) return;
    poll = setInterval(() => {
      getState()
        .then(s => {
          onStatus('poll');
          handle(s);
        })
        .catch(() => onStatus('off'));
    }, 3000);
  };
  const stopPoll = () => {
    if (poll) {
      clearInterval(poll);
      poll = null;
    }
  };
  const open = () => {
    if (closed) return;
    try {
      ws = new WebSocket(wsUrl());
    } catch {
      onStatus('off');
      startPoll();
      retry = setTimeout(open, 3000);
      return;
    }
    ws.onopen = () => {
      onStatus('ok');
      stopPoll();
    };
    ws.onmessage = e => {
      try {
        handle(JSON.parse(e.data));
      } catch {
        /* 坏包忽略 */
      }
    };
    ws.onerror = () => {
      try {
        ws.close();
      } catch {
        /* 已关 */
      }
    };
    ws.onclose = () => {
      if (closed) return;
      if (!poll) onStatus('off'); // 轮询已经在跑就别把状态打回 off，轮询自己会报 poll / off
      startPoll();
      retry = setTimeout(open, 3000);
    };
  };

  // 页面刚打开时会议可能已经结束了，先拉一次
  getState().then(handle).catch(() => {});
  open();

  return () => {
    closed = true;
    clearTimeout(retry);
    stopPoll();
    try {
      ws && ws.close();
    } catch {
      /* 已关 */
    }
  };
}

// 后端的一句转写 {text, ts} → 页面的一行 [时间, 发言人, 内容]。
// 后端预置的会议记录格式是“张三：……”；叫机器人的指令没有发言人前缀。
export function toLine(u) {
  const d = new Date((u.ts || 0) * 1000);
  const hhmm = u.ts ? `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}` : '';
  const m = /^([^：:，,。\s]{1,6})[：:]\s*([\s\S]+)$/.exec(u.text || '');
  return m ? [hhmm, m[1], m[2]] : [hhmm, '', u.text || ''];
}
