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
		if (!outcome) return 'text-slate-400';
		if (outcome.toLowerCase().includes('success')) return 'text-green-400';
		if (outcome.toLowerCase().includes('error') || outcome.toLowerCase().includes('fail'))
			return 'text-red-400';
		return 'text-slate-300';
	}
</script>

<div class="space-y-6">
	<!-- Agent Status and Controls -->
	<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
		<!-- Status Card -->
		<Card title="Agent Status" class="lg:col-span-2">
			{#if loading}
				<div class="animate-pulse space-y-4">
					<div class="h-6 bg-surface-700 rounded w-1/3"></div>
					<div class="h-4 bg-surface-700 rounded w-full"></div>
					<div class="h-4 bg-surface-700 rounded w-2/3"></div>
				</div>
			{:else if status && info}
				<div class="space-y-4">
					<div class="flex items-center gap-4">
						<span
							class="badge {status.is_running ? 'badge-success' : 'badge-danger'} text-sm px-3 py-1"
						>
							{status.is_running ? 'Running' : 'Stopped'}
						</span>
						<span class="badge badge-info text-sm px-3 py-1">{status.state}</span>
					</div>

					<div class="grid grid-cols-2 gap-4">
						<div>
							<p class="text-sm text-slate-400">Personality</p>
							<p class="text-white">{info.personality}</p>
						</div>
						<div>
							<p class="text-sm text-slate-400">Goal</p>
							<p class="text-white">{info.goal}</p>
						</div>
					</div>

					<div class="grid grid-cols-3 gap-4">
						<div class="p-3 bg-surface-800 rounded-lg text-center">
							<p class="stat-value">{info.total_actions_executed}</p>
							<p class="stat-label">Actions Executed</p>
						</div>
						<div class="p-3 bg-surface-800 rounded-lg text-center">
							<p class="stat-value">{info.total_rewards.toFixed(2)}</p>
							<p class="stat-label">Total Rewards</p>
						</div>
						<div class="p-3 bg-surface-800 rounded-lg text-center">
							<p class="stat-value">{status.mcp_available_tools}</p>
							<p class="stat-label">MCP Tools</p>
						</div>
					</div>

					{#if info.last_action}
						<div class="p-3 bg-surface-800 rounded-lg">
							<p class="text-sm text-slate-400">Last Action</p>
							<p class="text-white font-medium">{info.last_action}</p>
							{#if info.last_action_time}
								<p class="text-xs text-slate-500 mt-1">{formatTime(info.last_action_time)}</p>
							{/if}
						</div>
					{/if}
				</div>
			{:else}
				<p class="text-slate-500">Unable to load agent status</p>
			{/if}
		</Card>

		<!-- Controls Card -->
		<Card title="Controls">
			<div class="space-y-4">
				<!-- Start/Stop Buttons -->
				<div class="flex gap-2">
					<button
						class="btn btn-success flex-1"
						onclick={startAgent}
						disabled={actionLoading || status?.is_running}
					>
						{actionLoading ? 'Loading...' : 'Start'}
					</button>
					<button
						class="btn btn-danger flex-1"
						onclick={stopAgent}
						disabled={actionLoading || !status?.is_running}
					>
						{actionLoading ? 'Loading...' : 'Stop'}
					</button>
				</div>

				<!-- Manual Action Execution -->
				<div class="pt-4 border-t border-surface-700">
					<p class="text-sm text-slate-400 mb-2">Execute Action</p>
					<select class="input w-full mb-2" bind:value={selectedAction}>
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
			<div class="animate-pulse space-y-2">
				{#each Array(5) as _}
					<div class="h-12 bg-surface-700 rounded"></div>
				{/each}
			</div>
		{:else if context?.actions_history && context.actions_history.length > 0}
			<div class="overflow-x-auto">
				<table class="w-full">
					<thead>
						<tr class="text-left border-b border-surface-700">
							<th class="pb-3 text-sm text-slate-400 font-medium">Time</th>
							<th class="pb-3 text-sm text-slate-400 font-medium">Action</th>
							<th class="pb-3 text-sm text-slate-400 font-medium">State</th>
							<th class="pb-3 text-sm text-slate-400 font-medium">Outcome</th>
							<th class="pb-3 text-sm text-slate-400 font-medium">Reward</th>
						</tr>
					</thead>
					<tbody>
						{#each context.actions_history.slice().reverse() as item (item.timestamp)}
							<tr class="border-b border-surface-800">
								<td class="py-3 text-sm text-slate-400">{formatTime(item.timestamp)}</td>
								<td class="py-3">
									<span class="font-medium text-white">{item.action}</span>
								</td>
								<td class="py-3">
									<span class="badge badge-info">{item.state}</span>
								</td>
								<td class="py-3">
									<span class={getOutcomeColor(item.outcome)}>
										{item.outcome || '-'}
									</span>
								</td>
								<td class="py-3">
									{#if item.reward !== null}
										<span class={item.reward > 0 ? 'text-green-400' : 'text-red-400'}>
											{item.reward > 0 ? '+' : ''}{item.reward.toFixed(2)}
										</span>
									{:else}
										<span class="text-slate-500">-</span>
									{/if}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{:else}
			<p class="text-slate-500 text-center py-8">No action history available</p>
		{/if}
	</Card>
</div>
