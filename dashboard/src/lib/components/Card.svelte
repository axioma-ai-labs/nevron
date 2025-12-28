<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		title?: string;
		subtitle?: string;
		class?: string;
		headerClass?: string;
		static?: boolean;
		children: Snippet;
		actions?: Snippet;
	}

	let {
		title = '',
		subtitle = '',
		class: className = '',
		headerClass = '',
		static: isStatic = false,
		children,
		actions
	}: Props = $props();
</script>

<div class="{isStatic ? 'card-static' : 'card'} {className}">
	{#if title || actions}
		<div class="flex items-center justify-between mb-5 {headerClass}">
			<div>
				{#if title}
					<h3 class="text-lg font-semibold text-apple-text-primary tracking-tight">{title}</h3>
				{/if}
				{#if subtitle}
					<p class="text-sm text-apple-text-tertiary mt-0.5">{subtitle}</p>
				{/if}
			</div>
			{#if actions}
				<div class="flex items-center gap-2">
					{@render actions()}
				</div>
			{/if}
		</div>
	{/if}
	{@render children()}
</div>
