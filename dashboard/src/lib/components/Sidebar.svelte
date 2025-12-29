<script lang="ts">
	import { page } from '$app/stores';

	interface NavItem {
		href: string;
		label: string;
		icon: string;
	}

	const navItems: NavItem[] = [
		{ href: '/', label: 'Control', icon: 'control' },
		{ href: '/settings', label: 'Settings', icon: 'settings' },
		{ href: '/explore', label: 'Explore', icon: 'explore' }
	];

	function isActive(href: string, pathname: string): boolean {
		if (href === '/') return pathname === '/';
		return pathname.startsWith(href);
	}

	const iconMap: Record<string, string> = {
		control: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"/>
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
		</svg>`,
		settings: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
		</svg>`,
		explore: `<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
		</svg>`
	};
</script>

<aside class="w-64 bg-apple-bg-secondary flex flex-col h-screen border-r border-apple-border-subtle">
	<!-- Logo Section -->
	<div class="p-6">
		<div class="flex items-center gap-3">
			<div class="w-10 h-10 rounded-apple bg-gradient-to-br from-apple-blue to-apple-indigo flex items-center justify-center shadow-apple">
				<svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
					/>
				</svg>
			</div>
			<div>
				<h1 class="text-lg font-semibold text-apple-text-primary tracking-tight">Nevron</h1>
				<p class="text-xs text-apple-text-tertiary">AI Agent Dashboard</p>
			</div>
		</div>
	</div>

	<!-- Divider -->
	<div class="mx-4 border-t border-apple-border-subtle"></div>

	<!-- Navigation -->
	<nav class="flex-1 p-4 space-y-1 overflow-y-auto">
		{#each navItems as item}
			<a
				href={item.href}
				class="nav-link group"
				class:active={isActive(item.href, $page.url.pathname)}
			>
				<span class="flex-shrink-0 transition-colors duration-150">
					{@html iconMap[item.icon]}
				</span>
				<span class="text-sm">{item.label}</span>
			</a>
		{/each}
	</nav>

	<!-- Footer -->
	<div class="p-4 border-t border-apple-border-subtle">
		<div class="flex items-center justify-between">
			<span class="text-xs text-apple-text-quaternary">Nevron v1.0.0</span>
			<a
				href="https://github.com/axioma-ai-labs/nevron"
				target="_blank"
				rel="noopener noreferrer"
				class="text-apple-text-quaternary hover:text-apple-text-secondary transition-colors duration-150"
				aria-label="GitHub Repository"
			>
				<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
					<path fill-rule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clip-rule="evenodd"/>
				</svg>
			</a>
		</div>
	</div>
</aside>
