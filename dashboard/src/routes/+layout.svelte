<script lang="ts">
	import '../app.css';
	import Sidebar from '$lib/components/Sidebar.svelte';
	import Header from '$lib/components/Header.svelte';
	import { page } from '$app/stores';

	let { children } = $props();

	const pageTitles: Record<string, string> = {
		'/': 'Dashboard',
		'/agent': 'Agent Control',
		'/runtime': 'Runtime Monitor',
		'/memory': 'Memory Explorer',
		'/learning': 'Learning Insights',
		'/mcp': 'MCP Manager'
	};

	let pageTitle = $derived(pageTitles[$page.url.pathname] || 'Dashboard');
</script>

<div class="flex h-screen overflow-hidden">
	<Sidebar />

	<div class="flex-1 flex flex-col overflow-hidden">
		<Header>
			{#snippet title()}
				{pageTitle}
			{/snippet}
		</Header>

		<main class="flex-1 overflow-y-auto p-6 bg-surface-950">
			{@render children()}
		</main>
	</div>
</div>
