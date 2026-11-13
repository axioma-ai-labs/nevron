<script lang="ts">
	import { authRequired, setApiKey } from '$lib/api/client';

	let key = $state('');

	function save(event: SubmitEvent) {
		event.preventDefault();
		if (!key.trim()) return;
		setApiKey(key.trim());
		// Reload so every view and the WebSocket retry with the key
		window.location.reload();
	}
</script>

{#if $authRequired}
	<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
		<form
			class="w-full max-w-sm rounded-apple-lg bg-apple-bg-primary p-6 shadow-xl"
			onsubmit={save}
		>
			<h2 class="mb-2 text-lg font-semibold">API key required</h2>
			<p class="mb-4 text-sm opacity-70">
				Enter the value of <code>NEVRON_API_KEY</code> set on the API server. It is kept for
				this tab only.
			</p>
			<input
				type="password"
				autocomplete="off"
				class="mb-4 w-full rounded-apple-md border px-3 py-2"
				placeholder="API key"
				bind:value={key}
			/>
			<button type="submit" class="w-full rounded-apple-md bg-blue-600 px-3 py-2 text-white">
				Save
			</button>
		</form>
	</div>
{/if}
