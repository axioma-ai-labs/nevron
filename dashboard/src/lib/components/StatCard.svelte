<script lang="ts">
	interface Props {
		label: string;
		value: string | number;
		change?: number;
		icon?: string;
	}

	let { label, value, change, icon }: Props = $props();

	const iconMap: Record<string, string> = {
		up: `<svg class="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 10l7-7m0 0l7 7m-7-7v18"/>
		</svg>`,
		down: `<svg class="w-4 h-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3"/>
		</svg>`,
		actions: `<svg class="w-8 h-8 text-accent-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
		</svg>`,
		memory: `<svg class="w-8 h-8 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/>
		</svg>`,
		success: `<svg class="w-8 h-8 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
		</svg>`,
		tools: `<svg class="w-8 h-8 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 4a2 2 0 114 0v1a1 1 0 001 1h3a1 1 0 011 1v3a1 1 0 01-1 1h-1a2 2 0 100 4h1a1 1 0 011 1v3a1 1 0 01-1 1h-3a1 1 0 01-1-1v-1a2 2 0 10-4 0v1a1 1 0 01-1 1H7a1 1 0 01-1-1v-3a1 1 0 00-1-1H4a2 2 0 110-4h1a1 1 0 001-1V7a1 1 0 011-1h3a1 1 0 001-1V4z"/>
		</svg>`
	};
</script>

<div class="card flex items-center gap-4">
	{#if icon && iconMap[icon]}
		<div class="flex-shrink-0">
			{@html iconMap[icon]}
		</div>
	{/if}
	<div class="flex-1">
		<p class="stat-label">{label}</p>
		<div class="flex items-center gap-2">
			<p class="stat-value">{value}</p>
			{#if change !== undefined}
				<span class="flex items-center text-sm">
					{#if change > 0}
						{@html iconMap.up}
						<span class="text-green-400">+{change}%</span>
					{:else if change < 0}
						{@html iconMap.down}
						<span class="text-red-400">{change}%</span>
					{/if}
				</span>
			{/if}
		</div>
	</div>
</div>
