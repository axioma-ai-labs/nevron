<script lang="ts">
	import { events, type WebSocketEvent } from '$lib/stores/websocket';

	interface Props {
		maxItems?: number;
	}

	let { maxItems = 10 }: Props = $props();

	function formatTime(timestamp: string): string {
		const date = new Date(timestamp);
		return date.toLocaleTimeString();
	}

	function getEventColor(type: string): string {
		if (type.includes('error')) return 'border-red-500';
		if (type.includes('success')) return 'border-green-500';
		if (type.includes('warning')) return 'border-yellow-500';
		return 'border-accent-500';
	}

	function getEventIcon(type: string): string {
		if (type.includes('action'))
			return `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
			</svg>`;
		if (type.includes('memory'))
			return `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/>
			</svg>`;
		if (type.includes('learning'))
			return `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
			</svg>`;
		return `<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
		</svg>`;
	}

	let displayEvents: WebSocketEvent[] = $derived($events.slice(0, maxItems));
</script>

<div class="card">
	<div class="flex items-center justify-between mb-4">
		<h3 class="card-header mb-0">Live Events</h3>
		<span class="text-xs text-slate-500">{$events.length} total</span>
	</div>

	{#if displayEvents.length === 0}
		<div class="text-center py-8 text-slate-500">
			<p>No events yet</p>
			<p class="text-xs mt-1">Events will appear here in real-time</p>
		</div>
	{:else}
		<div class="space-y-2 max-h-96 overflow-y-auto">
			{#each displayEvents as event (event.timestamp)}
				<div
					class="flex items-start gap-3 p-3 rounded-lg bg-surface-800 border-l-2 {getEventColor(
						event.type
					)}"
				>
					<div class="text-slate-400 flex-shrink-0 mt-0.5">
						{@html getEventIcon(event.type)}
					</div>
					<div class="flex-1 min-w-0">
						<div class="flex items-center justify-between gap-2">
							<span class="font-medium text-sm text-white truncate">{event.type}</span>
							<span class="text-xs text-slate-500 flex-shrink-0">{formatTime(event.timestamp)}</span>
						</div>
						{#if event.data.message}
							<p class="text-xs text-slate-400 mt-1 truncate">
								{event.data.message}
							</p>
						{/if}
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>
