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
		<StatCard label="Servers" value={servers.length} />
	</div>

	<!-- Two Column Layout -->
	<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
		<!-- Servers -->
		<Card title="MCP Servers">
			{#if loading}
				<div class="space-y-3">
					{#each Array(3) as _}
						<div class="skeleton h-16"></div>
					{/each}
				</div>
			{:else if servers.length > 0}
				<div class="space-y-3">
					{#each servers as server (server.name)}
						<div class="p-4 bg-apple-bg-tertiary rounded-apple-md flex items-center justify-between transition-all duration-150 hover:bg-apple-bg-elevated">
							<div>
								<p class="font-medium text-apple-text-primary">{server.name}</p>
								<div class="flex items-center gap-3 mt-1.5 text-sm">
									<span class="flex items-center gap-1.5 {server.connected ? 'text-apple-green' : 'text-apple-red'}">
										<span class="status-dot {server.connected ? 'status-dot-success' : 'status-dot-danger'}"></span>
										{server.connected ? 'Connected' : 'Disconnected'}
									</span>
									<span class="text-apple-text-quaternary">{server.tools_count} tools</span>
									<span class="badge badge-neutral">{server.transport}</span>
								</div>
							</div>
							<button
								class="btn btn-secondary text-sm"
								onclick={() => reconnectServer(server.name)}
								disabled={reconnecting === server.name}
							>
								<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
								</svg>
								{reconnecting === server.name ? 'Reconnecting...' : 'Reconnect'}
							</button>
						</div>
					{/each}
				</div>
			{:else}
				<div class="flex flex-col items-center justify-center py-12 text-center">
					<div class="w-12 h-12 rounded-full bg-apple-bg-tertiary flex items-center justify-center mb-4">
						<svg class="w-6 h-6 text-apple-text-tertiary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01"/>
						</svg>
					</div>
					<p class="text-apple-text-secondary font-medium">
						{status?.enabled ? 'No MCP servers configured' : 'MCP is disabled'}
					</p>
				</div>
			{/if}
		</Card>

		<!-- Tool Execution -->
		<Card title="Tool Execution">
			{#if selectedTool}
				<div class="space-y-4">
					<div class="p-4 bg-apple-bg-tertiary rounded-apple-md">
						<div class="flex items-center justify-between">
							<p class="font-medium text-apple-text-primary">{selectedTool.name}</p>
							<button class="text-apple-text-tertiary hover:text-apple-text-primary transition-colors" onclick={() => (selectedTool = null)}>
								<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M6 18L18 6M6 6l12 12"/>
								</svg>
							</button>
						</div>
						<p class="text-sm text-apple-text-secondary mt-1">{selectedTool.description}</p>
						<p class="text-xs text-apple-text-quaternary mt-2 font-mono">Server: {selectedTool.server}</p>
					</div>

					<div>
						<label class="block text-xs text-apple-text-tertiary uppercase tracking-wider font-medium mb-2">Arguments (JSON)</label>
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
						<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/>
						</svg>
						{executing === selectedTool.name ? 'Executing...' : 'Execute Tool'}
					</button>

					{#if executionResult}
						<div
							class="p-4 rounded-apple-md {executionResult.success
								? 'bg-apple-green/10 border border-apple-green/30'
								: 'bg-apple-red/10 border border-apple-red/30'}"
						>
							<p class="text-sm font-medium {executionResult.success ? 'text-apple-green' : 'text-apple-red'}">
								{executionResult.success ? 'Success' : 'Failed'}
							</p>
							{#if executionResult.error}
								<p class="text-sm text-apple-red/80 mt-1">{executionResult.error}</p>
							{/if}
							{#if executionResult.content}
								<pre class="text-xs text-apple-text-secondary mt-2 overflow-auto max-h-48 font-mono bg-apple-bg-secondary p-3 rounded-apple-sm">{JSON.stringify(
									executionResult.content,
									null,
									2
								)}</pre>
							{/if}
						</div>
					{/if}
				</div>
			{:else}
				<div class="flex flex-col items-center justify-center py-12 text-center">
					<div class="w-12 h-12 rounded-full bg-apple-bg-tertiary flex items-center justify-center mb-4">
						<svg class="w-6 h-6 text-apple-text-tertiary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122"/>
						</svg>
					</div>
					<p class="text-apple-text-secondary font-medium">Select a tool to execute</p>
					<p class="text-sm text-apple-text-tertiary mt-1">Choose a tool from the list below</p>
				</div>
			{/if}
		</Card>
	</div>

	<!-- Tools List -->
	<Card title="Available Tools">
		{#if loading}
			<div class="space-y-2">
				{#each Array(5) as _}
					<div class="skeleton h-12"></div>
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
						<tr class="text-left border-b border-apple-border-subtle">
							<th class="table-header">Tool</th>
							<th class="table-header">Description</th>
							<th class="table-header">Server</th>
							<th class="table-header"></th>
						</tr>
					</thead>
					<tbody>
						{#each filteredTools as tool (tool.name)}
							<tr
								class="table-row cursor-pointer"
								onclick={() => selectTool(tool)}
							>
								<td class="table-cell">
									<span class="font-medium text-apple-text-primary">{tool.name}</span>
								</td>
								<td class="table-cell text-sm text-apple-text-secondary max-w-md truncate">{tool.description}</td>
								<td class="table-cell">
									<span class="badge badge-info">{tool.server}</span>
								</td>
								<td class="table-cell">
									<button
										class="btn btn-ghost text-sm"
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
			<div class="flex flex-col items-center justify-center py-12 text-center">
				<div class="w-12 h-12 rounded-full bg-apple-bg-tertiary flex items-center justify-center mb-4">
					<svg class="w-6 h-6 text-apple-text-tertiary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
					</svg>
				</div>
				<p class="text-apple-text-secondary font-medium">No tools available</p>
				<p class="text-sm text-apple-text-tertiary mt-1">Connect MCP servers to see available tools</p>
			</div>
		{/if}
	</Card>
</div>
