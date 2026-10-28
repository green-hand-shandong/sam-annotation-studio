import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { get, fmtTime } from '@/lib/utils'

const STAT_NAMES: Record<string, string> = {
  datasets: '数据集', images: '图片', tasks: '任务', annotations: '标注',
  pending_review: '待审核', passed: '审核通过', rejected: '驳回次数', exports: '导出次数',
}

export default function Dashboard() {
  const [dash, setDash] = useState<any>({ stats: {}, by_source: [], by_task: [], recent_logs: [] })
  useEffect(() => { get('/api/system/dashboard').then(setDash) }, [])
  return (
    <div className="space-y-5">
      <h2 className="text-xl font-semibold">工作看板</h2>
      <div className="grid grid-cols-8 gap-3">
        {Object.entries(dash.stats).map(([k, v]) => (
          <Card key={k}><CardContent className="p-4 text-center">
            <div className="text-2xl font-bold text-primary">{v as number}</div>
            <div className="text-xs text-muted-foreground">{STAT_NAMES[k] || k}</div>
          </CardContent></Card>
        ))}
      </div>
      <div className="grid grid-cols-3 gap-4">
        <Card><CardHeader><CardTitle className="text-sm">标注来源分布</CardTitle></CardHeader>
          <CardContent>
            <Table><TableHeader><TableRow><TableHead>来源</TableHead><TableHead>数量</TableHead></TableRow></TableHeader>
              <TableBody>{dash.by_source.map((r: any) => (
                <TableRow key={r.source}><TableCell>{r.source}</TableCell><TableCell>{r.count}</TableCell></TableRow>))}
              </TableBody></Table>
          </CardContent></Card>
        <Card><CardHeader><CardTitle className="text-sm">最近任务</CardTitle></CardHeader>
          <CardContent>
            <Table><TableHeader><TableRow><TableHead>任务</TableHead><TableHead>状态</TableHead><TableHead>标注</TableHead></TableRow></TableHeader>
              <TableBody>{dash.by_task.map((t: any) => (
                <TableRow key={t.id}><TableCell>{t.name}</TableCell><TableCell>{t.status}</TableCell><TableCell>{t.annos}</TableCell></TableRow>))}
              </TableBody></Table>
          </CardContent></Card>
        <Card><CardHeader><CardTitle className="text-sm">操作日志</CardTitle></CardHeader>
          <CardContent>
            <div className="max-h-64 overflow-y-auto font-mono text-xs text-muted-foreground leading-6">
              {dash.recent_logs.map((l: any, i: number) => (
                <div key={i}>[{fmtTime(l.created_at)}] {l.user} {l.action} {l.detail}</div>))}
            </div>
          </CardContent></Card>
      </div>
    </div>
  )
}
