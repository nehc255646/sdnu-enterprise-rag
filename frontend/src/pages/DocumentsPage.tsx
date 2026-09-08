import { useCallback, useEffect, useState } from 'react'
import { Button, Card, Select, Space, Table, Tag, Upload, message, Typography } from 'antd'
import { UploadOutlined, ReloadOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import {
  ALLOWED_UPLOAD_EXT,
  MAX_UPLOAD_BYTES,
  SYNC_THRESHOLD_BYTES,
  listDocuments,
  uploadDocument,
  validateUploadFile,
} from '../api/documents'
import type { DocumentListItem } from '../types'

const statusColor: Record<string, string> = {
  pending: 'default',
  processing: 'processing',
  succeeded: 'success',
  failed: 'error',
}

export default function DocumentsPage() {
  const [items, setItems] = useState<DocumentListItem[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [docType, setDocType] = useState<string | undefined>('kb')
  const [uploading, setUploading] = useState(false)
  const [page, setPage] = useState(1)
  const pageSize = 50

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const data = await listDocuments({
        doc_type: docType,
        offset: (page - 1) * pageSize,
        limit: pageSize,
      })
      setItems(data.items || [])
      setTotal(data.total || 0)
    } catch (e) {
      message.error(e instanceof Error ? e.message : '加载失败')
    } finally {
      setLoading(false)
    }
  }, [docType, page])

  useEffect(() => { void refresh() }, [refresh])

  const columns: ColumnsType<DocumentListItem> = [
    { title: '文件名', dataIndex: 'filename', key: 'filename' },
    { title: '类型', dataIndex: 'doc_type', key: 'doc_type', width: 100 },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (s: string) => <Tag color={statusColor[s] || 'default'}>{s}</Tag>,
    },
    { title: '分块数', dataIndex: 'chunk_count', key: 'chunk_count', width: 90 },
    { title: '文档 ID', dataIndex: 'document_id', key: 'document_id', ellipsis: true },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 200,
      render: (v?: string | null) => v || '-',
    },
  ]

  return (
    <Card
      title="文档管理"
      extra={
        <Space>
          <Select
            allowClear
            placeholder="doc_type"
            style={{ width: 140 }}
            value={docType}
            onChange={(v) => { setPage(1); setDocType(v) }}
            options={[
              { value: 'kb', label: 'kb' },
              { value: 'resume', label: 'resume' },
              { value: 'jd', label: 'jd' },
              { value: 'internship', label: 'internship' },
              { value: 'other', label: 'other' },
            ]}
          />
          <Button icon={<ReloadOutlined />} onClick={() => void refresh()}>刷新</Button>
          <Upload
            showUploadList={false}
            accept={ALLOWED_UPLOAD_EXT.join(',')}
            beforeUpload={async (file) => {
              const f = file as File
              const err = validateUploadFile(f)
              if (err) {
                message.error(err)
                return false
              }
              setUploading(true)
              try {
                const sync = f.size <= SYNC_THRESHOLD_BYTES
                const res = await uploadDocument(f, docType || 'kb', sync)
                if (res?.status === 'failed') {
                  message.error(res.message || '入库失败')
                } else {
                  message.success(sync ? '上传并同步入库成功' : '已提交异步入库，稍后刷新查看状态')
                }
                if (!sync && res?.document_id) {
                  // soft refresh soon for async jobs
                  setTimeout(() => { void refresh() }, 1500)
                }
                await refresh()
              } catch (e) {
                message.error(e instanceof Error ? e.message : '上传失败')
              } finally {
                setUploading(false)
              }
              return false
            }}
          >
            <Button type="primary" icon={<UploadOutlined />} loading={uploading}>上传文档</Button>
          </Upload>
        </Space>
      }
    >
      <Typography.Paragraph type="secondary">
        支持 {ALLOWED_UPLOAD_EXT.join(' / ')}，最大 {Math.round(MAX_UPLOAD_BYTES / 1024 / 1024)}MB；
        超过 {Math.round(SYNC_THRESHOLD_BYTES / 1024 / 1024)}MB 走异步入库（sync=false），避免卡住界面。
      </Typography.Paragraph>
      <Table
        rowKey="document_id"
        loading={loading}
        columns={columns}
        dataSource={items}
        pagination={{
          current: page,
          total,
          pageSize,
          hideOnSinglePage: true,
          onChange: (p) => setPage(p),
        }}
      />
    </Card>
  )
}
