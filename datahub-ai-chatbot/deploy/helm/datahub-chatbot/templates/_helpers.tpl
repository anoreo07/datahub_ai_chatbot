{{- define "datahub-chatbot.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "datahub-chatbot.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{- define "datahub-chatbot.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "datahub-chatbot.labels" -}}
helm.sh/chart: {{ include "datahub-chatbot.chart" . }}
{{ include "datahub-chatbot.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "datahub-chatbot.selectorLabels" -}}
app.kubernetes.io/name: {{ include "datahub-chatbot.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "datahub-chatbot.apiSelectorLabels" -}}
app.kubernetes.io/name: {{ include "datahub-chatbot.name" . }}-api
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "datahub-chatbot.workerSelectorLabels" -}}
app.kubernetes.io/name: {{ include "datahub-chatbot.name" . }}-worker
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "datahub-chatbot.imagePullSecrets" -}}
{{- if .Values.global.imagePullSecrets }}
imagePullSecrets:
{{- range .Values.global.imagePullSecrets }}
  - name: {{ . }}
{{- end }}
{{- end }}
{{- end }}

{{- define "datahub-chatbot.image" -}}
{{- $registry := .Values.global.imageRegistry | default "" -}}
{{- $repository := .repository | default .Values.image.repository -}}
{{- $tag := .tag | default .Values.image.tag -}}
{{- if $registry -}}
{{- printf "%s/%s:%s" $registry $repository $tag -}}
{{- else -}}
{{- printf "%s:%s" $repository $tag -}}
{{- end -}}
{{- end -}}

{{- define "datahub-chatbot.env" -}}
- name: APP_NAME
  value: {{ .Values.app.name | default "DataHub AI Chatbot" | quote }}
- name: APP_ENV
  value: {{ .Values.app.env | quote }}
- name: APP_HOST
  value: {{ .Values.app.host | quote }}
- name: APP_PORT
  value: {{ .Values.app.port | quote }}
- name: LOG_LEVEL
  value: {{ .Values.app.logLevel | quote }}
- name: AUTH_MODE
  value: {{ .Values.app.authMode | quote }}
- name: AUTH_REQUIRED
  value: {{ .Values.app.authRequired | quote }}
- name: USE_MOCK_DATAHUB
  value: {{ .Values.app.useMockDatahub | quote }}
- name: DATAHUB_GMS_URL
  value: {{ .Values.datahub.gmsUrl | quote }}
- name: DATAHUB_FRONTEND_URL
  value: {{ .Values.datahub.frontendUrl | quote }}
- name: DATAHUB_PAGE_SIZE
  value: {{ .Values.datahub.pageSize | quote }}
- name: DATAHUB_REQUEST_TIMEOUT_SECONDS
  value: {{ .Values.datahub.requestTimeoutSeconds | quote }}
- name: DATAHUB_MAX_RETRIES
  value: {{ .Values.datahub.maxRetries | quote }}
- name: DATAHUB_SYNC_DRY_RUN
  value: {{ .Values.datahub.syncDryRun | quote }}
- name: EMBEDDING_PROVIDER
  value: {{ .Values.app.embeddingProvider | quote }}
- name: EMBEDDING_MODEL
  value: {{ .Values.app.embeddingModel | quote }}
- name: LLM_PROVIDER
  value: {{ .Values.app.llmProvider | quote }}
- name: LLM_MODEL
  value: {{ .Values.app.llmModel | quote }}
- name: ENABLE_DEV_ENDPOINTS
  value: {{ .Values.app.enableDevEndpoints | quote }}
- name: CACHE_ENABLED
  value: {{ .Values.app.cacheEnabled | quote }}
- name: CACHE_DEFAULT_TTL_SECONDS
  value: {{ .Values.app.cacheDefaultTtlSeconds | quote }}
- name: RATE_LIMIT_MAX_REQUESTS
  value: {{ .Values.app.rateLimitMaxRequests | quote }}
- name: RATE_LIMIT_WINDOW_SECONDS
  value: {{ .Values.app.rateLimitWindowSeconds | quote }}
- name: MAX_CONTEXT_CHUNKS
  value: {{ .Values.app.maxContextChunks | quote }}
- name: MAX_CONTEXT_CHARACTERS
  value: {{ .Values.app.maxContextCharacters | quote }}
- name: SEARCH_CACHE_TTL_SECONDS
  value: {{ .Values.app.searchCacheTtlSeconds | quote }}
- name: INDEX_MAX_RETRIES
  value: {{ .Values.app.indexMaxRetries | quote }}
- name: INDEX_BATCH_SIZE
  value: {{ .Values.app.indexBatchSize | quote }}
- name: LLM_TIMEOUT_SECONDS
  value: {{ .Values.app.llmTimeoutSeconds | quote }}
- name: LLM_MAX_RETRIES
  value: {{ .Values.app.llmMaxRetries | quote }}
- name: LOCAL_STORAGE_PATH
  value: {{ .Values.app.localStoragePath | quote }}
- name: MAX_DOCUMENT_SIZE_MB
  value: {{ .Values.app.maxDocumentSizeMb | quote }}
- name: ENABLE_MALWARE_SCAN
  value: {{ .Values.app.enableMalwareScan | quote }}
- name: DATABASE_URL
  valueFrom:
    secretKeyRef:
      name: {{ .Values.postgresql.existingSecret | default (printf "%s-db" (include "datahub-chatbot.fullname" .)) }}
      key: database-url
- name: REDIS_URL
  valueFrom:
    secretKeyRef:
      name: {{ .Values.redis.existingSecret | default (printf "%s-redis" (include "datahub-chatbot.fullname" .)) }}
      key: redis-url
- name: OPENSEARCH_URL
  valueFrom:
    secretKeyRef:
      name: {{ .Values.opensearch.existingSecret | default (printf "%s-search" (include "datahub-chatbot.fullname" .)) }}
      key: opensearch-url
{{- end }}

{{- define "datahub-chatbot.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "datahub-chatbot.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- .Values.serviceAccount.name | default "default" }}
{{- end }}
{{- end }}

{{- define "datahub-chatbot.secretEnv" -}}
- name: DATAHUB_TOKEN
  valueFrom:
    secretKeyRef:
      name: {{ .Values.datahub.existingSecret | default (printf "%s-datahub" (include "datahub-chatbot.fullname" .)) }}
      key: datahub-token
- name: JWT_SECRET_KEY
  valueFrom:
    secretKeyRef:
      name: {{ .Values.datahub.existingSecret | default (printf "%s-datahub" (include "datahub-chatbot.fullname" .)) }}
      key: jwt-secret-key
{{- end }}
