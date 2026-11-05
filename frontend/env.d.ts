/// <reference types="vite/client" />
/// <reference types="element-plus/global" />

interface ImportMetaEnv {
  readonly VITE_API_BASE: string
  readonly VITE_GRAFANA_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}