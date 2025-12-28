<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import Card from '$lib/components/Card.svelte';
	import {
		agentAPI,
		type AgentStatus,
		type AgentInfo,
		type AgentContext,
		type ActionHistoryItem
	} from '$lib/api/client';

	let status: AgentStatus | null = $state(null);
	let info: AgentInfo | null = $state(null);
	let context: AgentContext | null = $state(null);
	let loading = $state(true);
	let actionLoading = $state(false);
	let selectedAction = $state('');
	let refreshInterval: ReturnType<typeof setInterval>;

	onMount(() => {
		fetchData();
		refreshInterval = setInterval(fetchData, 5000);
	});

	onDestroy(() => {
		if (refreshInterval) clearInterval(refreshInterval);
	});

	async function fetchData() {
		try {
			const [statusRes, infoRes, contextRes] = await Promise.all([
				agentAPI.getStatus(),
				agentAPI.getInfo(),
				agentAPI.getContext(50)
			]);

			if (statusRes.data) status = statusRes.data;
			if (infoRes.data) info = infoRes.data;
			if (contextRes.data) context = contextRes.data;
			loading = false;
		} catch (e) {
			console.error('Failed to fetch agent data:', e);
			loading = false;
		}
	}

	async function startAgent() {
		actionLoading = true;
		try {
			await agentAPI.start();
			await fetchData();
		} catch (e) {
			console.error('Failed to start agent:', e);
		}
		actionLoading = false;
	}

	async function stopAgent() {
		actionLoading = true;
		try {
			await agentAPI.stop();
			await fetchData();
		} catch (e) {
			console.error('Failed to stop agent:', e);
		}
		actionLoading = false;
	}

	async function executeAction() {
		if (!selectedAction) return;
		actionLoading = true;
		try {
			await agentAPI.executeAction(selectedAction);
			selectedAction = '';
			await fetchData();
		} catch (e) {
			console.error('Failed to execute action:', e);
		}
		actionLoading = false;
	}

	function formatTime(timestamp: string): string {
		return new Date(timestamp).toLocaleString();
	}

	function getOutcomeColor(outcome: string | null): string {
		if (!outcome) return 'text-apple-text-tertiary';
		if (outcome.toLowerCase().includes('success')) return 'text-apple-green';
		if (outcome.toLowerCase().includes('error') || outcome.toLowerCase().includes('fail'))
			return 'text-apple-red';
		return 'text-apple-text-secondary';
	}
</script>

<div class="space-y-6">
	<!-- Agent Status and Controls -->
	<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
		<!-- Status Card -->
		<Card title="Agent Status" class="lg:col-span-2">
			{#if loading}
				<div class="space-y-4">
					{#each Array(4) as _}
						<div class="skeleton h-6 w-full"></div>
					{/each}
				</div>
			{:else if status && info}
				<div class="space-y-5">
					<!-- Status Badges -->
					<div class="flex items-center gap-3">
						<span class="badge {status.is_running ? 'badge-success' : 'badge-danger'} text-sm px-3 py-1.5">
							{status.is_running ? 'Running' : 'Stopped'}
						</span>
						<span class="badge badge-info text-sm px-3 py-1.5">{status.state}</span>
					</div>

					<!-- Info Grid -->
					<div class="grid grid-cols-2 gap-5">
						<div>
							<p class="text-xs text-apple-text-tertiary uppercase tracking-wider font-medium">Personality</p>
							<p class="text-apple-text-primary mt-1">{info.personality}</p>
						</div>
						<div>
							<p class="text-xs text-apple-text-tertiary uppercase tracking-wider font-medium">Goal</p>
							<p class="text-apple-text-primary mt-1">{info.goal}</p>
						</div>
					</div>

					<!-- Stats Cards -->
					<div class="grid grid-cols-3 gap-4">
						<div class="p-4 bg-apple-bg-tertiary rounded-apple-md text-center">
							<p class="stat-value">{info.total_actions_executed}</p>
							<p class="stat-label mt-1">Actions Executed</p>
						</div>
						<div class="p-4 bg-apple-bg-tertiary rounded-apple-md text-center">
							<p class="stat-value">{info.total_rewards.toFixed(2)}</p>
							<p class="stat-label mt-1">Total Rewards</p>
						</div>
						<div class="p-4 bg-apple-bg-tertiary rounded-apple-md text-center">
							<p class="stat-value">{status.mcp_available_tools}</p>
							<p class="stat-label mt-1">MCP Tools</p>
						</div>
					</div>

					<!-- Last Action -->
					{#if info.last_action}
						<div class="p-4 bg-apple-bg-tertiary rounded-apple-md">
							<p class="text-xs text-apple-text-tertiary uppercase tracking-wider font-medium">Last Action</p>
							<p class="text-apple-text-primary font-medium mt-1">{info.last_action}</p>
							{#if info.last_action_time}
								<p class="text-xs text-apple-text-quaternary mt-2 font-mono">{formatTime(info.last_action_time)}</p>
							{/if}
						</div>
					{/if}
				</div>
			{:else}
				<p class="text-apple-text-tertiary text-center py-8">Unable to load agent status</p>
			{/if}
		</Card>

		<!-- Controls Card -->
		<Card title="Controls">
			<div class="space-y-5">
				<!-- Start/Stop Buttons -->
				<div class="flex gap-3">
					<button
						class="btn btn-success flex-1"
						onclick={startAgent}
						disabled={actionLoading || status?.is_running}
					>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/>
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
						</svg>
						{actionLoading ? 'Loading...' : 'Start'}
					</button>
					<button
						class="btn btn-danger flex-1"
						onclick={stopAgent}
						disabled={actionLoading || !status?.is_running}
					>
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z"/>
						</svg>
						{actionLoading ? 'Loading...' : 'Stop'}
					</button>
				</div>

				<!-- Manual Action Execution -->
				<div class="pt-5 border-t border-apple-border-subtle">
					<p class="text-xs text-apple-text-tertiary uppercase tracking-wider font-medium mb-3">Execute Action</p>
					<select class="input mb-3" bind:value={selectedAction}>
						<option value="">Select an action...</option>
						{#if info?.available_actions}
							{#each info.available_actions as action}
								<option value={action}>{action}</option>
							{/each}
						{/if}
					</select>
					<button
						class="btn btn-primary w-full"
						onclick={executeAction}
						disabled={!selectedAction || actionLoading}
					>
						Execute
					</button>
				</div>
			</div>
		</Card>
	</div>

	<!-- Action History -->
	<Card title="Action History">
		{#if loading}
			<div class="space-y-3">
				{#each Array(5) as _}
					<div class="skeleton h-14"></div>
				{/each}
			</div>
		{:else if context?.actions_history && context.actions_history.length > 0}
			<div class="overflow-x-auto">
				<table class="w-full">
					<thead>
						<tr class="text-left border-b border-apple-border-subtle">
							<th class="table-header">Time</th>
							<th class="table-header">Action</th>
							<th class="table-header">State</th>
							<th class="table-header">Outcome</th>
							<th class="table-header">Reward</th>
						</tr>
					</thead>
					<tbody>
						{#each context.actions_history.slice().reverse() as item (item.timestamp)}
							<tr class="table-row">
								<td class="table-cell text-apple-text-tertiary font-mono text-xs">{formatTime(item.timestamp)}</td>
								<td class="table-cell">
									<span class="font-medium text-apple-text-primary">{item.action}</span>
								</td>
								<td class="table-cell">
									<span class="badge badge-info">{item.state}</span>
								</td>
								<td class="table-cell">
									<span class={getOutcomeColor(item.outcome)}>
										{item.outcome || '-'}
									</span>
								</td>
								<td class="table-cell font-mono">
									{#if item.reward !== null}
										<span class={item.reward > 0 ? 'text-apple-green' : 'text-apple-red'}>
											{item.reward > 0 ? '+' : ''}{item.reward.toFixed(2)}
										</span>
									{:else}
										<span class="text-apple-text-quaternary">-</span>
									{/if}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{:else}
			<div class="flex flex-col items-center justify-center py-12 text-center">
				<div class="w-12 h-12 rounded-full bg-apple-bg-tertiary flex items-center justify-center mb-4">
					<svg class="w-6 h-6 text-apple-text-tertiary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
					</svg>
				</div>
				<p class="text-apple-text-secondary font-medium">No action history available</p>
				<p class="text-sm text-apple-text-tertiary mt-1">Actions will appear here as the agent executes them</p>
			</div>
		{/if}
	</Card>
</div>
