<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import Card from '$lib/components/Card.svelte';
	import StatCard from '$lib/components/StatCard.svelte';
	import {
		runtimeAPI,
		type FullRuntimeStatistics,
		type QueueStatistics,
		type BackgroundProcess
	} from '$lib/api/client';

	let stats: FullRuntimeStatistics | null = $state(null);
	let loading = $state(true);
	let actionLoading = $state(false);
	let refreshInterval: ReturnType<typeof setInterval>;

	onMount(() => {
		fetchData();
		refreshInterval = setInterval(fetchData, 3000);
	});

	onDestroy(() => {
		if (refreshInterval) clearInterval(refreshInterval);
	});

	async function fetchData() {
		try {
			const res = await runtimeAPI.getStatistics();
			if (res.data) stats = res.data;
			loading = false;
		} catch (e) {
			console.error('Failed to fetch runtime data:', e);
			loading = false;
		}
	}

	async function startRuntime() {
		actionLoading = true;
		try {
			await runtimeAPI.start();
			await fetchData();
		} catch (e) {
			console.error('Failed to start runtime:', e);
		}
		actionLoading = false;
	}

	async function stopRuntime() {
		actionLoading = true;
		try {
			await runtimeAPI.stop();
			await fetchData();
		} catch (e) {
			console.error('Failed to stop runtime:', e);
		}
		actionLoading = false;
	}

	async function pauseRuntime() {
		actionLoading = true;
		try {
			await runtimeAPI.pause();
			await fetchData();
		} catch (e) {
			console.error('Failed to pause runtime:', e);
		}
		actionLoading = false;
	}

	async function resumeRuntime() {
		actionLoading = true;
		try {
			await runtimeAPI.resume();
			await fetchData();
		} catch (e) {
			console.error('Failed to resume runtime:', e);
		}
		actionLoading = false;
	}

	function formatUptime(seconds: number): string {
		const hours = Math.floor(seconds / 3600);
		const minutes = Math.floor((seconds % 3600) / 60);
		const secs = Math.floor(seconds % 60);
		if (hours > 0) return `${hours}h ${minutes}m ${secs}s`;
		if (minutes > 0) return `${minutes}m ${secs}s`;
		return `${secs}s`;
	}

	function formatTime(timestamp: string | null): string {
		if (!timestamp) return '-';
		return new Date(timestamp).toLocaleString();
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

	function getProcessStateColor(state: string): string {
		switch (state) {
			case 'running':
				return 'text-apple-green';
			case 'stopped':
			case 'error':
				return 'text-apple-red';
			default:
				return 'text-apple-text-tertiary';
		}
	}
</script>

<div class="space-y-6">
	<!-- Controls -->
	<Card>
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-4">
				<h3 class="text-lg font-semibold text-apple-text-primary tracking-tight">Runtime Control</h3>
				{#if stats}
					<span class="badge {getStateBadgeClass(stats.runtime.state)}">{stats.runtime.state}</span>
				{/if}
			</div>
			<div class="flex gap-2">
				<button
					class="btn btn-success"
					onclick={startRuntime}
					disabled={actionLoading || stats?.runtime.state === 'running'}
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/>
					</svg>
					Start
				</button>
				<button class="btn btn-secondary" onclick={pauseRuntime} disabled={actionLoading}>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
					</svg>
					Pause
				</button>
				<button class="btn btn-secondary" onclick={resumeRuntime} disabled={actionLoading}>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/>
					</svg>
					Resume
				</button>
				<button
					class="btn btn-danger"
					onclick={stopRuntime}
					disabled={actionLoading || stats?.runtime.state === 'stopped'}
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z"/>
					</svg>
					Stop
				</button>
			</div>
		</div>
	</Card>

	<!-- Stats Grid -->
	<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
		<StatCard
			label="Uptime"
			value={stats ? formatUptime(stats.runtime.uptime_seconds) : '-'}
			icon="actions"
		/>
		<StatCard label="Events Processed" value={stats?.runtime.events_processed ?? '-'} />
		<StatCard label="Events Failed" value={stats?.runtime.events_failed ?? '-'} />
		<StatCard label="Queue Size" value={stats?.queue.size ?? '-'} />
	</div>

	<!-- Two Column Layout -->
	<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
		<!-- Queue Statistics -->
		<Card title="Event Queue">
			{#if loading}
				<div class="space-y-4">
					{#each Array(5) as _}
						<div class="skeleton h-5 w-full"></div>
					{/each}
				</div>
			{:else if stats}
				<div class="space-y-4">
					<div class="flex justify-between items-center py-2 border-b border-apple-border-subtle">
						<span class="text-apple-text-secondary">Status</span>
						<span class="badge {stats.queue.paused ? 'badge-warning' : 'badge-success'}">
							{stats.queue.paused ? 'Paused' : 'Active'}
						</span>
					</div>
					<div class="flex justify-between items-center py-2 border-b border-apple-border-subtle">
						<span class="text-apple-text-secondary">Total Enqueued</span>
						<span class="text-apple-text-primary font-mono font-medium">{stats.queue.total_enqueued}</span>
					</div>
					<div class="flex justify-between items-center py-2 border-b border-apple-border-subtle">
						<span class="text-apple-text-secondary">Total Dequeued</span>
						<span class="text-apple-text-primary font-mono font-medium">{stats.queue.total_dequeued}</span>
					</div>
					<div class="flex justify-between items-center py-2 border-b border-apple-border-subtle">
						<span class="text-apple-text-secondary">Total Expired</span>
						<span class="text-apple-text-primary font-mono font-medium">{stats.queue.total_expired}</span>
					</div>

					{#if Object.keys(stats.queue.by_priority).length > 0}
						<div class="pt-4">
							<p class="text-xs text-apple-text-tertiary uppercase tracking-wider font-medium mb-3">By Priority</p>
							<div class="space-y-2">
								{#each Object.entries(stats.queue.by_priority) as [priority, count]}
									<div class="flex justify-between items-center">
										<span class="text-apple-text-secondary">{priority}</span>
										<span class="text-apple-text-primary font-mono font-medium">{count}</span>
									</div>
								{/each}
							</div>
						</div>
					{/if}

					{#if Object.keys(stats.queue.by_type).length > 0}
						<div class="pt-4 border-t border-apple-border-subtle">
							<p class="text-xs text-apple-text-tertiary uppercase tracking-wider font-medium mb-3">By Type</p>
							<div class="space-y-2">
								{#each Object.entries(stats.queue.by_type) as [type, count]}
									<div class="flex justify-between items-center">
										<span class="text-apple-text-secondary">{type}</span>
										<span class="text-apple-text-primary font-mono font-medium">{count}</span>
									</div>
								{/each}
							</div>
						</div>
					{/if}
				</div>
			{:else}
				<p class="text-apple-text-tertiary text-center py-8">No data available</p>
			{/if}
		</Card>

		<!-- Scheduler -->
		<Card title="Scheduler">
			{#if loading}
				<div class="space-y-4">
					{#each Array(4) as _}
						<div class="skeleton h-5 w-full"></div>
					{/each}
				</div>
			{:else if stats}
				<div class="space-y-4">
					<div class="flex justify-between items-center py-2 border-b border-apple-border-subtle">
						<span class="text-apple-text-secondary">Tasks Scheduled</span>
						<span class="text-apple-text-primary font-mono font-medium">{stats.scheduler.tasks_scheduled}</span>
					</div>
					<div class="flex justify-between items-center py-2 border-b border-apple-border-subtle">
						<span class="text-apple-text-secondary">Tasks Executed</span>
						<span class="text-apple-text-primary font-mono font-medium">{stats.scheduler.tasks_executed}</span>
					</div>
					{#if stats.scheduler.next_task}
						<div class="pt-4">
							<p class="text-xs text-apple-text-tertiary uppercase tracking-wider font-medium">Next Task</p>
							<p class="text-apple-text-primary font-medium mt-2">{stats.scheduler.next_task}</p>
							{#if stats.scheduler.next_run_at}
								<p class="text-xs text-apple-text-quaternary mt-2 font-mono">
									{formatTime(stats.scheduler.next_run_at)}
								</p>
							{/if}
						</div>
					{:else}
						<div class="pt-4">
							<p class="text-apple-text-tertiary">No scheduled tasks</p>
						</div>
					{/if}
				</div>
			{:else}
				<p class="text-apple-text-tertiary text-center py-8">No data available</p>
			{/if}
		</Card>
	</div>

	<!-- Background Processes -->
	<Card title="Background Processes">
		{#if loading}
			<div class="space-y-3">
				{#each Array(3) as _}
					<div class="skeleton h-16"></div>
				{/each}
			</div>
		{:else if stats?.background.processes && stats.background.processes.length > 0}
			<div class="overflow-x-auto">
				<table class="w-full">
					<thead>
						<tr class="text-left border-b border-apple-border-subtle">
							<th class="table-header">Process</th>
							<th class="table-header">State</th>
							<th class="table-header">Iterations</th>
							<th class="table-header">Errors</th>
							<th class="table-header">Last Run</th>
						</tr>
					</thead>
					<tbody>
						{#each stats.background.processes as process (process.name)}
							<tr class="table-row">
								<td class="table-cell">
									<span class="font-medium text-apple-text-primary">{process.name}</span>
								</td>
								<td class="table-cell">
									<span class="flex items-center gap-2">
										<span class="status-dot {process.state === 'running' ? 'status-dot-success' : 'status-dot-danger'}"></span>
										<span class={getProcessStateColor(process.state)}>{process.state}</span>
									</span>
								</td>
								<td class="table-cell text-apple-text-secondary font-mono">{process.iterations}</td>
								<td class="table-cell">
									<span class="font-mono {process.errors > 0 ? 'text-apple-red' : 'text-apple-text-tertiary'}">
										{process.errors}
									</span>
								</td>
								<td class="table-cell text-apple-text-tertiary font-mono text-xs">
									{formatTime(process.last_run_at)}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
			<div class="mt-5 pt-5 border-t border-apple-border-subtle flex gap-8">
				<div>
					<span class="text-apple-text-tertiary">Total Running:</span>
					<span class="text-apple-text-primary font-mono font-medium ml-2">{stats.background.total_running}</span>
				</div>
				<div>
					<span class="text-apple-text-tertiary">Total Errors:</span>
					<span class="text-apple-red font-mono font-medium ml-2">{stats.background.total_errors}</span>
				</div>
			</div>
		{:else}
			<div class="flex flex-col items-center justify-center py-12 text-center">
				<div class="w-12 h-12 rounded-full bg-apple-bg-tertiary flex items-center justify-center mb-4">
					<svg class="w-6 h-6 text-apple-text-tertiary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
					</svg>
				</div>
				<p class="text-apple-text-secondary font-medium">No background processes</p>
			</div>
		{/if}
	</Card>
</div>
