/**
 * API client for Nevron Dashboard
 */

const API_BASE = '/api/v1';

// Types
export interface APIResponse<T> {
	success: boolean;
	data: T;
	message: string;
	errors?: string[];
}

export interface AgentStatus {
	state: string;
	personality: string;
	goal: string;
	mcp_enabled: boolean;
	mcp_connected_servers: number;
	mcp_available_tools: number;
	is_running: boolean;
}

export interface AgentInfo {
	personality: string;
	goal: string;
	state: string;
	available_actions: string[];
	total_actions_executed: number;
	total_rewards: number;
	last_action: string | null;
	last_action_time: string | null;
}

export interface ActionHistoryItem {
	timestamp: string;
	action: string;
	state: string;
	outcome: string | null;
	reward: number | null;
}

export interface AgentContext {
	actions_history: ActionHistoryItem[];
	last_state: string;
	total_actions: number;
	total_rewards: number;
}

export interface RuntimeStatistics {
	state: string;
	started_at: string | null;
	uptime_seconds: number;
	events_processed: number;
	events_failed: number;
	current_queue_size: number;
	last_event_at: string | null;
}

export interface QueueStatistics {
	size: number;
	paused: boolean;
	total_enqueued: number;
	total_dequeued: number;
	total_expired: number;
	by_priority: Record<string, number>;
	by_type: Record<string, number>;
}

export interface SchedulerStatistics {
	tasks_scheduled: number;
	tasks_executed: number;
	next_task: string | null;
	next_run_at: string | null;
}

export interface BackgroundProcess {
	name: string;
	state: string;
	iterations: number;
	errors: number;
	last_run_at: string | null;
	last_error: string | null;
}

export interface BackgroundStatistics {
	processes: BackgroundProcess[];
	total_running: number;
	total_errors: number;
}

export interface FullRuntimeStatistics {
	runtime: RuntimeStatistics;
	queue: QueueStatistics;
	scheduler: SchedulerStatistics;
	background: BackgroundStatistics;
}

export interface MemoryStatistics {
	consolidation_enabled: boolean;
	consolidation_running: boolean;
	last_consolidation: string | null;
	total_skills: number;
	total_concepts: number;
	total_episodes: number;
	total_facts: number;
}

export interface Episode {
	id: string;
	timestamp: string;
	event: string;
	action: string;
	outcome: string;
	emotional_valence: number;
	importance: number;
	context: Record<string, unknown>;
}

export interface Fact {
	id: string;
	subject: string;
	predicate: string;
	object: string;
	confidence: number;
	source: string;
	created_at: string;
}

export interface Concept {
	id: string;
	name: string;
	concept_type: string;
	description: string;
	properties: Record<string, unknown>;
	created_at: string;
}

export interface Skill {
	id: string;
	name: string;
	description: string;
	trigger_pattern: string;
	confidence: number;
	execution_count: number;
	success_count: number;
	action_sequence: string[];
}

export interface LearningStatistics {
	total_actions_tracked: number;
	total_outcomes: number;
	overall_success_rate: number;
	best_performing: string | null;
	worst_performing: string | null;
	lessons_count: number;
	critiques_count: number;
}

export interface LearningOutcome {
	action: string;
	reward: number;
	success: boolean;
	new_success_rate: number;
	bias_change: number;
	critique_generated: boolean;
	lesson_created: boolean;
	timestamp: string;
}

export interface Critique {
	action: string;
	what_went_wrong: string;
	better_approach: string;
	lesson_learned: string;
	confidence: number;
	timestamp: string;
}

export interface ImprovementSuggestion {
	pattern: string;
	suggestion: string;
	affected_actions: string[];
	confidence: number;
}

export interface MetacognitionStatistics {
	state: MonitoringState;
	loop_detector: LoopDetectorStats;
	failure_predictor: FailurePredictorStats;
	human_handoff: HumanHandoffStats;
	total_interventions: number;
	handoff_enabled: boolean;
}

export interface MonitoringState {
	is_stuck: boolean;
	confidence_level: number;
	failure_risk: number;
	intervention_count: number;
	actions_since_intervention: number;
	consecutive_failures: number;
}

export interface LoopDetectorStats {
	current_sequence_length: number;
	max_repetitions_seen: number;
	is_stuck: boolean;
	loop_description: string | null;
}

export interface FailurePredictorStats {
	total_predictions: number;
	high_risk_predictions: number;
	failures_prevented: number;
}

export interface HumanHandoffStats {
	requests_made: number;
	responses_received: number;
	pending_requests: number;
}

export interface Intervention {
	type: string;
	reason: string;
	suggested_action: string;
	wait_seconds: number;
	priority: number;
	alternatives: string[];
	timestamp: string;
}

export interface MCPStatus {
	enabled: boolean;
	initialized: boolean;
	connected_servers: string[];
	total_tools: number;
	servers: MCPServerStatus[];
}

export interface MCPServerStatus {
	name: string;
	connected: boolean;
	tools_count: number;
	transport: string;
}

export interface MCPToolInfo {
	name: string;
	description: string;
	server: string;
	input_schema: Record<string, unknown>;
}

export interface HealthCheck {
	status: string;
	version: string;
	uptime_seconds: number;
	components: Record<string, string>;
}

// UI Config Types
export interface UIConfigResponse {
	llm_provider: string;
	llm_api_key_masked: string;
	llm_model: string;
	agent_personality: string;
	agent_goal: string;
	mcp_enabled: boolean;
	mcp_servers: Record<string, unknown>;
}

export interface UIConfigUpdate {
	llm_provider?: string;
	llm_api_key?: string;
	llm_model?: string;
	agent_personality?: string;
	agent_goal?: string;
	mcp_enabled?: boolean;
	mcp_servers?: Record<string, unknown>;
}

export interface ConfigExistsResponse {
	exists: boolean;
	has_api_key: boolean;
}

export interface ModelsListResponse {
	models: Record<string, string[]>;
}

export interface ValidateKeyResponse {
	valid: boolean;
	message: string;
}

// Available models per provider (for offline use)
export const AVAILABLE_MODELS: Record<string, string[]> = {
	openai: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-3.5-turbo'],
	anthropic: ['claude-3-opus-20240229', 'claude-3-sonnet-20240229', 'claude-3-haiku-20240307'],
	xai: ['grok-2-latest', 'grok-beta'],
	deepseek: ['deepseek-chat', 'deepseek-reasoner'],
	qwen: ['qwen-max', 'qwen-plus', 'qwen-turbo'],
	venice: ['venice-2-13b']
};

// API request helper
async function request<T>(
	endpoint: string,
	options: RequestInit = {}
): Promise<APIResponse<T>> {
	const url = `${API_BASE}${endpoint}`;

	const response = await fetch(url, {
		...options,
		headers: {
			'Content-Type': 'application/json',
			...options.headers
		}
	});

	if (!response.ok) {
		throw new Error(`API error: ${response.status} ${response.statusText}`);
	}

	return response.json();
}

// Agent API
export const agentAPI = {
	getStatus: () => request<AgentStatus>('/agent/status'),
	getInfo: () => request<AgentInfo>('/agent/info'),
	getContext: (limit = 50) => request<AgentContext>(`/agent/context?limit=${limit}`),
	start: () => request<{ status: string }>('/agent/start', { method: 'POST' }),
	stop: () => request<{ status: string }>('/agent/stop', { method: 'POST' }),
	executeAction: (action: string, params?: Record<string, unknown>) =>
		request<{ action: string; success: boolean; outcome: string | null; reward: number }>(
			'/agent/action',
			{
				method: 'POST',
				body: JSON.stringify({ action, params })
			}
		)
};

// Runtime API
export const runtimeAPI = {
	getStatistics: () => request<FullRuntimeStatistics>('/runtime/statistics'),
	getState: () => request<{ state: string; is_running: boolean; is_paused: boolean }>('/runtime/state'),
	getQueue: () => request<QueueStatistics>('/runtime/queue'),
	getScheduler: () => request<{ name: string; next_run: string; run_count: number; is_recurring: boolean }[]>('/runtime/scheduler'),
	getBackground: () => request<BackgroundStatistics>('/runtime/background'),
	start: () => request<{ status: string; state: string }>('/runtime/start', { method: 'POST' }),
	stop: () => request<{ status: string; state: string }>('/runtime/stop', { method: 'POST' }),
	pause: () => request<{ status: string; state: string }>('/runtime/pause', { method: 'POST' }),
	resume: () => request<{ status: string; state: string }>('/runtime/resume', { method: 'POST' })
};

// Memory API
export const memoryAPI = {
	getStatistics: () => request<MemoryStatistics>('/memory/statistics'),
	getEpisodes: (limit = 50, timePeriod?: string) => {
		let url = `/memory/episodes?limit=${limit}`;
		if (timePeriod) url += `&time_period=${encodeURIComponent(timePeriod)}`;
		return request<Episode[]>(url);
	},
	getFacts: (limit = 50, subject?: string) => {
		let url = `/memory/facts?limit=${limit}`;
		if (subject) url += `&subject=${encodeURIComponent(subject)}`;
		return request<Fact[]>(url);
	},
	getConcepts: (limit = 50, conceptType?: string) => {
		let url = `/memory/concepts?limit=${limit}`;
		if (conceptType) url += `&concept_type=${encodeURIComponent(conceptType)}`;
		return request<Concept[]>(url);
	},
	getSkills: (limit = 50, minConfidence = 0) => {
		return request<Skill[]>(`/memory/skills?limit=${limit}&min_confidence=${minConfidence}`);
	},
	recall: (query: string, topK = 10) =>
		request<{
			query: string;
			timestamp: string;
			episodes: Episode[];
			facts: Fact[];
			concepts: Concept[];
			skills: Skill[];
			has_results: boolean;
		}>('/memory/recall', {
			method: 'POST',
			body: JSON.stringify({
				query,
				top_k: topK,
				include_episodes: true,
				include_facts: true,
				include_concepts: true,
				include_skills: true
			})
		}),
	consolidate: () =>
		request<{
			episodes_processed: number;
			facts_created: number;
			skills_updated: number;
			duration_seconds: number;
		}>('/memory/consolidate', { method: 'POST' })
};

// Learning API
export const learningAPI = {
	getStatistics: () => request<LearningStatistics>('/learning/statistics'),
	getHistory: (limit = 50, action?: string) => {
		let url = `/learning/history?limit=${limit}`;
		if (action) url += `&action=${encodeURIComponent(action)}`;
		return request<LearningOutcome[]>(url);
	},
	getCritiques: (limit = 20) => request<Critique[]>(`/learning/critiques?limit=${limit}`),
	getFailingActions: (threshold = 0.3) =>
		request<{ action: string; stats: Record<string, unknown>; recent_errors: string[] }[]>(
			`/learning/failing-actions?threshold=${threshold}`
		),
	getSuggestions: () => request<ImprovementSuggestion[]>('/learning/suggestions'),
	analyzeFailures: () => request<ImprovementSuggestion[]>('/learning/analyze-failures', { method: 'POST' })
};

// Metacognition API
export const metacognitionAPI = {
	getStatistics: () => request<MetacognitionStatistics>('/metacognition/statistics'),
	getState: () => request<MonitoringState>('/metacognition/state'),
	getInterventions: (limit = 50) => request<Intervention[]>(`/metacognition/interventions?limit=${limit}`),
	getLoopDetector: () => request<LoopDetectorStats>('/metacognition/loop-detector'),
	predictFailure: (action: string, context: Record<string, unknown> = {}) =>
		request<{
			action: string;
			probability: number;
			is_high_risk: boolean;
			reason_details: string[];
			suggested_alternatives: string[];
			wait_seconds: number;
		}>('/metacognition/predict-failure', {
			method: 'POST',
			body: JSON.stringify({ action, context })
		}),
	clear: () => request<{ status: string }>('/metacognition/clear', { method: 'POST' })
};

// MCP API
export const mcpAPI = {
	getStatus: () => request<MCPStatus>('/mcp/status'),
	getServers: () => request<MCPServerStatus[]>('/mcp/servers'),
	getTools: (server?: string) => {
		let url = '/mcp/tools';
		if (server) url += `?server=${encodeURIComponent(server)}`;
		return request<MCPToolInfo[]>(url);
	},
	getToolInfo: (toolName: string) => request<MCPToolInfo>(`/mcp/tools/${toolName}`),
	reconnectServer: (serverName: string) =>
		request<{ server: string; reconnected: boolean; tools_discovered?: number }>(
			`/mcp/servers/${serverName}/reconnect`,
			{ method: 'POST' }
		),
	executeTool: (toolName: string, args: Record<string, unknown> = {}) =>
		request<{
			tool: string;
			success: boolean;
			content: Record<string, unknown>[];
			error: string | null;
			execution_time: number;
		}>(`/mcp/tools/${toolName}/execute`, {
			method: 'POST',
			body: JSON.stringify({ arguments: args })
		})
};

// Health API
export const healthAPI = {
	check: async (): Promise<HealthCheck> => {
		const response = await fetch('/health');
		return response.json();
	}
};

// Config API
export const configAPI = {
	getUIConfig: () => request<UIConfigResponse>('/config/ui'),
	saveUIConfig: (config: UIConfigUpdate) =>
		request<UIConfigResponse>('/config/ui', {
			method: 'PUT',
			body: JSON.stringify(config)
		}),
	checkConfigExists: () => request<ConfigExistsResponse>('/config/ui/exists'),
	validateApiKey: (provider: string, apiKey: string, model?: string) =>
		request<ValidateKeyResponse>('/config/ui/validate', {
			method: 'POST',
			body: JSON.stringify({ provider, api_key: apiKey, model })
		}),
	getAvailableModels: () => request<ModelsListResponse>('/config/ui/models')
};
