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
		mcpAPI,
		type AgentStatus,
		type FullRuntimeStatistics,
		type MemoryStatistics,
		type LearningStatistics,
		type MCPStatus
	} from '$lib/api/client';

	let agentStatus: AgentStatus | null = $state(null);
	let runtimeStats: FullRuntimeStatistics | null = $state(null);
	let memoryStats: MemoryStatistics | null = $state(null);
	let learningStats: LearningStatistics | null = $state(null);
	let mcpStatus: MCPStatus | null = $state(null);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let refreshInterval: ReturnType<typeof setInterval>;

	onMount(() => {
		fetchAllData();
		refreshInterval = setInterval(fetchAllData, 10000);
	});

	onDestroy(() => {
		if (refreshInterval) clearInterval(refreshInterval);
	});

	async function fetchAllData() {
		try {
			const [agentRes, runtimeRes, memoryRes, learningRes, mcpRes] = await Promise.all([
				agentAPI.getStatus().catch(() => null),
				runtimeAPI.getStatistics().catch(() => null),
				memoryAPI.getStatistics().catch(() => null),
				learningAPI.getStatistics().catch(() => null),
				mcpAPI.getStatus().catch(() => null)
			]);

			if (agentRes?.data) agentStatus = agentRes.data;
			if (runtimeRes?.data) runtimeStats = runtimeRes.data;
			if (memoryRes?.data) memoryStats = memoryRes.data;
			if (learningRes?.data) learningStats = learningRes.data;
			if (mcpRes?.data) mcpStatus = mcpRes.data;

			loading = false;
			error = null;
		} catch (e) {
			loading = false;
			error = e instanceof Error ? e.message : 'Failed to fetch data';
		}
	}

	function formatUptime(seconds: number): string {
		const hours = Math.floor(seconds / 3600);
		const minutes = Math.floor((seconds % 3600) / 60);
		if (hours > 0) return `${hours}h ${minutes}m`;
		return `${minutes}m`;
	}

	function getStateColor(state: string): string {
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
</script>

<div class="space-y-6">
	<!-- Status Banner -->
	{#if error}
		<div class="bg-red-900/50 border border-red-700 rounded-lg p-4 text-red-200">
			<p class="font-medium">Connection Error</p>
			<p class="text-sm mt-1">{error}</p>
		</div>
	{/if}

	<!-- Agent Status Card -->
	<Card>
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-4">
				<div
					class="w-12 h-12 rounded-lg bg-gradient-to-br from-accent-500 to-accent-700 flex items-center justify-center"
				>
					<svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
						/>
					</svg>
				</div>
				<div>
					<h2 class="text-xl font-bold text-white">Nevron Agent</h2>
					<p class="text-sm text-slate-400">
						{agentStatus?.personality || 'Loading...'}
					</p>
				</div>
			</div>
			<div class="flex items-center gap-4">
				{#if agentStatus}
					<span class="badge {getStateColor(agentStatus.state)}">{agentStatus.state}</span>
				{/if}
				{#if runtimeStats?.runtime}
					<span class="text-sm text-slate-400">
						Uptime: {formatUptime(runtimeStats.runtime.uptime_seconds)}
					</span>
				{/if}
			</div>
		</div>
		{#if agentStatus?.goal}
			<div class="mt-4 p-3 bg-surface-800 rounded-lg">
				<p class="text-sm text-slate-400">Current Goal:</p>
				<p class="text-white mt-1">{agentStatus.goal}</p>
			</div>
		{/if}
	</Card>

	<!-- Stats Grid -->
	<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
		<StatCard
			label="Events Processed"
			value={runtimeStats?.runtime?.events_processed ?? '-'}
			icon="actions"
		/>
		<StatCard
			label="Total Memories"
			value={memoryStats
				? memoryStats.total_episodes +
					memoryStats.total_facts +
					memoryStats.total_concepts +
					memoryStats.total_skills
				: '-'}
			icon="memory"
		/>
		<StatCard
			label="Success Rate"
			value={learningStats?.overall_success_rate
				? `${(learningStats.overall_success_rate * 100).toFixed(1)}%`
				: '-'}
			icon="success"
		/>
		<StatCard label="MCP Tools" value={mcpStatus?.total_tools ?? '-'} icon="tools" />
	</div>

	<!-- Two Column Layout -->
	<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
		<!-- Runtime Overview -->
		<Card title="Runtime Overview">
			{#if loading}
				<div class="animate-pulse space-y-3">
					<div class="h-4 bg-surface-700 rounded w-3/4"></div>
					<div class="h-4 bg-surface-700 rounded w-1/2"></div>
					<div class="h-4 bg-surface-700 rounded w-2/3"></div>
				</div>
			{:else if runtimeStats}
				<div class="space-y-4">
					<div class="flex justify-between items-center">
						<span class="text-slate-400">Queue Size</span>
						<span class="text-white font-medium">{runtimeStats.queue.size}</span>
					</div>
					<div class="flex justify-between items-center">
						<span class="text-slate-400">Events Failed</span>
						<span class="text-white font-medium">{runtimeStats.runtime.events_failed}</span>
					</div>
					<div class="flex justify-between items-center">
						<span class="text-slate-400">Scheduled Tasks</span>
						<span class="text-white font-medium">{runtimeStats.scheduler.tasks_scheduled}</span>
					</div>
					<div class="flex justify-between items-center">
						<span class="text-slate-400">Background Processes</span>
						<span class="text-white font-medium">
							{runtimeStats.background.total_running} running
						</span>
					</div>
				</div>
			{:else}
				<p class="text-slate-500">No data available</p>
			{/if}
		</Card>

		<!-- Memory Breakdown -->
		<Card title="Memory Breakdown">
			{#if loading}
				<div class="animate-pulse space-y-3">
					<div class="h-4 bg-surface-700 rounded w-3/4"></div>
					<div class="h-4 bg-surface-700 rounded w-1/2"></div>
					<div class="h-4 bg-surface-700 rounded w-2/3"></div>
				</div>
			{:else if memoryStats}
				<div class="space-y-4">
					<div class="flex justify-between items-center">
						<span class="text-slate-400">Episodes</span>
						<span class="text-white font-medium">{memoryStats.total_episodes}</span>
					</div>
					<div class="flex justify-between items-center">
						<span class="text-slate-400">Facts</span>
						<span class="text-white font-medium">{memoryStats.total_facts}</span>
					</div>
					<div class="flex justify-between items-center">
						<span class="text-slate-400">Concepts</span>
						<span class="text-white font-medium">{memoryStats.total_concepts}</span>
					</div>
					<div class="flex justify-between items-center">
						<span class="text-slate-400">Skills</span>
						<span class="text-white font-medium">{memoryStats.total_skills}</span>
					</div>
					<div class="flex justify-between items-center">
						<span class="text-slate-400">Consolidation</span>
						<span class="badge {memoryStats.consolidation_running ? 'badge-warning' : 'badge-info'}">
							{memoryStats.consolidation_running ? 'Running' : 'Idle'}
						</span>
					</div>
				</div>
			{:else}
				<p class="text-slate-500">No data available</p>
			{/if}
		</Card>
	</div>

	<!-- Live Events -->
	<EventFeed maxItems={15} />
</div>
