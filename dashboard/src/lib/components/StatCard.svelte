<script lang="ts">
	interface Props {
		label: string;
		value: string | number;
		change?: number;
		icon?: string;
		variant?: 'default' | 'blue' | 'green' | 'purple' | 'cyan' | 'orange';
	}

	let { label, value, change, icon, variant = 'default' }: Props = $props();

	const iconMap: Record<string, string> = {
		up: `<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 10l7-7m0 0l7 7m-7-7v18"/>
		</svg>`,
		down: `<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3"/>
		</svg>`,
		actions: `<svg class="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M13 10V3L4 14h7v7l9-11h-7z"/>
		</svg>`,
		memory: `<svg class="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/>
		</svg>`,
		success: `<svg class="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
		</svg>`,
		tools: `<svg class="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M11 4a2 2 0 114 0v1a1 1 0 001 1h3a1 1 0 011 1v3a1 1 0 01-1 1h-1a2 2 0 100 4h1a1 1 0 011 1v3a1 1 0 01-1 1h-3a1 1 0 01-1-1v-1a2 2 0 10-4 0v1a1 1 0 01-1 1H7a1 1 0 01-1-1v-3a1 1 0 00-1-1H4a2 2 0 110-4h1a1 1 0 001-1V7a1 1 0 011-1h3a1 1 0 001-1V4z"/>
		</svg>`
	};

	const iconColorMap: Record<string, string> = {
		actions: 'text-apple-blue',
		memory: 'text-apple-purple',
		success: 'text-apple-green',
		tools: 'text-apple-cyan'
	};

	const variantBgMap: Record<string, string> = {
		default: 'bg-apple-bg-tertiary',
		blue: 'bg-apple-blue/10',
		green: 'bg-apple-green/10',
		purple: 'bg-apple-purple/10',
		cyan: 'bg-apple-cyan/10',
		orange: 'bg-apple-orange/10'
	};

	function getIconBgClass(): string {
		if (!icon) return variantBgMap[variant];
		switch (icon) {
			case 'actions': return 'bg-apple-blue/10';
			case 'memory': return 'bg-apple-purple/10';
			case 'success': return 'bg-apple-green/10';
			case 'tools': return 'bg-apple-cyan/10';
			default: return variantBgMap[variant];
		}
	}
</script>

<div class="card-static group hover:border-apple-border-strong transition-all duration-150">
	<div class="flex items-center gap-4">
		{#if icon && iconMap[icon]}
			<div class="flex-shrink-0 w-12 h-12 rounded-apple-md {getIconBgClass()} flex items-center justify-center transition-transform duration-150 group-hover:scale-105">
				<span class={iconColorMap[icon] || 'text-apple-text-secondary'}>
					{@html iconMap[icon]}
				</span>
			</div>
		{/if}
		<div class="flex-1 min-w-0">
			<p class="stat-label truncate">{label}</p>
			<div class="flex items-baseline gap-2 mt-1">
				<p class="stat-value">{value}</p>
				{#if change !== undefined}
					<span class="flex items-center gap-0.5 text-sm font-medium">
						{#if change > 0}
							<span class="text-apple-green">
								{@html iconMap.up}
							</span>
							<span class="text-apple-green">+{change}%</span>
						{:else if change < 0}
							<span class="text-apple-red">
								{@html iconMap.down}
							</span>
							<span class="text-apple-red">{change}%</span>
						{/if}
					</span>
				{/if}
			</div>
		</div>
	</div>
</div>
