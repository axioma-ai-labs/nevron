<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import Card from '$lib/components/Card.svelte';
	import StatCard from '$lib/components/StatCard.svelte';
	import EventFeed from '$lib/components/EventFeed.svelte';
	import {
		agentAPI,
		runtimeAPI,
		memoryAPI,
		learningAPI,
		configAPI,
		type AgentStatus,
		type FullRuntimeStatistics,
		type MemoryStatistics,
		type LearningStatistics
	} from '$lib/api/client';

	let agentStatus = $state<AgentStatus | null>(null);
	let runtimeStats = $state<FullRuntimeStatistics | null>(null);
	let memoryStats = $state<MemoryStatistics | null>(null);
	let learningStats = $state<LearningStatistics | null>(null);
	let loading = $state(true);
	let actionLoading = $state(false);
	let error = $state<string | null>(null);
	let showConfigWarning = $state(false);
	let hasApiKey = $state(false);
	let refreshInterval: ReturnType<typeof setInterval>;

	onMount(() => {
		checkConfig();
		fetchAllData();
		refreshInterval = setInterval(fetchAllData, 10000);
	});

	onDestroy(() => {
		if (refreshInterval) clearInterval(refreshInterval);
	});

	async function checkConfig() {
		try {
			const res = await configAPI.checkConfigExists();
			if (res.data) {
				showConfigWarning = !res.data.exists || !res.data.has_api_key;
				hasApiKey = res.data.has_api_key;
			}
		} catch (e) {
			// Config check failed, show warning
			showConfigWarning = true;
			hasApiKey = false;
		}
	}

	async function fetchAllData() {
		try {
			const [agentRes, runtimeRes, memoryRes, learningRes] = await Promise.all([
				agentAPI.getStatus().catch(() => null),
				runtimeAPI.getStatistics().catch(() => null),
				memoryAPI.getStatistics().catch(() => null),
				learningAPI.getStatistics().catch(() => null)
			]);

			if (agentRes?.data) agentStatus = agentRes.data;
			if (runtimeRes?.data) runtimeStats = runtimeRes.data;
			if (memoryRes?.data) memoryStats = memoryRes.data;
			if (learningRes?.data) learningStats = learningRes.data;

			loading = false;
			error = null;
		} catch (e) {
			loading = false;
			error = e instanceof Error ? e.message : 'Failed to fetch data';
		}
	}

	async function startAgent() {
		actionLoading = true;
		try {
			await runtimeAPI.start();
			await fetchAllData();
		} catch (e) {
			console.error('Failed to start agent:', e);
		}
		actionLoading = false;
	}

	async function stopAgent() {
		actionLoading = true;
		try {
			await runtimeAPI.stop();
			await fetchAllData();
		} catch (e) {
			console.error('Failed to stop agent:', e);
		}
		actionLoading = false;
	}

	async function pauseAgent() {
		actionLoading = true;
		try {
			await runtimeAPI.pause();
			await fetchAllData();
		} catch (e) {
			console.error('Failed to pause agent:', e);
		}
		actionLoading = false;
	}

	function formatUptime(seconds: number): string {
		const hours = Math.floor(seconds / 3600);
		const minutes = Math.floor((seconds % 3600) / 60);
		if (hours > 0) return `${hours}h ${minutes}m`;
		return `${minutes}m`;
	}

	function getStateBadgeClass(state: string): string {
		switch (state) {
			case 'running':
				return 'badge-success';
			case 'paused':
				return 'badge-warning';
			case 'stopped':
				return 'badge-danger';
			default:
				return 'badge-info';
		}
	}

	function getStateIcon(state: string): string {
		switch (state) {
			case 'running':
				return 'M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z';
			case 'paused':
				return 'M10 9v6m4-6v6';
			case 'stopped':
				return 'M21 12a9 9 0 11-18 0 9 9 0 0118 0z';
			default:
				return 'M12 8v4m0 4h.01';
		}
	}

	let totalMemories = $derived(
		memoryStats
			? memoryStats.total_episodes + memoryStats.total_facts + memoryStats.total_concepts + memoryStats.total_skills
			: 0
	);
</script>

<div class="space-y-6">
	<!-- Config Warning Banner -->
	{#if showConfigWarning}
		<div class="card-static border-l-4 border-l-apple-orange bg-apple-orange/5">
			<div class="flex items-start gap-3">
				<svg class="w-5 h-5 text-apple-orange flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
				</svg>
				<div class="flex-1">
					<p class="font-medium text-apple-text-primary">Configuration Required</p>
					<p class="text-sm text-apple-text-secondary mt-1">
						{#if !hasApiKey}
							Please configure your LLM API key in <a href="/settings" class="text-apple-blue hover:underline">Settings</a> before starting the agent.
						{:else}
							Some settings may be missing. Visit <a href="/settings" class="text-apple-blue hover:underline">Settings</a> to review your configuration.
						{/if}
					</p>
				</div>
			</div>
		</div>
	{/if}

	<!-- Error Banner -->
	{#if error}
		<div class="card-static border-l-4 border-l-apple-red bg-apple-red/5">
			<div class="flex items-start gap-3">
				<svg class="w-5 h-5 text-apple-red flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
				</svg>
				<div>
					<p class="font-medium text-apple-text-primary">Connection Error</p>
					<p class="text-sm text-apple-text-secondary mt-1">{error}</p>
				</div>
			</div>
		</div>
	{/if}

	<!-- Agent Status Hero Card -->
	<Card>
		<div class="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
			<!-- Left: Status Info -->
			<div class="flex items-center gap-5">
				<!-- Status Icon -->
				<div class="w-20 h-20 rounded-apple-lg bg-gradient-to-br from-apple-blue to-apple-indigo flex items-center justify-center shadow-apple glow-blue">
					{#if runtimeStats?.runtime}
						<svg class="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d={getStateIcon(runtimeStats.runtime.state)}/>
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
						</svg>
					{:else}
						<svg class="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/>
						</svg>
					{/if}
				</div>
				<!-- Status Text -->
				<div>
					<div class="flex items-center gap-3 mb-2">
						<h2 class="text-3xl font-bold text-apple-text-primary tracking-tight capitalize">
							{runtimeStats?.runtime?.state || 'Unknown'}
						</h2>
						{#if runtimeStats?.runtime}
							<span class="badge {getStateBadgeClass(runtimeStats.runtime.state)} text-sm px-3 py-1">
								{runtimeStats.runtime.state}
							</span>
						{/if}
					</div>
					<p class="text-apple-text-secondary">
						{#if runtimeStats?.runtime?.state === 'running'}
							Agent is actively processing events
						{:else if runtimeStats?.runtime?.state === 'paused'}
							Agent is paused, events are queued
						{:else}
							Agent is stopped
						{/if}
					</p>
					{#if runtimeStats?.runtime && runtimeStats.runtime.uptime_seconds > 0}
						<p class="text-sm text-apple-text-tertiary mt-1">
							Uptime: <span class="font-mono">{formatUptime(runtimeStats.runtime.uptime_seconds)}</span>
						</p>
					{/if}
				</div>
			</div>

			<!-- Right: Control Buttons -->
			<div class="flex gap-3">
				<button
					class="btn btn-success px-6 py-3"
					onclick={startAgent}
					disabled={actionLoading || !hasApiKey || runtimeStats?.runtime?.state === 'running'}
					title={!hasApiKey ? 'Configure API key first' : ''}
				>
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/>
					</svg>
					Start
				</button>
				<button
					class="btn btn-secondary px-6 py-3"
					onclick={pauseAgent}
					disabled={actionLoading || runtimeStats?.runtime?.state !== 'running'}
				>
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 9v6m4-6v6"/>
					</svg>
					Pause
				</button>
			</div>
		</div>
	</Card>

	<!-- Stats Grid -->
	<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
		<StatCard
			label="Events Processed"
			value={runtimeStats?.runtime?.events_processed ?? '-'}
			icon="actions"
		/>
		<StatCard
			label="Success Rate"
			value={learningStats?.overall_success_rate
				? `${(learningStats.overall_success_rate * 100).toFixed(1)}%`
				: '-'}
			icon="success"
		/>
		<StatCard
			label="Uptime"
			value={runtimeStats?.runtime ? formatUptime(runtimeStats.runtime.uptime_seconds) : '-'}
			icon="actions"
		/>
		<StatCard
			label="Memories"
			value={totalMemories || '-'}
			icon="memory"
		/>
	</div>

	<!-- Agent Info -->
	{#if agentStatus}
		<Card>
			<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
				<div>
					<p class="text-xs text-apple-text-tertiary uppercase tracking-wider font-medium">Personality</p>
					<p class="text-apple-text-primary mt-2">{agentStatus.personality}</p>
				</div>
				<div>
					<p class="text-xs text-apple-text-tertiary uppercase tracking-wider font-medium">Goal</p>
					<p class="text-apple-text-primary mt-2">{agentStatus.goal}</p>
				</div>
			</div>
		</Card>
	{/if}

	<!-- Live Events -->
	<EventFeed maxItems={15} />
</div>
