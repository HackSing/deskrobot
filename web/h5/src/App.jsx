import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  CalendarBlank, FileText, Folder, Gear, Clock, Paperclip, ArrowRight,
  CheckCircle, ListBullets, ChatText, Target, Microphone, VideoCamera,
  Monitor, Stop, PaperPlaneRight, BookmarkSimple, Lightbulb, X, ArrowLeft,
  Waveform, CaretRight, DownloadSimple, FloppyDisk, Copy, Trash, QrCode, Users
} from '@phosphor-icons/react';
import { QRCodeSVG } from 'qrcode.react';
import { generateAvatarSVG, generateRobotAvatarSVG } from './utils/avatars';
import { saveMeetingData, loadMeetingData, clearMeetingData, exportToJSON } from './utils/storage';
import { downloadAsMarkdown, downloadAsHTML, copyToClipboard } from './utils/export';
import { TranscriptSimulator } from './utils/transcript';
import { validateFile, formatTime, formatDate, debounce } from './utils/helpers';
import { participants as defaultParticipants, generateParticipantAvatar } from './utils/participants';
import {
  createMeetingRoom,
  joinMeetingRoom,
  getMeetingRoom,
  endMeetingRoom,
  getMeetingUrl,
  pollMeetingRoom
} from './utils/meetingRoom';
import { connect as connectBackend, toLine } from './utils/backend';

const lines = [
  ['14:01', '张涛', '我们先看一下上周的整体进展。'],
  ['14:03', '李娜', '核心功能开发已完成 80%，目前进入测试阶段。'],
  ['14:05', '王强', '关于上线时间，团队评估后，我们可以在本周五完成发布。'],
  ['14:06', '张涛', '好的，那就按本周五上线来推进。'],
  ['14:08', '陈晨', '运营这边会同步准备社区和推广内容。'],
  ['14:10', '李娜', '另外，下个版本的需求我们下周再评审。']
];

const initialTasks = [
  ['完成新版功能的技术方案评审', '张涛', '2026-09-23'],
  ['整理并分析用户反馈，输出优化方案', '李娜', '2026-09-24'],
  ['制定市场推广计划并同步资源', '王磊', '2026-09-25'],
  ['跟进性能测试结果，确认上线风险', '陈晨', '2026-09-25']
].map((x, i) => ({ id: i, text: x[0], owner: x[1], date: x[2], done: false }));

const defaultDecisions = [
  '确定新版功能于本周五上线，按计划推进开发、测试与灰度发布。',
  '同意启动用户反馈优化专项，优先解决高频问题，提升核心功能的稳定性和用户体验。'
];

const defaultSummary =
  '重点回顾了上周的开发进展与数据表现，讨论了新功能的上线计划和市场推广方案。整体进展符合预期，但需要在用户反馈优化和性能稳定性方面继续投入。团队对下阶段的工作重点达成一致。';

// 首页会前表单的初值。后端连上后由 /api/state 里的会前准备覆盖（见 applyPrep），
// 这里写的是后端演示模式预置的同一份数据（仓库 demo/seed.py），后端连不上时页面也是这一套。
const DEFAULT_PREP = {
  name: '供应商报价',
  agenda: '1. 对比三家供应商\n2. 定下一步动作',
  duration: 20,
  files: ['演示资料_供应商对比表.md']
};

const backendLabel = { ok: '已连接机器人后端 · 会议结束后自动显示纪要', poll: '机器人后端轮询中', off: '未连接机器人后端 · 模拟数据' };

const labels = ['会前准备', '会中主持', '会中助手', '会后确认与追踪'];

function Card({ title, icon: Icon, children, className = '' }) {
  return (
    <section className={'card ' + className}>
      {title && (
        <h3>
          {Icon && <Icon size={25} />}
          {title}
        </h3>
      )}
      {children}
    </section>
  );
}

function Badge({ children }) {
  return (
    <span className="badge">
      <span /> {children}
    </span>
  );
}

// 视频窗口组件
function VideoWindow({ participant, isSpeaking, isMuted }) {
  const avatar = generateParticipantAvatar(participant.name);
  return (
    <div className={`video-window ${isSpeaking ? 'speaking' : ''} ${isMuted ? 'muted' : ''} ${!participant.active ? 'inactive' : ''}`}>
      <img src={avatar} alt={participant.name} />
      <div className="video-name">{participant.name}</div>
      <div className="video-status" title={isMuted ? '已静音' : '音频开启'} />
    </div>
  );
}

export default function App() {
  const [page, P] = useState(0);
  const [name, N] = useState(DEFAULT_PREP.name);
  const [agenda, A] = useState(DEFAULT_PREP.agenda);
  const [duration, D] = useState(DEFAULT_PREP.duration);
  const [speakingParticipant, SP] = useState(0); // 当前发言者
  const [customDuration, CD] = useState('');
  const [files, F] = useState([...DEFAULT_PREP.files]);
  const [running, R] = useState(false);
  const [seconds, S] = useState(0);
  const [topic, T] = useState(1);
  const [question, Q] = useState('');
  const [messages, M] = useState([
    { q: '刚才最终确认的上线时间是什么？', a: '本次会议确认：新版本周五上线。', source: 2 }
  ]);
  const [thinking, B] = useState(false);
  const [points, H] = useState(['核心功能已完成 80%，进入测试阶段。', '下周评审下个版本需求。']);
  const [tasks, U] = useState(initialTasks);

  // 会议房间状态
  const [meetingId, MI] = useState(null);
  const [meetingUrl, MURL] = useState('');
  const [participants, PART] = useState(defaultParticipants);
  const [showQR, SQR] = useState(false);
  const [isJoining, IJ] = useState(false);
  const [joinName, JN] = useState('');
  const [joinRole, JR] = useState('');
  const pollInterval = useRef(null);
  const [confirmed, C] = useState(false);
  const [filter, V] = useState('全部');
  const [tab, TB] = useState('会中助手');
  const [muted, MU] = useState(false);
  const [video, VI] = useState(true);
  const [share, SH] = useState(false);
  const [toast, TO] = useState('');
  const [source, SO] = useState(-1);
  const [history, HI] = useState(false);
  const [reminder, RE] = useState(true);
  const [meetingDate] = useState(new Date());
  const [transcriptLines, TL] = useState(lines);
  const [fileError, FE] = useState('');
  const [autoSave, AS] = useState(true);

  // ---- 对接机器人后端：唯一的接口，会议结束后后端把纪要推过来（src/utils/backend.js）----
  const [decisions, DE] = useState(defaultDecisions);
  const [summary, SU] = useState('');
  const [openQuestions, OQ] = useState([]);
  const [backend, BK] = useState('off'); // ok / poll / off
  const appliedMinutes = useRef('');
  const prefilled = useRef(null);            // 上一次由后端会前准备填进表单的那份值，用来判断用户有没有自己改过
  const restoredFromStorage = useRef(false); // 用户选了“继续上次会议”，此后不再跟随后端会前准备
  const formNow = useRef({ page: 0, running: false, name: DEFAULT_PREP.name, agenda: DEFAULT_PREP.agenda, duration: DEFAULT_PREP.duration, files: [...DEFAULT_PREP.files] });

  const transcriptSimulator = useRef(null);

  // 初始化转写模拟器
  useEffect(() => {
    transcriptSimulator.current = new TranscriptSimulator(lines);
    return () => {
      if (transcriptSimulator.current) {
        transcriptSimulator.current.stop();
      }
    };
  }, []);

  // 计时器
  useEffect(() => {
    if (!running) return;
    const id = setInterval(() => S(x => x + 1), 1000);
    return () => clearInterval(id);
  }, [running]);

  // 模拟发言者切换
  useEffect(() => {
    if (!running) return;
    const id = setInterval(() => {
      SP(prev => (prev + 1) % participants.length);
    }, 5000); // 每5秒切换发言者
    return () => clearInterval(id);
  }, [running]);

  // Toast 自动消失
  useEffect(() => {
    if (toast) {
      const id = setTimeout(() => TO(''), 3000);
      return () => clearTimeout(id);
    }
  }, [toast]);

  // 自动保存
  const saveData = useCallback(
    debounce(() => {
      if (autoSave && page > 0) {
        const data = {
          page,
          name,
          agenda,
          duration,
          files,
          seconds,
          tasks,
          points,
          messages,
          confirmed,
          transcriptLines,
          decisions,
          summary,
          openQuestions,
          meetingDate: meetingDate.toISOString()
        };
        saveMeetingData(data);
      }
    }, 2000),
    [autoSave, page, name, agenda, duration, files, seconds, tasks, points, messages, confirmed, transcriptLines, decisions, summary, openQuestions]
  );

  useEffect(() => {
    saveData();
  }, [tasks, points, messages, confirmed, seconds]);

  // 加载保存的数据
  useEffect(() => {
    const saved = loadMeetingData();
    if (saved && window.confirm('检测到上次未完成的会议，是否继续？')) {
      restoredFromStorage.current = true; // 恢复出来的是用户自己的会议，别再被后端会前准备覆盖
      P(saved.page || 0);
      N(saved.name || DEFAULT_PREP.name);
      A(saved.agenda || agenda);
      D(saved.duration || DEFAULT_PREP.duration);
      F(saved.files || []);
      S(saved.seconds || 0);
      U(saved.tasks || initialTasks);
      H(saved.points || []);
      M(saved.messages || []);
      C(saved.confirmed || false);
      TL(saved.transcriptLines || lines);
      DE(saved.decisions || defaultDecisions);
      SU(saved.summary || '');
      OQ(saved.openQuestions || []);
    }
  }, []);

  // 订阅回调是挂载时建的闭包，读不到最新 state，首页表单的当前值放 ref 里给 applyPrep 用。
  useEffect(() => {
    formNow.current = { page, running, name, agenda, duration, files };
  });

  // 订阅后端快照。state 回到 idle 且 minutes 非空 = 会议已结束、纪要出来了：切到会后页显示真纪要。
  // 同一份纪要只应用一次；后端重启开新会后 meeting_id 变了会再次应用。
  useEffect(() => {
    return connectBackend(snap => {
      if (!snap) return;
      applyPrep(snap);
      if (snap.state !== 'idle' || !snap.minutes) return;
      const key = (snap.meeting_id || '') + JSON.stringify(snap.minutes);
      if (appliedMinutes.current === key) return;
      appliedMinutes.current = key;
      applyMinutes(snap);
    }, BK);
  }, []);

  // 后端快照的会前准备（project / agenda / total / materials）→ 首页表单。
  // 后端 /api/state 是会前准备的权威来源，页面只在还没开会、用户也没改过表单时跟着它走：
  // 一旦当前值和上次填进去的那份对不上（= 用户自己编辑过），就再也不覆盖。
  function applyPrep(snap) {
    const cur = formNow.current;
    if (cur.page !== 0 || cur.running || restoredFromStorage.current) return;
    if (!snap.project || snap.minutes) return; // 纪要已出的快照交给 applyMinutes
    const base = prefilled.current || DEFAULT_PREP;
    const same = (a, b) => a.length === b.length && a.every((x, i) => x === b[i]);
    if (cur.name !== base.name || cur.agenda !== base.agenda || cur.duration !== base.duration || !same(cur.files, base.files)) {
      return;
    }
    const next = {
      name: snap.project,
      agenda: snap.agenda && snap.agenda.length
        ? snap.agenda.map((a, i) => `${i + 1}. ${a.title}`).join(String.fromCharCode(10))
        : cur.agenda,
      duration: snap.total ? Math.max(1, Math.round(snap.total / 60)) : cur.duration,
      files: snap.materials || []
    };
    // WebSocket 每次后端状态变化都推一份完整快照，会前准备没变就别白白重渲染。
    if (next.name === cur.name && next.agenda === cur.agenda && next.duration === cur.duration && same(next.files, cur.files)) {
      prefilled.current = next;
      return;
    }
    prefilled.current = next;
    N(next.name);
    A(next.agenda);
    D(next.duration);
    F(next.files);
  }

  // 后端快照 → 页面状态。字段对照见仓库 docs/前端对接_纪要推送.md
  function applyMinutes(snap) {
    const m = snap.minutes;
    R(false);
    if (transcriptSimulator.current) transcriptSimulator.current.stop();
    if (snap.project) N(snap.project);
    if (snap.agenda && snap.agenda.length) A(snap.agenda.map((a, i) => `${i + 1}. ${a.title}`).join(String.fromCharCode(10)));
    if (snap.total) D(Math.max(1, Math.round(snap.total / 60)));
    if (snap.transcript && snap.transcript.length) TL(snap.transcript.map(toLine));
    DE(m.conclusions || []);
    H(m.highlights || []);
    OQ(m.open_questions || []);
    SU((m.highlights || []).join(''));
    U(
      (m.todos || []).map((t, i) => ({
        id: i,
        text: t.content || '',
        owner: t.owner || '',
        date: t.due || '',
        done: t.status === 'done',
        confirmed: !!t.confirmed
      }))
    );
    C(false);
    TO('已收到机器人推送的会议纪要');
    go(3);
  }

  // 检查URL参数，处理加入会议
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const joinMeetingId = params.get('join');

    if (joinMeetingId) {
      const room = getMeetingRoom(joinMeetingId);
      if (room && room.status === 'active') {
        IJ(true);
        MI(joinMeetingId);
      } else {
        TO('会议不存在或已结束');
      }
    }
  }, []);

  // 轮询会议房间更新（实时同步参与者）
  useEffect(() => {
    if (!meetingId || !running) return;

    const stopPolling = pollMeetingRoom(meetingId, (room) => {
      if (room && room.participants) {
        // 更新参与者列表
        const updatedParticipants = room.participants.map(p => ({
          id: p.id,
          name: p.name,
          role: p.role,
          active: p.active,
          isHost: p.isHost
        }));
        PART(updatedParticipants);
      }
    });

    pollInterval.current = stopPolling;

    return () => {
      if (pollInterval.current) {
        pollInterval.current();
      }
    };
  }, [meetingId, running]);

  const topics = agenda.split('\n').filter(Boolean);
  const fmt = n => formatTime(n);

  const go = i => {
    P(i);
    window.scrollTo(0, 0);
  };

  const start = () => {
    R(true);
    S(0);
    T(0);
    C(false);
    TL([]);

    // 创建会议房间
    const { meetingId: newMeetingId, room } = createMeetingRoom({
      name,
      host: '林悦'
    });
    MI(newMeetingId);

    // 生成会议URL
    const url = getMeetingUrl(newMeetingId);
    MURL(url);

    // 初始化参与者（主持人）
    PART(room.participants);

    TO('会议已创建，可以分享二维码邀请他人加入');

    if (transcriptSimulator.current) {
      transcriptSimulator.current.reset();
      transcriptSimulator.current.start(3000);
      transcriptSimulator.current.addListener(newLines => {
        TL(newLines);
      });
    }
    go(1);
  };

  const end = () => {
    R(false);
    if (transcriptSimulator.current) {
      transcriptSimulator.current.stop();
    }

    // 结束会议房间
    if (meetingId) {
      endMeetingRoom(meetingId);
    }

    go(3);
  };

  // 处理加入会议
  const handleJoinMeeting = (e) => {
    e.preventDefault();

    if (!joinName.trim()) {
      TO('请输入你的姓名');
      return;
    }

    const result = joinMeetingRoom(meetingId, {
      name: joinName.trim(),
      role: joinRole.trim() || '参会人'
    });

    if (result.success) {
      TO(`${joinName} 已加入会议`);
      IJ(false);

      // 更新本地参与者列表
      const room = getMeetingRoom(meetingId);
      if (room) {
        PART(room.participants);

        // 如果会议正在进行，直接进入会议页面
        if (room.status === 'active') {
          R(true);
          N(room.name);
          go(1);
        }
      }
    } else {
      TO(result.error || '加入会议失败');
    }
  };

  const addFiles = e => {
    const fileList = Array.from(e);
    const errors = [];
    const validFiles = [];

    fileList.forEach(file => {
      const validation = validateFile(file);
      if (validation.valid) {
        validFiles.push(file.name);
      } else {
        errors.push(validation.error);
      }
    });

    if (errors.length > 0) {
      FE(errors[0]);
      setTimeout(() => FE(''), 5000);
    }

    if (validFiles.length > 0) {
      F(x => [...x, ...validFiles]);
      TO(`已添加 ${validFiles.length} 个文件`);
    }
  };

  const mark = () => {
    const value = messages.at(-1)?.a || lines[2][2];
    H(x => (x.includes(value) ? x : [value, ...x]));
    TO('已为你记录为会议重点');
  };

  function ask(e) {
    e.preventDefault();
    if (!question.trim() || thinking) return;
    const q = question.trim();
    Q('');
    B(true);
    M(x => [...x, { q, a: null }]);
    setTimeout(() => {
      const idx = /进度|进展|完成/.test(q)
        ? 1
        : /需求|下周/.test(q)
        ? 5
        : /推广|运营/.test(q)
        ? 4
        : /上线|发布|时间/.test(q)
        ? 2
        : -1;
      M(x =>
        x.map((m, i) =>
          i === x.length - 1
            ? {
                ...m,
                a:
                  idx < 0
                    ? '当前模拟会议记录中没有足够信息回答这个问题。你可以问我上线时间、开发进度或推广安排。'
                    : lines[idx][2],
                source: idx
              }
            : m
        )
      );
      B(false);
    }, 850);
  }

  const handleExport = format => {
    const data = {
      name,
      date: formatDate(meetingDate).full,
      duration,
      topics,
      lines: transcriptLines,
      decisions,
      tasks,
      summary: summary || '本次' + name + defaultSummary
    };

    switch (format) {
      case 'markdown':
        downloadAsMarkdown(data, `${name}-${formatDate(meetingDate).date}.md`);
        TO('已导出为 Markdown 文件');
        break;
      case 'html':
        downloadAsHTML(data, `${name}-${formatDate(meetingDate).date}.html`);
        TO('已导出为 HTML 文件');
        break;
      case 'json':
        exportToJSON(data, `${name}-${formatDate(meetingDate).date}.json`);
        TO('已导出为 JSON 文件');
        break;
      case 'copy':
        copyToClipboard(data).then(success => {
          TO(success ? '已复制到剪贴板' : '复制失败，请重试');
        });
        break;
      default:
        break;
    }
  };

  const handleClearData = () => {
    if (window.confirm('确定要清除所有保存的会议数据吗？此操作不可恢复。')) {
      clearMeetingData();
      TO('已清除所有保存的数据');
    }
  };

  const addNewTask = () => {
    const newTask = {
      id: tasks.length,
      text: '新待办事项',
      owner: '待分配',
      date: formatDate(new Date(Date.now() + 86400000)).date,
      done: false
    };
    U(x => [...x, newTask]);
    TO('已添加新待办事项');
  };

  const deleteTask = id => {
    if (window.confirm('确定要删除这个待办事项吗？')) {
      U(x => x.filter(t => t.id !== id));
      TO('已删除待办事项');
    }
  };

  const userAvatar = generateAvatarSVG('林悦');
  const robotAvatar = generateRobotAvatarSVG();

  const taskList = (
    <>
      <div className="section-head">
        <h3>
          <CheckCircle size={25} />
          待办事项（{tasks.length}）
        </h3>
        <select aria-label="筛选待办" value={filter} onChange={e => V(e.target.value)}>
          {['全部', '待办', '已完成'].map(s => (
            <option key={s}>{s}</option>
          ))}
        </select>
      </div>
      {tasks
        .filter(t => filter === '全部' || t.done === (filter === '已完成'))
        .map(t => (
          <div className={'task ' + (t.done ? 'done' : '')} key={t.id}>
            <input
              aria-label={'完成：' + t.text}
              type="checkbox"
              checked={t.done}
              onChange={() => U(x => x.map(a => (a.id === t.id ? { ...a, done: !a.done } : a)))}
            />
            <input
              aria-label={'任务内容：' + t.text}
              value={t.text}
              onChange={e => U(x => x.map(a => (a.id === t.id ? { ...a, text: e.target.value } : a)))}
              style={{ flex: 1, border: 'none', background: 'transparent' }}
            />
            <input
              aria-label={'负责人：' + t.text}
              value={t.owner}
              onChange={e => U(x => x.map(a => (a.id === t.id ? { ...a, owner: e.target.value } : a)))}
            />
            <input
              aria-label={'截止日期：' + t.text}
              type="text"
              className="due"
              placeholder="截止"
              value={t.date}
              onChange={e => U(x => x.map(a => (a.id === t.id ? { ...a, date: e.target.value } : a)))}
            />
            <small>{t.done ? '已完成' : t.confirmed ? '已拍背确认' : '待办'}</small>
            <button
              type="button"
              aria-label="删除待办"
              onClick={() => deleteTask(t.id)}
              style={{ padding: '4px' }}
            >
              <Trash size={16} />
            </button>
          </div>
        ))}
      <button className="green" onClick={addNewTask} style={{ marginTop: '10px', width: '100%' }}>
        + 添加待办事项
      </button>
    </>
  );

  const transcript = (
    <Card title="实时记录">
      {running && <span className="live-caption">AI 实时整理中…</span>}
      <div className="transcript">
        {transcriptLines.map((l, i) => (
          <button
            key={i}
            className={'transcript-row ' + (source === i ? 'highlight' : '')}
            onClick={() => SO(i)}
          >
            <time>{l[0]}</time>
            <b>{l[1]}</b>
            <span>{l[2]}</span>
          </button>
        ))}
      </div>
      <div className="listening">
        <Waveform size={23} />
        {running ? '正在聆听会议内容…' : '会议记录已保存'} <small>模拟逐字稿</small>
      </div>
    </Card>
  );

  // 如果是加入会议模式，显示加入表单
  if (isJoining) {
    const room = getMeetingRoom(meetingId);
    return (
      <div className="shell">
        <div className="join-form">
          <h2>加入会议</h2>
          {room && (
            <div className="meeting-info">
              <strong>{room.name}</strong>
              主持人: {room.host}
              <br />
              参会人数: {room.participants.length}
            </div>
          )}
          <form onSubmit={handleJoinMeeting}>
            <label>
              你的姓名 *
              <input
                type="text"
                value={joinName}
                onChange={e => JN(e.target.value)}
                placeholder="请输入你的姓名"
                required
              />
            </label>
            <label>
              你的角色
              <input
                type="text"
                value={joinRole}
                onChange={e => JR(e.target.value)}
                placeholder="如：产品经理、开发工程师（可选）"
              />
            </label>
            <button type="submit" className="join-button">
              加入会议
            </button>
          </form>
        </div>
        {toast && (
          <div role="status" aria-live="polite" className="toast">
            <CheckCircle />
            {toast}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="window-dots">
          <i />
          <i />
          <i />
        </div>
        <div className="brand">
          会议主持机器人
          <small>Meeting Host</small>
        </div>
        <nav>
          <button className={page < 3 ? 'active' : ''} onClick={() => go(running ? 1 : 0)}>
            <CalendarBlank />
            会议
          </button>
          <button className={page === 3 ? 'active' : ''} onClick={() => go(3)}>
            <FileText />
            记录
          </button>
          <button
            onClick={() => {
              go(3);
              TO('项目待办已显示，可更新负责人和截止时间');
            }}
          >
            <Folder />
            项目
          </button>
          <hr />
          <button onClick={() => TO('当前使用默认配置：中文 · 自动纪要 · 剩余 5 分钟提醒')}>
            <Gear />
            设置
          </button>
        </nav>
        <div className="profile">
          <img src={userAvatar} alt="用户头像" />
          <div>
            林悦
            <small>产品团队</small>
          </div>
          <CaretRight size={18} />
        </div>
      </aside>
      <main>
        <div className="breadcrumb">
          会议 <span>/</span>
          <b>{labels[page]}</b>
        </div>
        <div className="columns">
          <div className="primary">
            <header>
              <div className="title-row">
                <h1>{page === 0 ? '准备一场会议' : name}</h1>
                {(page === 1 || page === 2) && <Badge>{running ? '会议进行中' : '会议已结束'}</Badge>}
                {page === 2 && running && (
                  <button className="danger light" onClick={end}>
                    <Stop />
                    结束会议
                  </button>
                )}
              </div>
              {page === 0 ? (
                <p className="intro">告诉我这次会议的基本信息，会议主持机器人将为你做好准备。</p>
              ) : (
                <p className="meta">
                  {formatDate(meetingDate).full}
                  {page === 3 ? `| ${fmt(seconds)} | 5 位参会人` : ' · 5 位参会人'}
                </p>
              )}
              {page === 1 && (
                <div className="timer">
                  <strong>{fmt(seconds)}</strong>
                  <span> / {fmt(duration * 60)}</span>
                  <progress value={seconds} max={duration * 60} />
                </div>
              )}
            </header>

            {page === 0 && (
              <>
                <form
                  className="card preparation"
                  onSubmit={e => {
                    e.preventDefault();
                    start();
                  }}
                >
                  <label>
                    会议名称
                    <input
                      required
                      maxLength={50}
                      value={name}
                      onChange={e => N(e.target.value)}
                      placeholder="为会议起个名字"
                    />
                  </label>
                  <small className="counter">{name.length}/50</small>
                  <label>
                    会议目标 / 议程
                    <textarea required maxLength={500} value={agenda} onChange={e => A(e.target.value)} />
                  </label>
                  <small className="counter">{agenda.length}/500</small>
                  <label>
                    预计时长
                    <div style={{ display: 'flex', gap: '10px', marginTop: '8px' }}>
                      <select
                        value={duration}
                        onChange={e => {
                          const val = Number(e.target.value);
                          if (val === 0) {
                            CD('');
                          } else {
                            D(val);
                            CD('');
                          }
                        }}
                      >
                        {/* 后端议程加起来可能不是预设档位（演示数据是 20 分钟），补一档进去免得选框空着 */}
                        {[...new Set([5, 15, 30, 45, 60, 90, 120, duration].filter(v => v > 0))]
                          .sort((a, b) => a - b)
                          .map(v => (
                            <option key={v} value={v}>
                              {v} 分钟
                            </option>
                          ))}
                        <option value={0}>自定义</option>
                      </select>
                      {duration === 0 && (
                        <input
                          type="number"
                          min="5"
                          max="240"
                          value={customDuration}
                          onChange={e => {
                            CD(e.target.value);
                            const val = Number(e.target.value);
                            if (val >= 5 && val <= 240) {
                              D(val);
                            }
                          }}
                          placeholder="输入分钟数"
                          style={{ width: '120px' }}
                        />
                      )}
                    </div>
                  </label>
                  <label className="upload-label">上传资料（可选）</label>
                  <div
                    className="upload"
                    onDragOver={e => e.preventDefault()}
                    onDrop={e => {
                      e.preventDefault();
                      addFiles(e.dataTransfer.files);
                    }}
                  >
                    <label className="upload-trigger">
                      <FileText size={27} />
                      点击上传文件或拖拽到此处
                      <input
                        type="file"
                        multiple
                        accept=".pdf,.doc,.docx,.ppt,.pptx,.png,.jpg,.txt"
                        onChange={e => addFiles(e.target.files)}
                      />
                    </label>
                    <p>支持 PDF、Docs、PPT、图片等格式，单个文件不超过 10MB</p>
                    {fileError && <p style={{ color: '#ef6260', fontSize: '14px' }}>{fileError}</p>}
                    {files.map((f, i) => (
                      <span className="file" key={i}>
                        <FileText size={20} />
                        {f}
                        <button
                          type="button"
                          aria-label={'移除 ' + f}
                          onClick={() => F(x => x.filter((_, n) => n !== i))}
                        >
                          <X size={17} />
                        </button>
                      </span>
                    ))}
                  </div>
                  <button className="green start" type="submit">
                    开始这场会议 <ArrowRight size={23} />
                  </button>
                </form>
                {history && (
                  <Card title="上次会议未完成事项" icon={Clock}>
                    {tasks.filter(t => !t.done).map(t => (
                      <p key={t.id}>
                        {t.text} · {t.owner}
                      </p>
                    ))}
                  </Card>
                )}
              </>
            )}

            {page === 1 && (
              <>
                {video && (
                  <Card title="参会人员" icon={VideoCamera}>
                    <div className="video-grid">
                      {participants.map((p, i) => (
                        <VideoWindow
                          key={p.id}
                          participant={p}
                          isSpeaking={i === speakingParticipant}
                          isMuted={muted && p.name === '林悦'}
                        />
                      ))}
                    </div>
                  </Card>
                )}
                <Card>
                  <div className="goal">
                    <Target size={29} />
                    <div>
                      <h3>会议目标</h3>
                      <p>{topics.slice(0, 3).join('　')}</p>
                    </div>
                  </div>
                  <div className="current">
                    <ListBullets size={29} />
                    <div>
                      <h3>当前议题</h3>
                      <strong>{topics[topic] || '确认会议结论'}</strong>
                      <p>讨论各模块的工作安排、资源需求和风险点。</p>
                    </div>
                  </div>
                </Card>
                <Card title="实时会议记录" icon={FileText}>
                  {running && <span className="live-caption">AI 实时整理中…</span>}
                  <div className="timeline">
                    {transcriptLines.filter((_, i) => [0, 1, 4].includes(i)).map(l => (
                      <div key={l[0]}>
                        <time>{l[0]}</time>
                        <b>{l[1]}</b>
                        <p>{l[2]}</p>
                      </div>
                    ))}
                  </div>
                  <div className="listening">
                    <Waveform />
                    {muted ? '麦克风已静音 · 演示记录继续播放' : '机器人正在聆听并记录会议内容…'}
                  </div>
                </Card>
                {duration * 60 - seconds <= 300 && reminder && (
                  <div className="notice">
                    <Clock size={30} />
                    <div>
                      <b>
                        {seconds >= duration * 60
                          ? '会议已超时，建议确认结论'
                          : '还有不到 5 分钟，建议开始确认结论'}
                      </b>
                      <p>可围绕待办事项、负责人和时间节点进行总结。</p>
                    </div>
                    <button onClick={() => RE(false)} aria-label="关闭提醒">
                      <X />
                    </button>
                  </div>
                )}
                <div className="meeting-controls">
                  <button onClick={() => MU(!muted)}>
                    <Microphone />
                    {muted ? '取消静音' : '静音'}
                  </button>
                  <button onClick={() => VI(!video)}>
                    <VideoCamera />
                    {video ? '关闭视频' : '开启视频'}
                  </button>
                  <button onClick={() => SH(!share)}>
                    <Monitor />
                    {share ? '停止共享' : '共享屏幕'}
                  </button>
                  <button className="green" onClick={() => go(2)}>
                    <ChatText />
                    向会议提问
                  </button>
                  <button className="danger" onClick={end}>
                    <Stop />
                    结束会议
                  </button>
                </div>
                {share && <p className="muted">正在模拟共享屏幕</p>}
              </>
            )}

            {page === 2 && (
              <>
                <div className="tabs">
                  {['会中助手', '会议记录', '待办事项', '会议资料'].map(t => (
                    <button className={tab === t ? 'selected' : ''} key={t} onClick={() => TB(t)}>
                      {t}
                    </button>
                  ))}
                  <button onClick={() => go(running ? 1 : 3)}>
                    <ArrowLeft size={17} />
                    {running ? '返回主持' : '返回总结'}
                  </button>
                </div>
                {(tab === '会中助手' || tab === '会议记录') && transcript}
                {tab === '待办事项' && <Card>{taskList}</Card>}
                {tab === '会议资料' && (
                  <Card title="会议资料" icon={Paperclip}>
                    {files.length ? (
                      files.map((f, i) => (
                        <p className="file" key={i}>
                          <FileText />
                          {f}
                        </p>
                      ))
                    ) : (
                      <p>还没有上传资料</p>
                    )}
                    <p className="muted">演示资料仅用于展示文件列表。</p>
                  </Card>
                )}
                {tab === '会中助手' && (
                  <Card title="向会议提问" className="chat">
                    <div className="messages">
                      {messages.map((m, i) => (
                        <React.Fragment key={i}>
                          <div className="question">
                            <span>{m.q}</span>
                            <img src={userAvatar} alt="用户" />
                          </div>
                          <div className="answer">
                            <img src={robotAvatar} alt="机器人" />
                            <div>
                              <b>{m.a || '正在整理会议内容…'}</b>
                              {m.source >= 0 && (
                                <button className="source" onClick={() => SO(m.source)}>
                                  来源：本场会议记录（{lines[m.source][0]}）
                                  <CaretRight size={14} />
                                </button>
                              )}
                            </div>
                          </div>
                        </React.Fragment>
                      ))}
                    </div>
                    <button className="save-point" onClick={mark}>
                      <BookmarkSimple size={18} />
                      记一下这个重点
                    </button>
                    <form className="ask" onSubmit={ask}>
                      <Paperclip size={23} />
                      <input
                        aria-label="向会议提问"
                        value={question}
                        onChange={e => Q(e.target.value)}
                        placeholder="向会议提问…"
                      />
                      <button className="green" disabled={thinking || !question.trim()} aria-label="发送问题">
                        <PaperPlaneRight size={23} />
                      </button>
                    </form>
                  </Card>
                )}
              </>
            )}

            {page === 3 && (
              <>
                <div className="notice">
                  <CheckCircle size={38} weight="fill" />
                  <div>
                    <b>{confirmed ? '待办已确认' : '会议纪要已生成，请确认待办'}</b>
                    <p>
                      {confirmed
                        ? '会议内容与待办已保留在本次演示中。'
                        : '核对负责人和截止时间，让讨论成为下一步行动。'}
                    </p>
                  </div>
                  {!confirmed && (
                    <button className="green" onClick={() => C(true)}>
                      确认待办
                    </button>
                  )}
                </div>

                <Card title="AI 会议总结" icon={FileText}>
                  <p className="summary">{summary || '本次' + name + defaultSummary}</p>
                </Card>

                <Card title="关键结论" icon={Lightbulb}>
                  {decisions.map((d, i) => (
                    <div className="decision" key={i}>
                      <span>{i + 1}</span>
                      <p>{d}</p>
                    </div>
                  ))}
                </Card>

                {openQuestions.length > 0 && (
                  <Card title="未决问题" icon={ChatText}>
                    {openQuestions.map((d, i) => (
                      <div className="decision" key={i}>
                        <span>?</span>
                        <p>{d}</p>
                      </div>
                    ))}
                  </Card>
                )}

                <Card>{taskList}</Card>

                <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginTop: '15px' }}>
                  <button className="green" onClick={() => handleExport('markdown')}>
                    <DownloadSimple />
                    导出 Markdown
                  </button>
                  <button className="green" onClick={() => handleExport('html')}>
                    <DownloadSimple />
                    导出 HTML
                  </button>
                  <button className="green" onClick={() => handleExport('json')}>
                    <FloppyDisk />
                    导出 JSON
                  </button>
                  <button className="green" onClick={() => handleExport('copy')}>
                    <Copy />
                    复制到剪贴板
                  </button>
                </div>

                <button
                  className="text-link"
                  onClick={() => {
                    TB('会议记录');
                    go(2);
                  }}
                  style={{ marginTop: '15px' }}
                >
                  查看完整会议记录 <ArrowRight />
                </button>
              </>
            )}
          </div>
          <aside className="right">
            <Card className="robot-card">
              <div className="section-head">
                <h3>会议主持机器人</h3>
                <Badge>
                  {
                    ['待机', muted ? '已静音' : '正在聆听', thinking ? '正在思考' : '可随时回答', '已整理完成'][
                      page
                    ]
                  }
                </Badge>
              </div>
              <img className="robot" src={robotAvatar} alt="白色圆润机器人，绿色微笑表情" />
              <p>
                {['我已准备就绪，', '我正在专注聆听，', '我正在听会，', '我已完成会议的整理与待办提取，'][page]}
                <br />
                {
                  [
                    '可以在会议中为你记录、总结和跟进行动项。',
                    '实时记录会议内容，并在合适的时机给出提醒。',
                    '可以随时向我提问、总结或记录重点。',
                    '相关内容已保留在本次演示中。'
                  ][page]
                }
              </p>
            </Card>

            {page === 0 && (
              <Card title="本次只做最少配置">
                {[
                  [ChatText, '会议名称', name],
                  [ListBullets, '会议目标 / 议程', topics.length + ' 个要点'],
                  [Clock, '预计时长', duration + ' 分钟'],
                  [Paperclip, '上传资料', files.length + ' 个文件']
                ].map(([Icon, t, v]) => (
                  <div className="info" key={t}>
                    <Icon />
                    <div>
                      {t}
                      <small>{v}</small>
                    </div>
                  </div>
                ))}
                <div className="notice compact">
                  <CheckCircle size={31} weight="fill" />
                  <div>
                    其他设置将使用默认配置
                    <small>你可以在会议中随时调整。</small>
                  </div>
                </div>
              </Card>
            )}

            {page === 1 && (
              <>
                <Card title="会议数据">
                  <button
                    className="data-row"
                    onClick={() => {
                      go(2);
                      TB('会中助手');
                    }}
                  >
                    <FileText />
                    已记录结论 <strong>{points.length}</strong>
                    <CaretRight />
                  </button>
                  <button
                    className="data-row"
                    onClick={() => {
                      go(2);
                      TB('待办事项');
                    }}
                  >
                    <CheckCircle />
                    待办草稿<strong>{tasks.length}</strong>
                    <CaretRight />
                  </button>
                </Card>

                {/* 二维码和参与者 */}
                <Card title="邀请参会" icon={QrCode}>
                  <button
                    className="green"
                    onClick={() => SQR(!showQR)}
                    style={{ width: '100%', marginBottom: '10px' }}
                  >
                    {showQR ? '隐藏' : '显示'}二维码
                  </button>

                  {showQR && meetingUrl && (
                    <div className="qr-card">
                      <div className="qr-code">
                        <QRCodeSVG value={meetingUrl} size={180} />
                      </div>
                      <div className="meeting-id">会议 ID: {meetingId?.slice(-8)}</div>
                      <p className="qr-info">
                        扫描二维码或访问链接加入会议
                      </p>
                      <div className="qr-url">{meetingUrl}</div>
                    </div>
                  )}

                  <div style={{ marginTop: '15px', fontSize: '14px', fontWeight: '600', color: '#4b5361' }}>
                    <Users size={18} style={{ marginRight: '6px', verticalAlign: 'middle' }} />
                    参会人员 ({participants.length})
                  </div>
                  <div className="participants-list">
                    {participants.map(p => (
                      <div key={p.id} className="participant-item">
                        <img src={generateParticipantAvatar(p.name)} alt={p.name} />
                        <div className="info">
                          <div className="name">{p.name}</div>
                          <div className="role">{p.role}</div>
                        </div>
                        {p.isHost && <span className="badge-host">主持人</span>}
                      </div>
                    ))}
                  </div>
                </Card>

                <Card title="当前会议进度">
                  {topics.map((t, i) => (
                    <button key={i} className={'topic ' + (topic === i ? 'current' : '')} onClick={() => T(i)}>
                      <CheckCircle size={23} weight={i <= topic ? 'fill' : 'regular'} />
                      {t}
                    </button>
                  ))}
                </Card>
              </>
            )}

            {page === 2 && (
              <>
                <Card title="答案来源">
                  {[
                    [CalendarBlank, '本场会议', '基于实时记录生成'],
                    [FileText, '会议资料', `已上传 ${files.length} 个文件`],
                    [Clock, '历史会议', '参考过往相关会议']
                  ].map(([Icon, t, v], i) => (
                    <button
                      key={t}
                      className={'info source-info ' + (i === 0 ? 'current' : '')}
                      onClick={() => {
                        if (i === 0) {
                          TB('会议记录');
                          SO(messages.at(-1)?.source ?? 2);
                        } else if (i === 1) TB('会议资料');
                        else TO('演示中暂无可检索的历史会议');
                      }}
                    >
                      <Icon />
                      <div>
                        {t}
                        <small>{v}</small>
                      </div>
                    </button>
                  ))}
                </Card>
                <Card title="最近记录的重点">
                  {points.map((p, i) => (
                    <div className={'point ' + (i === 0 ? 'current' : '')} key={p}>
                      <BookmarkSimple size={20} />
                      <div>
                        {p}
                        <small>
                          {i === 0 ? '刚刚' : '14:03'} · 来自本场会议
                        </small>
                      </div>
                    </div>
                  ))}
                </Card>
              </>
            )}

            {page === 3 && (
              <Card title="下次会议追踪" icon={Clock}>
                <p className="muted">来自本次会议的未完成事项（{tasks.filter(t => !t.done).length}）</p>
                {tasks.filter(t => !t.done).map(t => (
                  <div className="follow-task" key={t.id}>
                    <b>{t.text}</b>
                    <small>
                      负责人：{t.owner}
                      <br />
                      截止 {t.date}
                    </small>
                  </div>
                ))}
                {tasks.every(t => t.done) && <p>所有事项已完成，下次会议可以轻松开始。</p>}
                <button
                  className="next-meeting"
                  onClick={() => {
                    HI(true);
                    go(0);
                  }}
                >
                  这些事项将自动带入下次会议
                  <br />
                  准备下一次会议 <CaretRight />
                </button>
                <button
                  onClick={handleClearData}
                  style={{
                    marginTop: '10px',
                    width: '100%',
                    fontSize: '13px',
                    color: '#ef6260',
                    padding: '8px'
                  }}
                >
                  <Trash size={16} />
                  清除所有保存的数据
                </button>
              </Card>
            )}
          </aside>
        </div>
        <footer className="flow">
          {labels.map((l, i) => (
            <button
              key={l}
              className={page === i ? 'selected' : ''}
              onClick={() => {
                if (i === 3 && running) end();
                else go(i);
              }}
            >
              {String(i + 1).padStart(2, '0')} {l}
            </button>
          ))}
          <span>{backendLabel[backend]}</span>
        </footer>
      </main>
      {toast && (
        <div role="status" aria-live="polite" className="toast">
          <CheckCircle />
          {toast}
        </div>
      )}
    </div>
  );
}

export { App };
