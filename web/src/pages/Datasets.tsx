import { useEffect, useRef, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { get, post, del, api } from '@/lib/utils'

export default function Datasets() {
  const [datasets, setDatasets] = useState<any[]>([])
  const [name, setName] = useState('')
  const [desc, setDesc] = useState('')
  const [uploadDs, setUploadDs] = useState<number | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)

  const refresh = () => get('/api/datasets').then(setDatasets)
  useEffect(() => { refresh() }, [])

  async function create() {
    if (!name) return
    await post('/api/datasets', { name, description: desc })
    setName(''); setDesc(''); refresh()
  }
  async function remove(d: any) {
    if (!confirm(`删除数据集「${d.name}」（${d.image_count} 张图）？`)) return
    await del('/api/datasets/' + d.id); refresh()
  }
  async function upload() {
    const files = fileRef.current?.files
    if (!files?.length || uploadDs == null) return
    const fd = new FormData()
    for (const f of files) fd.append('files', f)
    const r = await api('POST', `/api/datasets/${uploadDs}/upload`, fd)
    alert(`上传完成：新增 ${r.added} 张，跳过 ${r.skipped} 个`)
    setUploadDs(null); refresh()
  }

  return (
    <div className="space-y-5">
      <h2 className="text-xl font-semibold">数据集管理</h2>
      <Card><CardHeader><CardTitle className="text-sm">新建数据集</CardTitle></CardHeader>
        <CardContent className="flex gap-2">
          <Input className="w-56" placeholder="数据集名称" value={name} onChange={e => setName(e.target.value)} />
          <Input className="w-80" placeholder="描述" value={desc} onChange={e => setDesc(e.target.value)} />
          <Button onClick={create}>创建</Button>
        </CardContent></Card>
      <Card><CardHeader><CardTitle className="text-sm">数据集列表</CardTitle></CardHeader>
        <CardContent>
          <Table>
            <TableHeader><TableRow>
              <TableHead>ID</TableHead><TableHead>名称</TableHead><TableHead>描述</TableHead>
              <TableHead>图片数</TableHead><TableHead>创建人</TableHead><TableHead>操作</TableHead>
            </TableRow></TableHeader>
            <TableBody>{datasets.map(d => (
              <TableRow key={d.id}>
                <TableCell>{d.id}</TableCell><TableCell>{d.name}</TableCell>
                <TableCell>{d.description}</TableCell><TableCell>{d.image_count}</TableCell>
                <TableCell>{d.created_by}</TableCell>
                <TableCell className="space-x-1">
                  <Button size="sm" variant="outline" onClick={() => setUploadDs(d.id)}>上传图片</Button>
                  <Button size="sm" variant="destructive" onClick={() => remove(d)}>删除</Button>
                </TableCell>
              </TableRow>))}
            </TableBody>
          </Table>
          {uploadDs != null && (
            <div className="mt-4 rounded-lg bg-muted p-4 space-y-2">
              <div className="text-sm font-medium">上传到数据集 #{uploadDs}</div>
              <Input type="file" multiple className="w-96"
                accept=".jpg,.jpeg,.png,.bmp,.webp,.tif,.tiff,.zip" ref={fileRef} />
              <div className="flex gap-2">
                <Button size="sm" onClick={upload}>开始上传</Button>
                <Button size="sm" variant="outline" onClick={() => setUploadDs(null)}>取消</Button>
              </div>
            </div>
          )}
        </CardContent></Card>
    </div>
  )
}
