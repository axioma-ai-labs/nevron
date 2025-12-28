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

	function getProcessStateColor(state: string): string {
		switch (state) {
			case 'running':
				return 'text-green-400';
			case 'stopped':
				return 'text-red-400';
			case 'error':
				return 'text-red-400';
			default:
				return 'text-slate-400';
		}
	}
</script>

<div class="space-y-6">
	<!-- Controls -->
	<Card>
		<div class="flex items-center justify-between">
			<div class="flex items-center gap-4">
				<h3 class="text-lg font-semibold text-white">Runtime Control</h3>
				{#if stats}
					<span class="badge {getStateColor(stats.runtime.state)}">{stats.runtime.state}</span>
				{/if}
			</div>
			<div class="flex gap-2">
				<button
					class="btn btn-success"
					onclick={startRuntime}
					disabled={actionLoading || stats?.runtime.state === 'running'}
				>
					Start
				</button>
				<button class="btn btn-secondary" onclick={pauseRuntime} disabled={actionLoading}>
					Pause
				</button>
				<button class="btn btn-secondary" onclick={resumeRuntime} disabled={actionLoading}>
					Resume
				</button>
				<button
					class="btn btn-danger"
					onclick={stopRuntime}
					disabled={actionLoading || stats?.runtime.state === 'stopped'}
				>
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
				<div class="animate-pulse space-y-3">
					{#each Array(5) as _}
						<div class="h-4 bg-surface-700 rounded"></div>
					{/each}
				</div>
			{:else if stats}
				<div class="space-y-4">
					<div class="flex justify-between items-center">
						<span class="text-slate-400">Status</span>
						<span class="badge {stats.queue.paused ? 'badge-warning' : 'badge-success'}">
							{stats.queue.paused ? 'Paused' : 'Active'}
						</span>
					</div>
					<div class="flex justify-between items-center">
						<span class="text-slate-400">Total Enqueued</span>
						<span class="text-white font-medium">{stats.queue.total_enqueued}</span>
					</div>
					<div class="flex justify-between items-center">
						<span class="text-slate-400">Total Dequeued</span>
						<span class="text-white font-medium">{stats.queue.total_dequeued}</span>
					</div>
					<div class="flex justify-between items-center">
						<span class="text-slate-400">Total Expired</span>
						<span class="text-white font-medium">{stats.queue.total_expired}</span>
					</div>

					{#if Object.keys(stats.queue.by_priority).length > 0}
						<div class="pt-4 border-t border-surface-700">
							<p class="text-sm text-slate-400 mb-2">By Priority</p>
							<div class="space-y-2">
								{#each Object.entries(stats.queue.by_priority) as [priority, count]}
									<div class="flex justify-between items-center">
										<span class="text-slate-300">{priority}</span>
										<span class="text-white font-medium">{count}</span>
									</div>
								{/each}
							</div>
						</div>
					{/if}

					{#if Object.keys(stats.queue.by_type).length > 0}
						<div class="pt-4 border-t border-surface-700">
							<p class="text-sm text-slate-400 mb-2">By Type</p>
							<div class="space-y-2">
								{#each Object.entries(stats.queue.by_type) as [type, count]}
									<div class="flex justify-between items-center">
										<span class="text-slate-300">{type}</span>
										<span class="text-white font-medium">{count}</span>
									</div>
								{/each}
							</div>
						</div>
					{/if}
				</div>
			{:else}
				<p class="text-slate-500">No data available</p>
			{/if}
		</Card>

		<!-- Scheduler -->
		<Card title="Scheduler">
			{#if loading}
				<div class="animate-pulse space-y-3">
					{#each Array(4) as _}
						<div class="h-4 bg-surface-700 rounded"></div>
					{/each}
				</div>
			{:else if stats}
				<div class="space-y-4">
					<div class="flex justify-between items-center">
						<span class="text-slate-400">Tasks Scheduled</span>
						<span class="text-white font-medium">{stats.scheduler.tasks_scheduled}</span>
					</div>
					<div class="flex justify-between items-center">
						<span class="text-slate-400">Tasks Executed</span>
						<span class="text-white font-medium">{stats.scheduler.tasks_executed}</span>
					</div>
					{#if stats.scheduler.next_task}
						<div class="pt-4 border-t border-surface-700">
							<p class="text-sm text-slate-400">Next Task</p>
							<p class="text-white font-medium">{stats.scheduler.next_task}</p>
							{#if stats.scheduler.next_run_at}
								<p class="text-xs text-slate-500 mt-1">
									{formatTime(stats.scheduler.next_run_at)}
								</p>
							{/if}
						</div>
					{:else}
						<div class="pt-4 border-t border-surface-700">
							<p class="text-sm text-slate-500">No scheduled tasks</p>
						</div>
					{/if}
				</div>
			{:else}
				<p class="text-slate-500">No data available</p>
			{/if}
		</Card>
	</div>

	<!-- Background Processes -->
	<Card title="Background Processes">
		{#if loading}
			<div class="animate-pulse space-y-2">
				{#each Array(3) as _}
					<div class="h-16 bg-surface-700 rounded"></div>
				{/each}
			</div>
		{:else if stats?.background.processes && stats.background.processes.length > 0}
			<div class="overflow-x-auto">
				<table class="w-full">
					<thead>
						<tr class="text-left border-b border-surface-700">
							<th class="pb-3 text-sm text-slate-400 font-medium">Process</th>
							<th class="pb-3 text-sm text-slate-400 font-medium">State</th>
							<th class="pb-3 text-sm text-slate-400 font-medium">Iterations</th>
							<th class="pb-3 text-sm text-slate-400 font-medium">Errors</th>
							<th class="pb-3 text-sm text-slate-400 font-medium">Last Run</th>
						</tr>
					</thead>
					<tbody>
						{#each stats.background.processes as process (process.name)}
							<tr class="border-b border-surface-800">
								<td class="py-3">
									<span class="font-medium text-white">{process.name}</span>
								</td>
								<td class="py-3">
									<span class={getProcessStateColor(process.state)}>{process.state}</span>
								</td>
								<td class="py-3 text-slate-300">{process.iterations}</td>
								<td class="py-3">
									<span class={process.errors > 0 ? 'text-red-400' : 'text-slate-400'}>
										{process.errors}
									</span>
								</td>
								<td class="py-3 text-sm text-slate-400">
									{formatTime(process.last_run_at)}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
			<div class="mt-4 pt-4 border-t border-surface-700 flex gap-6">
				<div>
					<span class="text-slate-400">Total Running:</span>
					<span class="text-white font-medium ml-2">{stats.background.total_running}</span>
				</div>
				<div>
					<span class="text-slate-400">Total Errors:</span>
					<span class="text-red-400 font-medium ml-2">{stats.background.total_errors}</span>
				</div>
			</div>
		{:else}
			<p class="text-slate-500 text-center py-8">No background processes</p>
		{/if}
	</Card>
</div>
