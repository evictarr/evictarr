export interface SessionInfo {
  username: string
  mfa_enabled: boolean
}

export interface VersionResponse {
  version: string
}

export type AuthMethod = 'none' | 'basic'

export interface AuthConfig {
  auth_method: AuthMethod
}

export interface MfaEnrollResponse {
  secret: string
  otpauth_uri: string
  qr_png_base64: string
}

export type ServiceName = 'jellyfin' | 'seerr' | 'radarr' | 'sonarr'

export interface Integration {
  service: ServiceName
  base_url: string | null
  has_api_key: boolean
  extra_config: Record<string, unknown>
  enabled: boolean
  last_test_status: 'unknown' | 'ok' | 'failed'
  last_test_at: string | null
  last_test_detail: string | null
}

export interface IntegrationUpdateRequest {
  base_url: string | null
  api_key?: string | null
  extra_config: Record<string, unknown>
  enabled: boolean
}

export interface TestConnectionResponse {
  ok: boolean
  detail: string
}

export interface JellyfinUser {
  id: string
  name: string
}

export type RuleType = 'movie_watched_cleanup' | 'series_watched_cleanup' | 'stale_request_cleanup'
export type ThresholdUnit = 'hours' | 'days' | 'weeks' | 'months' | 'years'
export type SeriesGranularity = 'series' | 'season'

export interface Rule {
  id: number
  name: string
  rule_type: RuleType
  enabled: boolean
  threshold_value: number
  threshold_unit: ThresholdUnit
  granularity: SeriesGranularity | null
  exempt_favorite: boolean
}

export interface RuleFormValues {
  name: string
  rule_type: RuleType
  threshold_value: number
  threshold_unit: ThresholdUnit
  granularity: SeriesGranularity | null
  exempt_favorite: boolean
  enabled: boolean
}

export type RunStatus = 'running' | 'completed' | 'failed'
export type RunTypeValue = 'scheduled' | 'manual'

export interface Run {
  id: number
  run_type: RunTypeValue
  triggered_by: string
  started_at: string
  finished_at: string | null
  status: RunStatus
  items_scanned: number
  items_matched: number
  items_skipped: number
}

export type EventLevel = 'match' | 'skip' | 'error'

export interface RunEvent {
  id: number
  rule_id: number | null
  level: EventLevel
  media_title: string | null
  reason: string | null
  detail: Record<string, unknown> | null
  created_at: string
}

export type PendingMediaType = 'movie' | 'series' | 'season'
export type PendingStatus = 'pending' | 'cancelled' | 'executing' | 'completed' | 'failed'

export interface PendingDeletion {
  id: number
  rule_id: number | null
  media_type: PendingMediaType
  title: string
  external_ids: Record<string, unknown>
  staged_at: string
  grace_period_hours: number
  execute_after: string
  status: PendingStatus
  cancelled_at: string | null
  cancelled_reason: string | null
}

export type WatchedStatus = 'approaching' | 'exempt'

export interface WatchedStatusItem {
  title: string
  media_type: PendingMediaType
  jellyfin_item_id: string | null
  watched_at: string | null
  rule_id: number
  rule_name: string
  status: WatchedStatus
  threshold_value: number
  threshold_unit: ThresholdUnit
  hours_remaining: number | null
}

export interface WatchedStatusResponse {
  approaching: WatchedStatusItem[]
  exempt: WatchedStatusItem[]
}

export interface AppSettings {
  scheduler_time: string
  timezone: string
  default_grace_period_hours: number
  executor_interval_minutes: number
  log_retention_days: number
}

export type NotificationProviderName = 'discord' | 'telegram'

export interface NotificationConfig {
  provider: NotificationProviderName
  enabled: boolean
  config_summary: Record<string, unknown>
  notify_on_stage: boolean
  notify_on_execute: boolean
  notify_daily_summary: boolean
}

export type SystemStatus = 'success' | 'failed' | 'skipped'
export type OverallStatus = 'success' | 'partial_failure' | 'failed'

export interface ActionLogEntry {
  id: number
  pending_deletion: { id: number; title: string; media_type: PendingMediaType }
  seerr_status: SystemStatus | null
  radarr_sonarr_status: SystemStatus | null
  disk_status: SystemStatus | null
  overall_status: OverallStatus
  error_detail: Record<string, unknown> | null
  executed_at: string
}

export type LibraryContext = 'movies' | 'tv'
export type OrphanedStatus = 'open' | 'cleared'

export interface OrphanedFile {
  id: number
  path: string
  size_bytes: number
  service_context: LibraryContext
  detected_at: string
  status: OrphanedStatus
  cleared_at: string | null
}
