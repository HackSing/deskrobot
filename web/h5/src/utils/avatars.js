// 生成占位头像的 SVG
export function generateAvatarSVG(name = '林悦', size = 200) {
  const initial = name.charAt(0);
  const colors = [
    { bg: '#4b8053', text: '#fff' },
    { bg: '#5a9f6f', text: '#fff' },
    { bg: '#6eb584', text: '#fff' },
    { bg: '#7fc798', text: '#fff' },
  ];
  const color = colors[name.charCodeAt(0) % colors.length];

  return `data:image/svg+xml,${encodeURIComponent(`
    <svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
      <circle cx="${size/2}" cy="${size/2}" r="${size/2}" fill="${color.bg}"/>
      <text x="50%" y="50%" text-anchor="middle" dy="0.35em" fill="${color.text}" font-size="${size/2}" font-family="Arial, sans-serif" font-weight="600">${initial}</text>
    </svg>
  `)}`;
}

// 生成机器人头像的 SVG
export function generateRobotAvatarSVG(size = 400) {
  return `data:image/svg+xml,${encodeURIComponent(`
    <svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 400 400">
      <defs>
        <linearGradient id="robotGradient" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" style="stop-color:#f8f9fa;stop-opacity:1" />
          <stop offset="100%" style="stop-color:#e9ecef;stop-opacity:1" />
        </linearGradient>
      </defs>

      <!-- 机器人身体 -->
      <ellipse cx="200" cy="220" rx="140" ry="160" fill="url(#robotGradient)" stroke="#dee2e6" stroke-width="3"/>

      <!-- 头部 -->
      <circle cx="200" cy="140" r="80" fill="url(#robotGradient)" stroke="#dee2e6" stroke-width="3"/>

      <!-- 天线 -->
      <line x1="200" y1="60" x2="200" y2="30" stroke="#dee2e6" stroke-width="4" stroke-linecap="round"/>
      <circle cx="200" cy="25" r="8" fill="#4b8053"/>

      <!-- 微笑的眼睛 -->
      <path d="M 170 130 Q 175 125 180 130" fill="none" stroke="#4b8053" stroke-width="5" stroke-linecap="round"/>
      <path d="M 220 130 Q 225 125 230 130" fill="none" stroke="#4b8053" stroke-width="5" stroke-linecap="round"/>

      <!-- 微笑的嘴巴 -->
      <path d="M 170 160 Q 200 175 230 160" fill="none" stroke="#4b8053" stroke-width="6" stroke-linecap="round"/>

      <!-- 手臂 -->
      <ellipse cx="100" cy="250" rx="30" ry="70" fill="url(#robotGradient)" stroke="#dee2e6" stroke-width="3" transform="rotate(-20 100 250)"/>
      <ellipse cx="300" cy="250" rx="30" ry="70" fill="url(#robotGradient)" stroke="#dee2e6" stroke-width="3" transform="rotate(20 300 250)"/>

      <!-- 装饰点 -->
      <circle cx="200" cy="260" r="6" fill="#4b8053" opacity="0.3"/>
      <circle cx="200" cy="290" r="6" fill="#4b8053" opacity="0.3"/>
      <circle cx="200" cy="320" r="6" fill="#4b8053" opacity="0.3"/>
    </svg>
  `)}`;
}
