<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { websocketStore, connectionStatus } from '$lib/stores/websocket';
	import { healthAPI, type HealthCheck } from '$lib/api/client';
	import type { Snippet } from 'svelte';

	let { title }: { title?: Snippet } = $props();

	let health: HealthCheck | null = $state(null);
	let healthError = $state(false);
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

	function getStatusDotClass(status: string): string {
		switch (status) {
			case 'connected':
				return 'status-dot-success';
			case 'connecting':
				return 'status-dot-warning';
			case 'error':
				return 'status-dot-danger';
			default:
				return 'status-dot-neutral';
		}
	}

	function getHealthBadgeClass(status: string): string {
		switch (status) {
			case 'healthy':
				return 'badge-success';
			case 'degraded':
				return 'badge-warning';
			default:
				return 'badge-danger';
		}
	}
</script>

<header class="h-16 bg-apple-bg-secondary border-b border-apple-border-subtle flex items-center justify-between px-6">
	<!-- Page Title -->
	<div class="flex items-center gap-4">
		<h2 class="text-xl font-semibold text-apple-text-primary tracking-tight">
			{#if title}
				{@render title()}
			{:else}
				Dashboard
			{/if}
		</h2>
	</div>

	<!-- Status Indicators -->
	<div class="flex items-center gap-6">
		<!-- API Health Status -->
		<div class="flex items-center gap-3">
			<span class="text-sm text-apple-text-tertiary">API</span>
			{#if healthError}
				<span class="badge badge-danger">Offline</span>
			{:else if health}
				<span class="badge {getHealthBadgeClass(health.status)}">{health.status}</span>
				<span class="text-xs text-apple-text-quaternary font-mono">v{health.version}</span>
			{:else}
				<span class="badge badge-neutral">Checking</span>
			{/if}
		</div>

		<!-- Divider -->
		<div class="w-px h-6 bg-apple-border-subtle"></div>

		<!-- WebSocket Status -->
		<div class="flex items-center gap-3">
			<span class="text-sm text-apple-text-tertiary">WebSocket</span>
			<span class="flex items-center gap-2">
				<span class="status-dot {getStatusDotClass($connectionStatus)}"></span>
				<span class="text-sm text-apple-text-secondary capitalize">{$connectionStatus}</span>
			</span>
		</div>

		<!-- Refresh Button -->
		<button
			class="btn btn-ghost btn-icon"
			onclick={fetchHealth}
			title="Refresh status"
		>
			<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="1.5"
					d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
				/>
			</svg>
		</button>
	</div>
</header>
