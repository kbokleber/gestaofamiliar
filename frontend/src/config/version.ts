import packageJson from '../../package.json'

const FALLBACK_VERSION = `${packageJson.version}-dev`

export const APP_VERSION = import.meta.env.VITE_APP_VERSION || FALLBACK_VERSION

