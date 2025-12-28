<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { websocketStore, connectionStatus } from '$lib/stores/websocket';
	import { healthAPI, type HealthCheck } from '$lib/api/client';

	let health: HealthCheck | null = null;
	let healthError = false;
	let refreshInterval: ReturnType<typeof setInterval>;

	onMount(() => {
		websocketStore.connect();
		fetchHealth();
		refreshInterval = setInterval(fetchHealth, 30000);
	});

	onDestroy(() => {
		if (refreshInterval) clearInterval(refreshInterval);
	});

	async function fetchHealth() {
		try {
			health = await healthAPI.check();
			healthError = false;
		} catch {
			healthError = true;
		}
	}

	function getStatusColor(status: string): string {
		switch (status) {
			case 'connected':
				return 'bg-green-500';
			case 'connecting':
				return 'bg-yellow-500 animate-pulse';
			case 'error':
				return 'bg-red-500';
			default:
				return 'bg-gray-500';
		}
	}

	function getHealthColor(status: string): string {
		switch (status) {
			case 'healthy':
				return 'text-green-400';
			case 'degraded':
				return 'text-yellow-400';
			default:
				return 'text-red-400';
		}
	}
</script>

<header class="h-16 bg-surface-900 border-b border-surface-700 flex items-center justify-between px-6">
	<div class="flex items-center gap-4">
		<h2 class="text-lg font-semibold text-white">
			<slot name="title">Dashboard</slot>
		</h2>
	</div>

	<div class="flex items-center gap-6">
		<!-- API Health -->
		<div class="flex items-center gap-2 text-sm">
			<span class="text-slate-400">API:</span>
			{#if healthError}
				<span class="text-red-400">Offline</span>
			{:else if health}
				<span class={getHealthColor(health.status)}>{health.status}</span>
				<span class="text-slate-500">v{health.version}</span>
			{:else}
				<span class="text-slate-500">Checking...</span>
			{/if}
		</div>

		<!-- WebSocket Status -->
		<div class="flex items-center gap-2 text-sm">
			<span class="text-slate-400">WS:</span>
			<span class="flex items-center gap-2">
				<span class="w-2 h-2 rounded-full {getStatusColor($connectionStatus)}"></span>
				<span class="text-slate-300 capitalize">{$connectionStatus}</span>
			</span>
		</div>

		<!-- Refresh Button -->
		<button
			class="p-2 rounded-md bg-surface-800 hover:bg-surface-700 text-slate-400 hover:text-white transition-colors"
			onclick={fetchHealth}
			title="Refresh status"
		>
			<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
				/>
			</svg>
		</button>
	</div>
</header>
