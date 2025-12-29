<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import Card from '$lib/components/Card.svelte';
	import { cyclesAPI, type CycleLog, type CycleStats } from '$lib/api/client';
	import { websocketStore } from '$lib/stores/websocket';

	// State
	let loading = $state(true);
	let cycles = $state<CycleLog[]>([]);
	let stats = $state<CycleStats | null>(null);
	let expandedCycleId = $state<string | null>(null);

	// Filters
	let actionFilter = $state<string | null>(null);
	let successFilter = $state<boolean | null>(null);
	let page = $state(1);
	let hasMore = $state(false);

	// Real-time updates
	let autoRefresh = $state(true);
	let refreshInterval: ReturnType<typeof setInterval> | null = null;

	// Unique actions for filter dropdown
	let uniqueActions = $derived(() => {
		const actions = new Set<string>();
		cycles.forEach((c) => actions.add(c.action_name));
		return Array.from(actions).sort();
	});

	onMount(async () => {
		await loadData();
		websocketStore.connect();

		// Auto-refresh every 10 seconds if enabled
		if (autoRefresh) {
			refreshInterval = setInterval(() => {
				if (autoRefresh) {
					loadCycles();
					loadStats();
				}
			}, 10000);
		}
	});

	onDestroy(() => {
		if (refreshInterval) {
			clearInterval(refreshInterval);
		}
	});

	async function loadData() {
		loading = true;
		await Promise.all([loadCycles(), loadStats()]);
		loading = false;
	}

	async function loadCycles() {
		try {
			const res = await cyclesAPI.getCycles(
				page,
				50,
				actionFilter || undefined,
				successFilter ?? undefined
			);
			if (res.data) {
				cycles = res.data.cycles;
				hasMore = res.data.has_more;
			}
		} catch (e) {
			console.error('Failed to load cycles:', e);
		}
	}

	async function loadStats() {
		try {
			const res = await cyclesAPI.getStats();
			if (res.data) {
				stats = res.data;
			}
		} catch (e) {
			console.error('Failed to load stats:', e);
		}
	}

	function toggleExpand(cycleId: string) {
		if (expandedCycleId === cycleId) {
			expandedCycleId = null;
		} else {
			expandedCycleId = cycleId;
		}
	}

	function formatDuration(ms: number): string {
		if (ms < 1000) return `${ms}ms`;
		if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
		return `${(ms / 60000).toFixed(1)}m`;
	}

	function formatTime(timestamp: string): string {
		const date = new Date(timestamp);
		return date.toLocaleTimeString('en-US', {
			hour: '2-digit',
			minute: '2-digit',
			second: '2-digit',
			hour12: false
		});
	}

	function formatDate(timestamp: string): string {
		const date = new Date(timestamp);
		return date.toLocaleDateString('en-US', {
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function getActionDisplay(action: string): string {
		return action.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
	}

	async function handleFilterChange() {
		page = 1;
		await loadCycles();
	}

	async function loadMore() {
		page += 1;
		try {
			const res = await cyclesAPI.getCycles(
				page,
				50,
				actionFilter || undefined,
				successFilter ?? undefined
			);
			if (res.data) {
				cycles = [...cycles, ...res.data.cycles];
				hasMore = res.data.has_more;
			}
		} catch (e) {
			console.error('Failed to load more cycles:', e);
		}
	}

	function toggleAutoRefresh() {
		autoRefresh = !autoRefresh;
		if (autoRefresh && !refreshInterval) {
			refreshInterval = setInterval(() => {
				if (autoRefresh) {
					loadCycles();
					loadStats();
				}
			}, 10000);
		} else if (!autoRefresh && refreshInterval) {
			clearInterval(refreshInterval);
			refreshInterval = null;
		}
	}
</script>

<div class="space-y-6">
	<!-- Header -->
	<div class="flex items-center justify-between">
		<div>
			<h1 class="text-2xl font-bold text-apple-text-primary tracking-tight">Activity</h1>
			<p class="text-apple-text-secondary mt-1">Monitor agent cycles and performance</p>
		</div>
		<div class="flex items-center gap-4">
			<button
				class="btn {autoRefresh ? 'btn-primary' : 'btn-secondary'}"
				onclick={toggleAutoRefresh}
			>
				{autoRefresh ? 'Auto-refresh ON' : 'Auto-refresh OFF'}
			</button>
			<button class="btn btn-secondary" onclick={loadData}>Refresh</button>
		</div>
	</div>

	{#if loading}
		<div class="grid grid-cols-4 gap-4">
			{#each Array(4) as _}
				<Card>
					<div class="skeleton h-16 w-full"></div>
				</Card>
			{/each}
		</div>
		<Card>
			<div class="space-y-4">
				{#each Array(5) as _}
					<div class="skeleton h-20 w-full"></div>
				{/each}
			</div>
		</Card>
	{:else}
		<!-- Stats Grid -->
		{#if stats}
			<div class="grid grid-cols-2 md:grid-cols-4 gap-4">
				<Card>
					<div class="text-center">
						<p class="text-3xl font-bold text-apple-text-primary">{stats.total_cycles}</p>
						<p class="text-sm text-apple-text-secondary mt-1">Total Cycles</p>
					</div>
				</Card>
				<Card>
					<div class="text-center">
						<p
							class="text-3xl font-bold {stats.success_rate >= 80
								? 'text-apple-green'
								: stats.success_rate >= 50
									? 'text-apple-orange'
									: 'text-apple-red'}"
						>
							{stats.success_rate.toFixed(1)}%
						</p>
						<p class="text-sm text-apple-text-secondary mt-1">Success Rate</p>
					</div>
				</Card>
				<Card>
					<div class="text-center">
						<p class="text-3xl font-bold text-apple-text-primary">
							{formatDuration(stats.avg_duration_ms)}
						</p>
						<p class="text-sm text-apple-text-secondary mt-1">Avg Duration</p>
					</div>
				</Card>
				<Card>
					<div class="text-center">
						<p class="text-3xl font-bold text-apple-text-primary">
							{stats.cycles_per_hour.toFixed(1)}
						</p>
						<p class="text-sm text-apple-text-secondary mt-1">Cycles/Hour</p>
					</div>
				</Card>
			</div>

			<!-- Top Actions -->
			{#if stats.top_actions.length > 0}
				<Card title="Top Actions">
					<div class="flex flex-wrap gap-2">
						{#each stats.top_actions as action}
							<span
								class="px-3 py-1 bg-apple-bg-tertiary rounded-full text-sm text-apple-text-secondary"
							>
								{getActionDisplay(action)}
								<span class="ml-1 text-apple-text-tertiary">
									({stats.action_counts[action]})
								</span>
							</span>
						{/each}
					</div>
				</Card>
			{/if}
		{/if}

		<!-- Filters -->
		<Card>
			<div class="flex flex-wrap gap-4">
				<div>
					<label class="block text-sm text-apple-text-secondary mb-1" for="action-filter">Action</label>
					<select id="action-filter" class="input" bind:value={actionFilter} onchange={handleFilterChange}>
						<option value={null}>All Actions</option>
						{#each uniqueActions() as action}
							<option value={action}>{getActionDisplay(action)}</option>
						{/each}
					</select>
				</div>
				<div>
					<label class="block text-sm text-apple-text-secondary mb-1" for="status-filter">Status</label>
					<select
						id="status-filter"
						class="input"
						bind:value={successFilter}
						onchange={handleFilterChange}
					>
						<option value={null}>All</option>
						<option value={true}>Success</option>
						<option value={false}>Failed</option>
					</select>
				</div>
			</div>
		</Card>

		<!-- Cycles List -->
		<Card title="Recent Cycles">
			{#if cycles.length === 0}
				<div class="text-center py-12">
					<p class="text-apple-text-tertiary">No cycles recorded yet.</p>
					<p class="text-sm text-apple-text-tertiary mt-2">
						Start the agent to see activity here.
					</p>
				</div>
			{:else}
				<div class="space-y-3">
					{#each cycles as cycle}
						<div
							class="border border-apple-border-subtle rounded-lg overflow-hidden transition-all"
						>
							<!-- Cycle Header -->
							<button
								class="w-full px-4 py-3 flex items-center justify-between hover:bg-apple-bg-secondary transition-colors text-left"
								onclick={() => toggleExpand(cycle.cycle_id)}
							>
								<div class="flex items-center gap-4">
									<!-- Status Indicator -->
									<div
										class="w-3 h-3 rounded-full {cycle.execution_success
											? 'bg-apple-green'
											: 'bg-apple-red'}"
									></div>

									<!-- Action Name -->
									<div>
										<p class="font-medium text-apple-text-primary">
											{getActionDisplay(cycle.action_name)}
										</p>
										<p class="text-xs text-apple-text-tertiary">
											{formatDate(cycle.timestamp)}
										</p>
									</div>
								</div>

								<div class="flex items-center gap-6">
									<!-- Duration -->
									<div class="text-right">
										<p class="text-sm font-medium text-apple-text-primary">
											{formatDuration(cycle.total_duration_ms)}
										</p>
										<p class="text-xs text-apple-text-tertiary">duration</p>
									</div>

									<!-- Reward -->
									<div class="text-right">
										<p
											class="text-sm font-medium {cycle.reward > 0
												? 'text-apple-green'
												: cycle.reward < 0
													? 'text-apple-red'
													: 'text-apple-text-primary'}"
										>
											{cycle.reward > 0 ? '+' : ''}{cycle.reward.toFixed(2)}
										</p>
										<p class="text-xs text-apple-text-tertiary">reward</p>
									</div>

									<!-- Expand Icon -->
									<svg
										class="w-5 h-5 text-apple-text-tertiary transition-transform {expandedCycleId ===
										cycle.cycle_id
											? 'rotate-180'
											: ''}"
										fill="none"
										stroke="currentColor"
										viewBox="0 0 24 24"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M19 9l-7 7-7-7"
										/>
									</svg>
								</div>
							</button>

							<!-- Expanded Details -->
							{#if expandedCycleId === cycle.cycle_id}
								<div class="px-4 py-4 border-t border-apple-border-subtle bg-apple-bg-secondary">
									<div class="grid grid-cols-2 gap-6">
										<!-- Left Column -->
										<div class="space-y-4">
											<div>
												<p class="text-xs font-semibold text-apple-text-tertiary uppercase mb-1">
													Cycle ID
												</p>
												<p class="text-sm text-apple-text-primary font-mono">
													{cycle.cycle_id}
												</p>
											</div>

											<div>
												<p class="text-xs font-semibold text-apple-text-tertiary uppercase mb-1">
													State Before
												</p>
												<p class="text-sm text-apple-text-primary">
													{cycle.planning_input_state}
												</p>
											</div>

											<div>
												<p class="text-xs font-semibold text-apple-text-tertiary uppercase mb-1">
													State After
												</p>
												<p class="text-sm text-apple-text-primary">
													{cycle.agent_state_after || 'N/A'}
												</p>
											</div>

											{#if cycle.planning_output_reasoning}
												<div>
													<p
														class="text-xs font-semibold text-apple-text-tertiary uppercase mb-1"
													>
														Planning Reasoning
													</p>
													<p class="text-sm text-apple-text-secondary">
														{cycle.planning_output_reasoning}
													</p>
												</div>
											{/if}
										</div>

										<!-- Right Column -->
										<div class="space-y-4">
											<div>
												<p class="text-xs font-semibold text-apple-text-tertiary uppercase mb-1">
													Timing Breakdown
												</p>
												<div class="space-y-1">
													<div class="flex justify-between text-sm">
														<span class="text-apple-text-secondary">Planning</span>
														<span class="text-apple-text-primary">
															{formatDuration(cycle.planning_duration_ms)}
														</span>
													</div>
													<div class="flex justify-between text-sm">
														<span class="text-apple-text-secondary">Execution</span>
														<span class="text-apple-text-primary">
															{formatDuration(cycle.execution_duration_ms)}
														</span>
													</div>
												</div>
											</div>

											{#if cycle.execution_error}
												<div>
													<p
														class="text-xs font-semibold text-apple-text-tertiary uppercase mb-1"
													>
														Error
													</p>
													<p class="text-sm text-apple-red">{cycle.execution_error}</p>
												</div>
											{/if}

											{#if cycle.execution_result && Object.keys(cycle.execution_result).length > 0}
												<div>
													<p
														class="text-xs font-semibold text-apple-text-tertiary uppercase mb-1"
													>
														Result
													</p>
													<pre
														class="text-xs text-apple-text-secondary bg-apple-bg-tertiary p-2 rounded overflow-x-auto">{JSON.stringify(cycle.execution_result, null, 2)}</pre>
												</div>
											{/if}

											{#if cycle.critique}
												<div>
													<p
														class="text-xs font-semibold text-apple-text-tertiary uppercase mb-1"
													>
														Critique
													</p>
													<p class="text-sm text-apple-text-secondary">{cycle.critique}</p>
												</div>
											{/if}

											{#if cycle.lesson_learned}
												<div>
													<p
														class="text-xs font-semibold text-apple-text-tertiary uppercase mb-1"
													>
														Lesson Learned
													</p>
													<p class="text-sm text-apple-text-secondary">{cycle.lesson_learned}</p>
												</div>
											{/if}
										</div>
									</div>

									{#if cycle.planning_input_recent_actions.length > 0}
										<div class="mt-4 pt-4 border-t border-apple-border-subtle">
											<p class="text-xs font-semibold text-apple-text-tertiary uppercase mb-2">
												Recent Actions Context
											</p>
											<div class="flex flex-wrap gap-2">
												{#each cycle.planning_input_recent_actions as action}
													<span
														class="px-2 py-1 bg-apple-bg-tertiary rounded text-xs text-apple-text-secondary"
													>
														{getActionDisplay(action)}
													</span>
												{/each}
											</div>
										</div>
									{/if}
								</div>
							{/if}
						</div>
					{/each}
				</div>

				{#if hasMore}
					<div class="mt-4 text-center">
						<button class="btn btn-secondary" onclick={loadMore}>Load More</button>
					</div>
				{/if}
			{/if}
		</Card>
	{/if}
</div>
