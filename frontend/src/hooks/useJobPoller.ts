import { useEffect, useRef, useState } from 'react'
import { ingestApi } from '@/api/endpoints'
import type { UploadJobStatus } from '@/types'

/**
 * Polls job status every 2 seconds until completed or failed.
 */
export function useJobPoller(jobId: string | null) {
  const [job, setJob] = useState<UploadJobStatus | null>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (!jobId) return

    const poll = async () => {
      try {
        const status = await ingestApi.getJobStatus(jobId)
        setJob(status)
        if (status.status === 'completed' || status.status === 'failed') {
          if (intervalRef.current) clearInterval(intervalRef.current)
        }
      } catch {
        if (intervalRef.current) clearInterval(intervalRef.current)
      }
    }

    poll()
    intervalRef.current = setInterval(poll, 2000)

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [jobId])

  return job
}
