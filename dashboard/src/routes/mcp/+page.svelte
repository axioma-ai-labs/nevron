<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import Card from '$lib/components/Card.svelte';
	import StatCard from '$lib/components/StatCard.svelte';
	import {
		mcpAPI,
		type MCPStatus,
		type MCPServerStatus,
		type MCPToolInfo
	} from '$lib/api/client';

	let status: MCPStatus | null = $state(null);
	let servers: MCPServerStatus[] = $state([]);
	let tools: MCPToolInfo[] = $state([]);
	let loading = $state(true);
	let reconnecting = $state<string | null>(null);
	let executing = $state<string | null>(null);
	let selectedTool: MCPToolInfo | null = $state(null);
	let toolArgs = $state('{}');
	let executionResult = $state<{ success: boolean; content: unknown; error: string | null } | null>(
		null
	);
	let serverFilter = $state('');
	let refreshInterval: ReturnType<typeof setInterval>;

	onMount(() => {
		fetchData();
		refreshInterval = setInterval(fetchStatus, 10000);
	});

	onDestroy(() => {
		if (refreshInterval) clearInterval(refreshInterval);
	});

	async function fetchStatus() {
		try {
			const res = await mcpAPI.getStatus();
			if (res.data) status = res.data;
		} catch (e) {
			console.error('Failed to fetch MCP status:', e);
		}
	}

	async function fetchData() {
		loading = true;
		try {
			const [statusRes, serversRes, toolsRes] = await Promise.all([
				mcpAPI.getStatus(),
				mcpAPI.getServers(),
				mcpAPI.getTools()
			]);

			if (statusRes.data) status = statusRes.data;
			if (serversRes.data) servers = serversRes.data;
			if (toolsRes.data) tools = toolsRes.data;
		} catch (e) {
			console.error('Failed to fetch MCP data:', e);
		}
		loading = false;
	}

	async function reconnectServer(serverName: string) {
		reconnecting = serverName;
		try {
			await mcpAPI.reconnectServer(serverName);
			await fetchData();
		} catch (e) {
			console.error('Failed to reconnect server:', e);
		}
		reconnecting = null;
	}

	async function executeTool() {
		if (!selectedTool) return;
		executing = selectedTool.name;
		executionResult = null;

		try {
			const args = JSON.parse(toolArgs);
			const res = await mcpAPI.executeTool(selectedTool.name, args);
			if (res.data) {
				executionResult = {
					success: res.data.success,
					content: res.data.content,
					error: res.data.error
				};
			}
		} catch (e) {
			executionResult = {
				success: false,
				content: null,
				error: e instanceof Error ? e.message : 'Execution failed'
			};
		}
		executing = null;
	}

	function selectTool(tool: MCPToolInfo) {
		selectedTool = tool;
		toolArgs = JSON.stringify(tool.input_schema.properties ? {} : {}, null, 2);
		executionResult = null;
	}

	let filteredTools = $derived(
		serverFilter ? tools.filter((t) => t.server === serverFilter) : tools
	);

	let uniqueServers = $derived([...new Set(tools.map((t) => t.server))]);
</script>

<div class="space-y-6">
	<!-- Stats Grid -->
	<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
		<StatCard
			label="Status"
			value={status?.enabled ? (status.initialized ? 'Active' : 'Initializing') : 'Disabled'}
			icon="tools"
		/>
		<StatCard label="Connected Servers" value={status?.connected_servers.length ?? '-'} />
		<StatCard label="Total Tools" value={status?.total_tools ?? '-'} />
		<StatCard
			label="Servers"
			value={servers.length}
		/>
	</div>

	<!-- Two Column Layout -->
	<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
		<!-- Servers -->
		<Card title="MCP Servers">
			{#if loading}
				<div class="animate-pulse space-y-3">
					{#each Array(3) as _}
						<div class="h-16 bg-surface-700 rounded"></div>
					{/each}
				</div>
			{:else if servers.length > 0}
				<div class="space-y-3">
					{#each servers as server (server.name)}
						<div class="p-4 bg-surface-800 rounded-lg flex items-center justify-between">
							<div>
								<p class="font-medium text-white">{server.name}</p>
								<div class="flex items-center gap-3 mt-1 text-sm">
									<span
										class="flex items-center gap-1 {server.connected
											? 'text-green-400'
											: 'text-red-400'}"
									>
										<span
											class="w-2 h-2 rounded-full {server.connected ? 'bg-green-400' : 'bg-red-400'}"
										></span>
										{server.connected ? 'Connected' : 'Disconnected'}
									</span>
									<span class="text-slate-500">{server.tools_count} tools</span>
									<span class="text-slate-500">{server.transport}</span>
								</div>
							</div>
							<button
								class="btn btn-secondary text-sm"
								onclick={() => reconnectServer(server.name)}
								disabled={reconnecting === server.name}
							>
								{reconnecting === server.name ? 'Reconnecting...' : 'Reconnect'}
							</button>
						</div>
					{/each}
				</div>
			{:else}
				<p class="text-slate-500 text-center py-8">
					{status?.enabled ? 'No MCP servers configured' : 'MCP is disabled'}
				</p>
			{/if}
		</Card>

		<!-- Tool Execution -->
		<Card title="Tool Execution">
			{#if selectedTool}
				<div class="space-y-4">
					<div class="p-3 bg-surface-800 rounded-lg">
						<div class="flex items-center justify-between">
							<p class="font-medium text-white">{selectedTool.name}</p>
							<button class="text-slate-400 hover:text-white" onclick={() => (selectedTool = null)}>
								<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2"
										d="M6 18L18 6M6 6l12 12"
									/>
								</svg>
							</button>
						</div>
						<p class="text-sm text-slate-400 mt-1">{selectedTool.description}</p>
						<p class="text-xs text-slate-500 mt-1">Server: {selectedTool.server}</p>
					</div>

					<div>
						<label class="block text-sm text-slate-400 mb-1">Arguments (JSON)</label>
						<textarea
							class="input w-full h-32 font-mono text-sm"
							bind:value={toolArgs}
							placeholder={"{}"}
						></textarea>
					</div>

					<button
						class="btn btn-primary w-full"
						onclick={executeTool}
						disabled={executing === selectedTool.name}
					>
						{executing === selectedTool.name ? 'Executing...' : 'Execute Tool'}
					</button>

					{#if executionResult}
						<div
							class="p-3 rounded-lg {executionResult.success
								? 'bg-green-900/30 border border-green-700'
								: 'bg-red-900/30 border border-red-700'}"
						>
							<p class="text-sm font-medium {executionResult.success ? 'text-green-400' : 'text-red-400'}">
								{executionResult.success ? 'Success' : 'Failed'}
							</p>
							{#if executionResult.error}
								<p class="text-sm text-red-300 mt-1">{executionResult.error}</p>
							{/if}
							{#if executionResult.content}
								<pre class="text-xs text-slate-300 mt-2 overflow-auto max-h-48">{JSON.stringify(
										executionResult.content,
										null,
										2
									)}</pre>
							{/if}
						</div>
					{/if}
				</div>
			{:else}
				<p class="text-slate-500 text-center py-8">Select a tool from the list below to execute it</p>
			{/if}
		</Card>
	</div>

	<!-- Tools List -->
	<Card title="Available Tools">
		{#if loading}
			<div class="animate-pulse space-y-2">
				{#each Array(5) as _}
					<div class="h-12 bg-surface-700 rounded"></div>
				{/each}
			</div>
		{:else if tools.length > 0}
			<!-- Filter -->
			<div class="mb-4">
				<select class="input" bind:value={serverFilter}>
					<option value="">All servers</option>
					{#each uniqueServers as server}
						<option value={server}>{server}</option>
					{/each}
				</select>
			</div>

			<div class="overflow-x-auto">
				<table class="w-full">
					<thead>
						<tr class="text-left border-b border-surface-700">
							<th class="pb-3 text-sm text-slate-400 font-medium">Tool</th>
							<th class="pb-3 text-sm text-slate-400 font-medium">Description</th>
							<th class="pb-3 text-sm text-slate-400 font-medium">Server</th>
							<th class="pb-3 text-sm text-slate-400 font-medium"></th>
						</tr>
					</thead>
					<tbody>
						{#each filteredTools as tool (tool.name)}
							<tr
								class="border-b border-surface-800 hover:bg-surface-800 cursor-pointer"
								onclick={() => selectTool(tool)}
							>
								<td class="py-3">
									<span class="font-medium text-white">{tool.name}</span>
								</td>
								<td class="py-3 text-sm text-slate-400 max-w-md truncate">{tool.description}</td>
								<td class="py-3">
									<span class="badge badge-info">{tool.server}</span>
								</td>
								<td class="py-3">
									<button
										class="btn btn-secondary text-sm"
										onclick={(e) => { e.stopPropagation(); selectTool(tool); }}
									>
										Select
									</button>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{:else}
			<p class="text-slate-500 text-center py-8">No tools available</p>
		{/if}
	</Card>
</div>
