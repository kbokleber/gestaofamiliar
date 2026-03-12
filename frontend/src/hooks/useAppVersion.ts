import { useEffect, useState } from 'react'
import { APP_VERSION } from '../config/version'

type VersionResponse = {
  version?: string
  releaseName?: string
}

export function useAppVersion() {
  const [version, setVersion] = useState(APP_VERSION)

  useEffect(() => {
    if (APP_VERSION !== 'dev-local') {
      setVersion(APP_VERSION)
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

  return version
}
