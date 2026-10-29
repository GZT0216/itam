import dayjs from 'dayjs'

export function formatDateTime(value?: string | null): string {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm') : '—'
}

export function greeting(): string {
  const hour = new Date().getHours()
  if (hour < 6) return '夜深了'
  if (hour < 9) return '早上好'
  if (hour < 12) return '上午好'
  if (hour < 14) return '中午好'
  if (hour < 18) return '下午好'
  return '晚上好'
}

export function initials(name?: string | null): string {
  if (!name) return 'IT'
  return name.trim().slice(0, 2).toUpperCase()
}

export function todayLabel(): string {
  return dayjs().format('YYYY 年 M 月 D 日')
}
