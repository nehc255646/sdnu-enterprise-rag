import { useCallback, useEffect, useState } from 'react'
import { Button, Card, Select, Space, Table, Tag, Upload, message, Typography } from 'antd'
import { UploadOutlined, ReloadOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { listDocuments, uploadDocument } from '../api/documents'
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

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const data = await listDocuments({ doc_type: docType })
      setItems(data.items || [])
      setTotal(data.total || 0)
    } catch (e) {
      message.error(e instanceof Error ? e.message : '加载失败')
    } finally {
      setLoading(false)
    }
  }, [docType])

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
            onChange={(v) => setDocType(v)}
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
            beforeUpload={async (file) => {
              setUploading(true)
              try {
                await uploadDocument(file as File, docType || 'kb', true)
                message.success('上传并入库成功')
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
        对接后端1 GET /api/v1/documents 与 POST /api/v1/ingest，请求头带 X-Tenant-Id。
      </Typography.Paragraph>
      <Table
        rowKey="document_id"
        loading={loading}
        columns={columns}
        dataSource={items}
        pagination={{ total, pageSize: 50, hideOnSinglePage: true }}
      />
    </Card>
  )
}
