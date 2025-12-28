<script lang="ts">
	import type { Snippet } from 'svelte';

	interface Props {
		title?: string;
		class?: string;
		children: Snippet;
	}

	let { title = '', class: className = '', children }: Props = $props();
</script>

<div class="card {className}">
	{#if title}
		<h3 class="card-header">{title}</h3>
	{/if}
	{@render children()}
</div>
