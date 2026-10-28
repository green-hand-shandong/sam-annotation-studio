import { useCallback, useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { post, get, qsUrl, api, del } from '@/lib/utils'

/* 标注画布状态（非 React 状态，避免高频渲染） */
type CvState = {
  ctx: CanvasRenderingContext2D
  image: HTMLImageElement | null
  scale: number
  points: [number, number][]
  labels: number[]
  dragBox: number[] | null
  dragStart: [number, number] | null
  box: number[] | null
  maskImg: HTMLImageElement | null
  activeMask: HTMLImageElement | null
}

function newCv(cv: HTMLCanvasElement): CvState {
  return { ctx: cv.getContext('2d')!, image: null, scale: 1, points: [], labels: [],
           dragBox: null, dragStart: null, box: null, maskImg: null, activeMask: null }
}

function render(cvEl: HTMLCanvasElement, st: CvState) {
  const { ctx } = st
  ctx.clearRect(0, 0, cvEl.width, cvEl.height)
  if (!st.image) return
  ctx.drawImage(st.image, 0, 0, cvEl.width, cvEl.height)
  if (st.activeMask) { ctx.globalAlpha = 0.45; ctx.drawImage(st.activeMask, 0, 0, cvEl.width, cvEl.height); ctx.globalAlpha = 1 }
  if (st.maskImg) { ctx.globalAlpha = 0.5; ctx.drawImage(st.maskImg, 0, 0, cvEl.width, cvEl.height); ctx.globalAlpha = 1 }
  const s = st.scale
  st.points.forEach((p, i) => {
    ctx.beginPath(); ctx.arc(p[0] * s, p[1] * s, 6, 0, 7)
    ctx.fillStyle = st.labels[i] === 1 ? '#22c55e' : '#ef4444'; ctx.fill()
    ctx.lineWidth = 2; ctx.strokeStyle = '#fff'; ctx.stroke()
  })
  if (st.box) { ctx.strokeStyle = '#3b82f6'; ctx.lineWidth = 2; ctx.strokeRect(st.box[0]*s, st.box[1]*s, st.box[2]*s, st.box[3]*s) }
  if (st.dragBox) {
    ctx.setLineDash([6, 4]); ctx.strokeStyle = '#f59e0b'; ctx.lineWidth = 2
    ctx.strokeRect(st.dragBox[0]*s, st.dragBox[1]*s, st.dragBox[2]*s, st.dragBox[3]*s)
    ctx.setLineDash([])
  }
}

function toImgXY(e: React.MouseEvent, cvEl: HTMLCanvasElement, st: CvState): [number, number] {
  const r = cvEl.getBoundingClientRect()
  return [(e.clientX - r.left) / st.scale, (e.clientY - r.top) / st.scale]
}

export default function Workbench() {
  const loc = useLocation() as any
  const cvRef = useRef<HTMLCanvasElement>(null)
  const st = useRef<CvState | null>(null)
  const [mode, setMode] = useState<'point' | 'box'>('point')
  const [images, setImages] = useState<any[]>([])
  const [image, setImage] = useState<any>(null)
  const [annos, setAnnos] = useState<any[]>([])
  const [result, setResult] = useState<any>(null)
  const [running, setRunning] = useState(false)
  const [preRunning, setPreRunning] = useState(false)
  const [preText, setPreText] = useState('')
  const [task, setTask] = useState<any>(null)
  const [categories, setCategories] = useState<string[]>(['object'])
  const [category, setCategory] = useState(0)
  const [taskId, setTaskId] = useState<number | null>(loc.state?.taskId ?? null)

  /* 初始化画布 */
  useEffect(() => {
    if (cvRef.current && !st.current) st.current = newCv(cvRef.current)
  }, [])

  /* 无 taskId 时用第一个任务 */
  useEffect(() => {
    if (taskId == null) {
      get('/api/tasks').then(ts => {
        if (ts.length) setTaskId(ts[0].id)
        else alert('暂无任务，请先在「标注任务」页创建')
      })
    }
  }, [taskId])

  const loadTask = useCallback(async (id: number) => {
    const t = await get('/api/tasks/' + id)
    setTask(t)
    setCategories(t.categories.length ? t.categories : ['object'])
    const imgs = await get(`/api/tasks/${id}/images`)
    setImages(imgs)
    if (imgs.length) selectImage(imgs[0], id)
  }, [])

  useEffect(() => { if (taskId != null) loadTask(taskId) }, [taskId, loadTask])

  async function selectImage(im: any, tid = taskId) {
    setImage(im); setResult(null)
    const stc = st.current!
    stc.points = []; stc.labels = []; stc.box = null; stc.maskImg = null; stc.activeMask = null
    await loadImage(qsUrl(`/api/images/${im.id}/file`))
    setAnnos(await get(`/api/annotations?task_id=${tid}&image_id=${im.id}`))
    render(cvRef.current!, stc)
  }

  function loadImage(url: string) {
    const stc = st.current!
    return new Promise<void>(res => {
      const img = new Image()
      img.onload = () => {
        stc.image = img
        const scale = Math.min(1100 / img.width, 640 / img.height, 1.0)
        stc.scale = scale
        cvRef.current!.width = img.width * scale
        cvRef.current!.height = img.height * scale
        render(cvRef.current!, stc)
        res()
      }
      img.src = url
    })
  }

  /* 交互 */
  function onMouseDown(e: React.MouseEvent) {
    const stc = st.current!
    if (!stc.image || mode !== 'box') return
    stc.dragStart = toImgXY(e, cvRef.current!, stc)
  }
  function onMouseMove(e: React.MouseEvent) {
    const stc = st.current!
    if (!stc.image || mode !== 'box' || !stc.dragStart) return
    const [x, y] = toImgXY(e, cvRef.current!, stc)
    const [x0, y0] = stc.dragStart
    stc.dragBox = [Math.min(x0, x), Math.min(y0, y), Math.abs(x - x0), Math.abs(y - y0)]
    render(cvRef.current!, stc)
  }
  function onMouseUp(e: React.MouseEvent) {
    const stc = st.current!
    if (!stc.image || mode !== 'box' || !stc.dragStart) return
    const d = stc.dragBox
    stc.dragStart = null; stc.dragBox = null
    if (d && d[2] > 4 && d[3] > 4) { stc.box = d; runSegment(stc) }
    else render(cvRef.current!, stc)
  }
  function onClick(e: React.MouseEvent) {
    const stc = st.current!
    if (!stc.image || mode !== 'point') return
    const [x, y] = toImgXY(e, cvRef.current!, stc)
    stc.points.push([Math.round(x), Math.round(y)])
    stc.labels.push(e.altKey ? 0 : 1)   // Alt+点击 = 背景点
    render(cvRef.current!, stc)
  }

  async function runSegment(stc = st.current) {
    const s = stc!
    if (!image || (!s.points.length && !s.box)) { alert('请先点选或框选目标'); return }
    setRunning(true)
    try {
      const r = await post('/api/inference/segment', {
        image_id: image.id, model: 'sam',
        points: s.points, point_labels: s.labels,
        boxes: s.box ? [[s.box[0], s.box[1], s.box[0] + s.box[2], s.box[1] + s.box[3]]] : [],
      })
      setResult(r)
      const im = new Image()
      im.onload = () => { s.maskImg = im; render(cvRef.current!, s) }
      im.src = 'data:image/png;base64,' + r.mask_png_b64
    } catch (e: any) { alert('分割失败: ' + e.message) }
    setRunning(false)
  }

  async function saveAnnotation() {
    if (!result || !image || !task) return
    const stc = st.current!
    const a = await post('/api/annotations', {
      task_id: task.id, image_id: image.id, category_id: category,
      bbox: result.bbox, mask_png_b64: result.mask_png_b64,
      area: result.area, score: result.score, source: 'sam',
    })
    setAnnos(await get(`/api/annotations?task_id=${task.id}&image_id=${image.id}`))
    setImages(await get(`/api/tasks/${task.id}/images`))
    stc.points = []; stc.labels = []; stc.box = null; stc.maskImg = null; setResult(null)
    render(cvRef.current!, stc)
    alert(`已保存标注 #${a.id}，类别: ${categories[category]}`)
  }

  async function toggleShow(a: any) {
    const stc = st.current!
    if (stc.activeMask) { stc.activeMask = null; render(cvRef.current!, stc); return }
    const resp = await api('GET', qsUrl(`/api/annotations/${a.id}/mask`), undefined, true)
    const im = new Image()
    im.onload = () => { stc.activeMask = im; render(cvRef.current!, stc) }
    im.src = URL.createObjectURL(await resp.blob())
  }

  async function delAnno(a: any) {
    if (!confirm(`删除标注 #${a.id}？`)) return
    await del('/api/annotations/' + a.id)
    setAnnos(await get(`/api/annotations?task_id=${task.id}&image_id=${image.id}`))
    const stc = st.current!
    stc.activeMask = null; render(cvRef.current!, stc)
  }

  async function preannotate() {
    if (!preText || !task) return alert('请输入预标注文字提示')
    setPreRunning(true)
    try {
      const r = await post(`/api/inference/preannotate/${task.id}`, { text: preText, limit: 10 })
      alert(`SAM3 预标注完成：${r.images} 张图片生成 ${r.generated} 条标注（待复核）`)
      setImages(await get(`/api/tasks/${task.id}/images`))
      if (image) selectImage(image)
    } catch (e: any) { alert(e.message) }
    setPreRunning(false)
  }

  function clearPrompts() {
    const stc = st.current!
    stc.points = []; stc.labels = []; stc.box = null; stc.maskImg = null; setResult(null)
    render(cvRef.current!, stc)
  }

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Enter') { e.preventDefault(); runSegment() }
      if (e.key === 's' || e.key === 'S') { e.preventDefault(); saveAnnotation() }
      if (e.key === 'Escape') clearPrompts()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2 rounded-xl bg-card p-3 shadow-sm">
        <b className="mr-2">{task ? task.name : '工作台'}</b>
        <span className="flex-1 text-xs text-muted-foreground">
          左键点选=前景 · Alt+点选=背景 · 切到框选拖拽 · Enter 分割 · S 保存
        </span>
        <label className="text-sm">类别
          <Select value={category} onChange={e => setCategory(Number(e.target.value))} className="ml-1 w-32">
            {categories.map((c, i) => <option key={i} value={i}>{i + 1}.{c}</option>)}
          </Select>
        </label>
        <Button variant={mode === 'point' ? 'default' : 'outline'} size="sm" onClick={() => setMode('point')}>点选</Button>
        <Button variant={mode === 'box' ? 'default' : 'outline'} size="sm" onClick={() => setMode('box')}>框选</Button>
        <Button size="sm" variant="outline" onClick={() => { const s = st.current!; s.points.pop(); s.labels.pop(); render(cvRef.current!, s) }}>撤销点</Button>
        <Button size="sm" variant="outline" onClick={clearPrompts}>清除提示</Button>
        <Button size="sm" onClick={() => runSegment()} disabled={running}>{running ? '分割中...' : '生成分割'}</Button>
        <Button size="sm" variant="secondary" onClick={saveAnnotation} disabled={!result}>保存标注</Button>
        <Input className="w-40" placeholder="SAM3 预标注文字" value={preText} onChange={e => setPreText(e.target.value)} />
        <Button size="sm" variant="outline" onClick={preannotate} disabled={preRunning}>
          {preRunning ? '预标注中...' : '批量预标注'}</Button>
        {result && <span className="text-sm font-semibold text-green-600">IoU: {result.score}</span>}
      </div>
      <div className="flex gap-3">
        <div className="w-60 rounded-xl bg-card p-3 shadow-sm">
          <div className="mb-2 text-xs text-muted-foreground">图片列表 ({images.length})</div>
          <div className="max-h-[680px] space-y-0.5 overflow-y-auto">
            {images.map(im => (
              <div key={im.id} onClick={() => selectImage(im)}
                className={`flex cursor-pointer items-center justify-between rounded-md px-2.5 py-1.5 text-sm hover:bg-muted ${image?.id === im.id && 'bg-blue-50 font-medium'}`}>
                <span className="truncate">{im.filename}</span>
                <span className="ml-1 text-xs text-muted-foreground">{im.anno_count}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="relative flex min-h-[660px] flex-1 items-start justify-center rounded-xl bg-slate-600 p-4">
          <canvas ref={cvRef} className="cursor-crosshair bg-black"
            onClick={onClick} onMouseDown={onMouseDown} onMouseMove={onMouseMove} onMouseUp={onMouseUp}
            onContextMenu={e => e.preventDefault()} />
          {!image && <div className="absolute top-1/2 text-slate-300">← 请先选择图片</div>}
        </div>
        <div className="w-64 rounded-xl bg-card p-3 shadow-sm">
          <div className="mb-2 text-xs text-muted-foreground">当前标注 ({annos.length})</div>
          <div className="max-h-[680px] space-y-0.5 overflow-y-auto">
            {annos.map(a => (
              <div key={a.id} className="group flex items-center justify-between rounded-md px-2.5 py-1.5 text-sm hover:bg-muted">
                <span className="cursor-pointer" onClick={() => toggleShow(a)}>
                  #{a.id} {categories[a.category_id] || '?'} <span className="text-xs text-muted-foreground">{a.source} {a.score}</span>
                </span>
                <Button size="sm" variant="destructive" className="h-6 px-2 opacity-0 group-hover:opacity-100"
                  onClick={() => delAnno(a)}>删</Button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
