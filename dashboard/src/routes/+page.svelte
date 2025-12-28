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
</script>

<div class="space-y-6">
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

	<!-- Agent Hero Card -->
	<Card>
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-5">
				<!-- Agent Icon -->
				<div class="w-14 h-14 rounded-apple-lg bg-gradient-to-br from-apple-blue to-apple-indigo flex items-center justify-center shadow-apple glow-blue">
					<svg class="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="1.5"
							d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
						/>
					</svg>
				</div>
				<!-- Agent Info -->
				<div>
					<h2 class="text-2xl font-semibold text-apple-text-primary tracking-tight">Nevron Agent</h2>
					<p class="text-sm text-apple-text-secondary mt-1">
						{agentStatus?.personality || 'Loading personality...'}
					</p>
				</div>
			</div>
			<!-- Status -->
			<div class="flex items-center gap-4">
				{#if agentStatus}
					<span class="badge {getStateBadgeClass(agentStatus.state)} text-sm px-3">{agentStatus.state}</span>
				{/if}
				{#if runtimeStats?.runtime}
					<div class="text-right">
						<p class="text-xs text-apple-text-tertiary">Uptime</p>
						<p class="text-sm font-mono text-apple-text-secondary">{formatUptime(runtimeStats.runtime.uptime_seconds)}</p>
					</div>
				{/if}
			</div>
		</div>
		{#if agentStatus?.goal}
			<div class="mt-5 p-4 bg-apple-bg-tertiary rounded-apple-md">
				<p class="text-xs text-apple-text-tertiary uppercase tracking-wider font-medium">Current Goal</p>
				<p class="text-apple-text-primary mt-2">{agentStatus.goal}</p>
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
				<div class="space-y-4">
					{#each Array(4) as _}
						<div class="skeleton h-5 w-full"></div>
					{/each}
				</div>
			{:else if runtimeStats}
				<div class="space-y-4">
					<div class="flex justify-between items-center py-2 border-b border-apple-border-subtle">
						<span class="text-apple-text-secondary">Queue Size</span>
						<span class="text-apple-text-primary font-mono font-medium">{runtimeStats.queue.size}</span>
					</div>
					<div class="flex justify-between items-center py-2 border-b border-apple-border-subtle">
						<span class="text-apple-text-secondary">Events Failed</span>
						<span class="text-apple-text-primary font-mono font-medium">{runtimeStats.runtime.events_failed}</span>
					</div>
					<div class="flex justify-between items-center py-2 border-b border-apple-border-subtle">
						<span class="text-apple-text-secondary">Scheduled Tasks</span>
						<span class="text-apple-text-primary font-mono font-medium">{runtimeStats.scheduler.tasks_scheduled}</span>
					</div>
					<div class="flex justify-between items-center py-2">
						<span class="text-apple-text-secondary">Background Processes</span>
						<span class="text-apple-text-primary font-mono font-medium">
							{runtimeStats.background.total_running} running
						</span>
					</div>
				</div>
			{:else}
				<p class="text-apple-text-tertiary text-center py-8">No data available</p>
			{/if}
		</Card>

		<!-- Memory Breakdown -->
		<Card title="Memory Breakdown">
			{#if loading}
				<div class="space-y-4">
					{#each Array(5) as _}
						<div class="skeleton h-5 w-full"></div>
					{/each}
				</div>
			{:else if memoryStats}
				<div class="space-y-4">
					<div class="flex justify-between items-center py-2 border-b border-apple-border-subtle">
						<span class="text-apple-text-secondary">Episodes</span>
						<span class="text-apple-text-primary font-mono font-medium">{memoryStats.total_episodes}</span>
					</div>
					<div class="flex justify-between items-center py-2 border-b border-apple-border-subtle">
						<span class="text-apple-text-secondary">Facts</span>
						<span class="text-apple-text-primary font-mono font-medium">{memoryStats.total_facts}</span>
					</div>
					<div class="flex justify-between items-center py-2 border-b border-apple-border-subtle">
						<span class="text-apple-text-secondary">Concepts</span>
						<span class="text-apple-text-primary font-mono font-medium">{memoryStats.total_concepts}</span>
					</div>
					<div class="flex justify-between items-center py-2 border-b border-apple-border-subtle">
						<span class="text-apple-text-secondary">Skills</span>
						<span class="text-apple-text-primary font-mono font-medium">{memoryStats.total_skills}</span>
					</div>
					<div class="flex justify-between items-center py-2">
						<span class="text-apple-text-secondary">Consolidation</span>
						<span class="badge {memoryStats.consolidation_running ? 'badge-warning' : 'badge-neutral'}">
							{memoryStats.consolidation_running ? 'Running' : 'Idle'}
						</span>
					</div>
				</div>
			{:else}
				<p class="text-apple-text-tertiary text-center py-8">No data available</p>
			{/if}
		</Card>
	</div>

	<!-- Live Events -->
	<EventFeed maxItems={15} />
</div>
