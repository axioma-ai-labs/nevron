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

<div class="flex h-screen overflow-hidden bg-apple-bg-primary">
	<!-- Sidebar -->
	<Sidebar />

	<!-- Main Content Area -->
	<div class="flex-1 flex flex-col overflow-hidden">
		<!-- Header -->
		<Header>
			{#snippet title()}
				{pageTitle}
			{/snippet}
		</Header>

		<!-- Page Content -->
		<main class="flex-1 overflow-y-auto p-6 bg-apple-bg-primary">
			<div class="animate-fade-in">
				{@render children()}
			</div>
		</main>
	</div>
</div>
