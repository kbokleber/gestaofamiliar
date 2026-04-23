import { useEffect, useState } from 'react'
import { APP_BUILD_TIME, APP_VERSION, extractRevision, formatBuildTimestamp } from '../config/version'

type VersionResponse = {
  version?: string
  commit?: string
  releaseName?: string
}

export function useAppVersion() {
  const [version, setVersion] = useState(APP_VERSION)
  const [revision, setRevision] = useState(extractRevision(APP_VERSION))

  useEffect(() => {
    if (APP_VERSION !== 'dev-local') {
      setVersion(APP_VERSION)
      setRevision(extractRevision(APP_VERSION))
      return
    }

    const controller = new AbortController()

    const loadVersion = async () => {
      try {
        const response = await fetch('/api/v1/system/version', {
          signal: controller.signal,
        })

        if (!response.ok) {
          return
        }

        const data = (await response.json()) as VersionResponse
        const resolvedVersion = data.releaseName || data.version

        if (resolvedVersion && resolvedVersion !== 'dev') {
          setVersion(resolvedVersion)
          setRevision(extractRevision(data.commit || resolvedVersion))
        }
      } catch (error) {
        if (import.meta.env.DEV) {
          console.warn('Não foi possível carregar a versão oficial do backend.', error)
        }
      }
    }

    void loadVersion()

    return () => controller.abort()
  }, [])

  return {
    version,
    revision,
    buildTime: APP_BUILD_TIME,
    buildTimeLabel: formatBuildTimestamp(APP_BUILD_TIME),
  }
}
