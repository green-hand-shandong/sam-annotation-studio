import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export async function api<T = any>(method: string, url: string, body?: any, raw = false): Promise<T> {
  const token = localStorage.getItem('token')
  const opt: RequestInit = { method, headers: {} as any }
  if (token) (opt.headers as any).Authorization = `Bearer ${token}`
  if (body !== undefined && !(body instanceof FormData)) {
    ;(opt.headers as any)['Content-Type'] = 'application/json'
    opt.body = JSON.stringify(body)
  } else if (body instanceof FormData) opt.body = body
  const resp = await fetch(url, opt)
  if (resp.status === 401 && token) {
    localStorage.removeItem('token')
    window.location.reload()
    throw new Error('登录已失效')
  }
  if (!resp.ok) {
    let msg = `HTTP ${resp.status}`
    try { msg = (await resp.json()).detail || msg } catch {}
    throw new Error(msg)
  }
  return raw ? (resp as any) : resp.json()
}

export const get = <T = any>(url: string) => api<T>('GET', url)
export const post = (url: string, body?: any) => api('POST', url, body)
export const put = (url: string, body?: any) => api('PUT', url, body)
export const del = (url: string) => api('DELETE', url)
export const qsUrl = (url: string) =>
  url + (url.includes('?') ? '&' : '?') + 'token=' + encodeURIComponent(localStorage.getItem('token') || '')
export const fmtTime = (t: number) => new Date(t * 1000).toLocaleString('zh-CN', { hour12: false })
