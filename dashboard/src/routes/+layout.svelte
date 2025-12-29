<script lang="ts">
	import '../app.css';
	import Sidebar from '$lib/components/Sidebar.svelte';
	import Header from '$lib/components/Header.svelte';
	import { page } from '$app/stores';

	let { children } = $props();

	const pageTitles: Record<string, string> = {
		'/': 'Control',
		'/settings': 'Settings',
		'/explore': 'Explore'
	};

	// Get page title based on path prefix matching
	function getPageTitle(pathname: string): string {
		if (pathname === '/') return 'Control';
		if (pathname.startsWith('/settings')) return 'Settings';
		if (pathname.startsWith('/explore')) return 'Explore';
		return 'Nevron';
	}

	let pageTitle = $derived(getPageTitle($page.url.pathname));
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
