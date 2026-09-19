// 导出会议纪要工具

export function generateMeetingSummaryText(data) {
  const { name, date, duration, topics, lines, decisions, tasks, summary } = data;

  let text = `# ${name}\n\n`;
  text += `**日期**: ${date}\n`;
  text += `**时长**: ${duration} 分钟\n`;
  text += `**参会人数**: 5 人\n\n`;

  text += `## 会议目标\n\n`;
  topics.forEach((topic, i) => {
    text += `${i + 1}. ${topic}\n`;
  });

  text += `\n## AI 会议总结\n\n${summary}\n\n`;

  if (decisions && decisions.length > 0) {
    text += `## 关键结论\n\n`;
    decisions.forEach((decision, i) => {
      text += `${i + 1}. ${decision}\n`;
    });
    text += '\n';
  }

  if (tasks && tasks.length > 0) {
    text += `## 待办事项\n\n`;
    tasks.forEach(task => {
      const status = task.done ? '[x]' : '[ ]';
      text += `${status} ${task.text}\n`;
      text += `   - 负责人: ${task.owner}\n`;
      text += `   - 截止日期: ${task.date}\n\n`;
    });
  }

  if (lines && lines.length > 0) {
    text += `## 会议记录\n\n`;
    lines.forEach(([time, speaker, content]) => {
      text += `**${time}** ${speaker}: ${content}\n\n`;
    });
  }

  text += `\n---\n生成时间: ${new Date().toLocaleString('zh-CN')}\n`;

  return text;
}

export function downloadAsMarkdown(data, filename = 'meeting-summary.md') {
  const text = generateMeetingSummaryText(data);
  const blob = new Blob([text], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function downloadAsHTML(data, filename = 'meeting-summary.html') {
  const text = generateMeetingSummaryText(data);
  const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${data.name}</title>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      max-width: 800px;
      margin: 40px auto;
      padding: 20px;
      line-height: 1.6;
      color: #333;
    }
    h1, h2 { color: #2c5f2d; border-bottom: 2px solid #eee; padding-bottom: 10px; }
    h1 { font-size: 2em; }
    h2 { font-size: 1.5em; margin-top: 30px; }
    ul, ol { padding-left: 25px; }
    .meta { color: #666; font-size: 0.9em; }
    .task { margin: 15px 0; padding: 10px; background: #f9f9f9; border-left: 3px solid #4b8053; }
    .done { opacity: 0.6; text-decoration: line-through; }
    .transcript { margin: 10px 0; padding: 10px; background: #fafafa; }
    .speaker { font-weight: bold; color: #4b8053; }
    footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; color: #999; font-size: 0.85em; }
  </style>
</head>
<body>
  <h1>${data.name}</h1>
  <div class="meta">
    <p><strong>日期</strong>: ${data.date}</p>
    <p><strong>时长</strong>: ${data.duration} 分钟</p>
    <p><strong>参会人数</strong>: 5 人</p>
  </div>

  <h2>会议目标</h2>
  <ol>
    ${data.topics.map(t => `<li>${t}</li>`).join('\n    ')}
  </ol>

  <h2>AI 会议总结</h2>
  <p>${data.summary}</p>

  ${data.decisions && data.decisions.length > 0 ? `
  <h2>关键结论</h2>
  <ol>
    ${data.decisions.map(d => `<li>${d}</li>`).join('\n    ')}
  </ol>
  ` : ''}

  ${data.tasks && data.tasks.length > 0 ? `
  <h2>待办事项</h2>
  ${data.tasks.map(task => `
  <div class="task ${task.done ? 'done' : ''}">
    <div>${task.done ? '✓' : '○'} ${task.text}</div>
    <div style="margin-top: 5px; font-size: 0.9em; color: #666;">
      负责人: ${task.owner} | 截止日期: ${task.date}
    </div>
  </div>
  `).join('\n  ')}
  ` : ''}

  ${data.lines && data.lines.length > 0 ? `
  <h2>会议记录</h2>
  ${data.lines.map(([time, speaker, content]) => `
  <div class="transcript">
    <span class="speaker">${time} ${speaker}</span>: ${content}
  </div>
  `).join('\n  ')}
  ` : ''}

  <footer>
    生成时间: ${new Date().toLocaleString('zh-CN')}
  </footer>
</body>
</html>`;

  const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function copyToClipboard(data) {
  const text = generateMeetingSummaryText(data);
  return navigator.clipboard.writeText(text)
    .then(() => true)
    .catch(() => false);
}
