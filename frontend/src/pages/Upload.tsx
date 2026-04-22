import { useState, useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Upload as UploadIcon, FileText, CheckCircle2,
  AlertCircle, X, ArrowRight, Info,
} from 'lucide-react'
import { TopBar } from '@/components/layout/TopBar'
import { ingestApi } from '@/api/endpoints'
import { useJobPoller } from '@/hooks/useJobPoller'
import { cn } from '@/lib/utils'
import toast from 'react-hot-toast'

type JobState = {
  jobId: string
  filename: string
}

export default function Upload() {
  const [activeJob, setActiveJob] = useState<JobState | null>(null)
  const [uploading, setUploading] = useState(false)

  const job = useJobPoller(activeJob?.jobId ?? null)

  const onDrop = useCallback(async (accepted: File[]) => {
    const file = accepted[0]
    if (!file) return

    setUploading(true)
    try {
      const result = await ingestApi.uploadFile(file)
      setActiveJob({ jobId: result.job_id, filename: file.name })
      toast.success('File uploaded — processing started')
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? 'Upload failed')
    } finally {
      setUploading(false)
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive, fileRejections } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.ms-excel': ['.xls'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
    },
    maxFiles: 1,
    maxSize: 50 * 1024 * 1024,
    disabled: uploading || (job?.status === 'processing'),
  })

  const progress = job?.progress_percent ?? 0
  const isComplete = job?.status === 'completed'
  const isFailed = job?.status === 'failed'
  const isProcessing = job?.status === 'processing' || job?.status === 'queued'

  const reset = () => setActiveJob(null)

  return (
    <div className="flex flex-col h-full">
      <TopBar title="Upload Data" subtitle="CSV / Excel batch ingestion" />

      <div className="flex-1 p-6 space-y-6 max-w-3xl mx-auto w-full">

        {/* Format guide */}
        <div className="glass-card p-4 flex gap-3">
          <Info size={16} className="text-blue-400 mt-0.5 flex-shrink-0" />
          <div className="text-xs space-y-1" style={{ color: 'rgba(255,255,255,0.55)' }}>
            <p className="font-semibold text-white/70">Expected columns (auto-detected):</p>
            <p>
              <span className="text-neon-blue">text / review / comment</span> — review content (required) &nbsp;·&nbsp;
              <span className="text-neon-purple">date / created_at</span> — review date &nbsp;·&nbsp;
              <span className="text-neon-cyan">product / product_id</span> — product name &nbsp;·&nbsp;
              <span className="text-neon-green">branch / location</span> — branch/store
            </p>
          </div>
        </div>

        {/* Drop zone */}
        <AnimatePresence mode="wait">
          {!activeJob ? (
            <motion.div
              key="dropzone"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
            >
              <div
                {...getRootProps()}
                className={cn(
                  'glass-card p-12 text-center cursor-pointer transition-all duration-200',
                  isDragActive && 'border-brand-500 bg-brand-500/10',
                  (uploading) && 'opacity-60 cursor-not-allowed',
                )}
                style={isDragActive ? { borderColor: '#7c3aed', boxShadow: '0 0 30px rgba(124,58,237,0.2)' } : {}}
              >
                <input {...getInputProps()} />

                <motion.div
                  animate={isDragActive ? { scale: 1.1 } : { scale: 1 }}
                  transition={{ duration: 0.2 }}
                >
                  <div
                    className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4"
                    style={{ background: isDragActive ? 'rgba(124,58,237,0.3)' : 'rgba(255,255,255,0.06)' }}
                  >
                    {uploading ? (
                      <span className="w-6 h-6 border-2 border-brand-400/40 border-t-brand-400 rounded-full animate-spin" />
                    ) : (
                      <UploadIcon size={24} style={{ color: isDragActive ? '#a78bfa' : 'rgba(255,255,255,0.4)' }} />
                    )}
                  </div>

                  {uploading ? (
                    <p className="text-white/70 text-sm">Uploading...</p>
                  ) : isDragActive ? (
                    <p className="text-brand-300 font-semibold">Drop it here</p>
                  ) : (
                    <>
                      <p className="text-white font-semibold mb-1">
                        Drag & drop your file here
                      </p>
                      <p className="text-sm mb-4" style={{ color: 'rgba(255,255,255,0.4)' }}>
                        or click to browse
                      </p>
                      <p className="text-xs" style={{ color: 'rgba(255,255,255,0.25)' }}>
                        CSV, XLS, XLSX &nbsp;·&nbsp; Max 50MB
                      </p>
                    </>
                  )}
                </motion.div>
              </div>

              {fileRejections.length > 0 && (
                <p className="text-red-400 text-xs mt-2 text-center">
                  {fileRejections[0].errors[0].message}
                </p>
              )}
            </motion.div>
          ) : (
            <motion.div
              key="progress"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="glass-card p-6"
            >
              {/* Header */}
              <div className="flex items-start justify-between mb-5">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-xl" style={{ background: 'rgba(124,58,237,0.15)' }}>
                    <FileText size={18} className="text-brand-400" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-white">{activeJob.filename}</p>
                    <p className="text-xs mt-0.5" style={{ color: 'rgba(255,255,255,0.4)' }}>
                      Job ID: {activeJob.jobId.slice(0, 8)}...
                    </p>
                  </div>
                </div>

                {(isComplete || isFailed) && (
                  <button onClick={reset} className="p-1 rounded-lg hover:bg-white/10 transition-colors">
                    <X size={16} style={{ color: 'rgba(255,255,255,0.4)' }} />
                  </button>
                )}
              </div>

              {/* Status badge */}
              <div className="flex items-center gap-2 mb-4">
                {isComplete && (
                  <span className="badge-positive flex items-center gap-1.5">
                    <CheckCircle2 size={12} /> Completed
                  </span>
                )}
                {isFailed && (
                  <span className="badge-negative flex items-center gap-1.5">
                    <AlertCircle size={12} /> Failed
                  </span>
                )}
                {isProcessing && (
                  <span className="badge-neutral flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
                    Processing
                  </span>
                )}
              </div>

              {/* Progress bar */}
              <div
                className="w-full h-2 rounded-full mb-3 overflow-hidden"
                style={{ background: 'rgba(255,255,255,0.08)' }}
              >
                <motion.div
                  className="h-full rounded-full"
                  style={{
                    background: isFailed
                      ? 'linear-gradient(90deg, #f87171, #ef4444)'
                      : 'linear-gradient(90deg, #7c3aed, #2563eb)',
                  }}
                  initial={{ width: 0 }}
                  animate={{ width: `${isFailed ? 100 : progress}%` }}
                  transition={{ duration: 0.4 }}
                />
              </div>

              {/* Stats */}
              <div className="flex items-center justify-between text-xs" style={{ color: 'rgba(255,255,255,0.5)' }}>
                <span>
                  {job?.processed_rows ?? 0} / {job?.total_rows ?? '?'} rows processed
                </span>
                <span className="font-semibold text-white">
                  {isFailed ? 'Error' : `${progress.toFixed(0)}%`}
                </span>
              </div>

              {job?.failed_rows ? (
                <p className="text-xs mt-2 text-orange-400">
                  {job.failed_rows} rows failed (skipped)
                </p>
              ) : null}

              {isFailed && job?.error_message && (
                <p className="text-xs mt-3 text-red-400 bg-red-400/10 rounded-lg p-3">
                  {job.error_message}
                </p>
              )}

              {isComplete && (
                <motion.div
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mt-4 flex gap-3"
                >
                  <a
                    href="/dashboard"
                    className="btn-primary text-xs py-2 px-4"
                  >
                    View Dashboard <ArrowRight size={13} />
                  </a>
                  <button onClick={reset} className="btn-ghost text-xs py-2 px-4">
                    Upload Another
                  </button>
                </motion.div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Instructions */}
        <div className="glass-card p-5">
          <p className="text-xs font-semibold text-white/60 mb-3 uppercase tracking-wider">
            How it works
          </p>
          <div className="space-y-2.5">
            {[
              ['1', 'Upload your CSV or Excel file'],
              ['2', 'System auto-detects language and translates if needed'],
              ['3', 'Claude AI analyzes sentiment + aspects per review'],
              ['4', 'Results appear in your Dashboard in real time'],
            ].map(([num, text]) => (
              <div key={num} className="flex items-center gap-3">
                <span
                  className="w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0"
                  style={{ background: 'rgba(124,58,237,0.25)', color: '#a78bfa' }}
                >
                  {num}
                </span>
                <span className="text-xs" style={{ color: 'rgba(255,255,255,0.5)' }}>{text}</span>
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  )
}
