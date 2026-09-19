// 生成参会人员头像
export function generateParticipantAvatar(name, size = 200) {
  const colors = [
    { bg: '#4b8053', text: '#fff' },
    { bg: '#5a9f6f', text: '#fff' },
    { bg: '#6eb584', text: '#fff' },
    { bg: '#7fc798', text: '#fff' },
    { bg: '#3d6b44', text: '#fff' },
    { bg: '#2e5a34', text: '#fff' },
  ];
  const initial = name.charAt(0);
  const color = colors[name.charCodeAt(0) % colors.length];

  return `data:image/svg+xml,${encodeURIComponent(`
    <svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
      <rect width="${size}" height="${size}" fill="${color.bg}"/>
      <text x="50%" y="50%" text-anchor="middle" dy="0.35em" fill="${color.text}" font-size="${size/2.5}" font-family="Arial, sans-serif" font-weight="600">${initial}</text>
    </svg>
  `)}`;
}

// 参会人员列表
export const participants = [
  { id: 1, name: '张涛', role: '项目负责人', active: true },
  { id: 2, name: '李娜', role: '开发工程师', active: true },
  { id: 3, name: '王强', role: '技术主管', active: true },
  { id: 4, name: '陈晨', role: '运营经理', active: true },
  { id: 5, name: '林悦', role: '产品经理', active: true },
];
