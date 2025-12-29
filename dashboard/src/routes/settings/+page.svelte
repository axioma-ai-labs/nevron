<script lang="ts">
	import { onMount } from 'svelte';
	import Card from '$lib/components/Card.svelte';
	import {
		configAPI,
		AVAILABLE_MODELS,
		type UIConfigResponse,
		type UIConfigUpdate
	} from '$lib/api/client';

	// Form state
	let loading = $state(true);
	let saving = $state(false);
	let testing = $state(false);
	let saveMessage = $state<{ type: 'success' | 'error'; text: string } | null>(null);
	let testMessage = $state<{ type: 'success' | 'error'; text: string } | null>(null);

	// Config fields
	let llmProvider = $state('openai');
	let llmApiKey = $state('');
	let llmApiKeyMasked = $state('');
	let llmModel = $state('gpt-4o-mini');
	let agentPersonality = $state('');
	let agentGoal = $state('');
	let mcpEnabled = $state(false);

	// Track if API key has been changed
	let apiKeyChanged = $state(false);

	// Available models for current provider
	let availableModels = $derived(AVAILABLE_MODELS[llmProvider] || []);

	// Provider options
	const providers = [
		{ value: 'openai', label: 'OpenAI' },
		{ value: 'anthropic', label: 'Anthropic' },
		{ value: 'xai', label: 'xAI (Grok)' },
		{ value: 'deepseek', label: 'DeepSeek' },
		{ value: 'qwen', label: 'Qwen' },
		{ value: 'venice', label: 'Venice' }
	];

	onMount(async () => {
		await loadConfig();
	});

	async function loadConfig() {
		loading = true;
		try {
			const res = await configAPI.getUIConfig();
			if (res.data) {
				llmProvider = res.data.llm_provider;
				llmApiKeyMasked = res.data.llm_api_key_masked;
				llmModel = res.data.llm_model;
				agentPersonality = res.data.agent_personality;
				agentGoal = res.data.agent_goal;
				mcpEnabled = res.data.mcp_enabled;
			}
		} catch (e) {
			console.error('Failed to load config:', e);
		}
		loading = false;
	}

	function handleProviderChange() {
		// Reset model to first available for new provider
		const models = AVAILABLE_MODELS[llmProvider];
		if (models && models.length > 0) {
			llmModel = models[0];
		}
	}

	async function testApiKey() {
		if (!llmApiKey && !llmApiKeyMasked) {
			testMessage = { type: 'error', text: 'Please enter an API key first' };
			return;
		}

		testing = true;
		testMessage = null;

		try {
			const keyToTest = apiKeyChanged ? llmApiKey : '';
			if (!keyToTest) {
				testMessage = { type: 'error', text: 'Please enter a new API key to test' };
				testing = false;
				return;
			}

			const res = await configAPI.validateApiKey(llmProvider, keyToTest, llmModel);
			if (res.data.valid) {
				testMessage = { type: 'success', text: res.data.message };
			} else {
				testMessage = { type: 'error', text: res.data.message };
			}
		} catch (e) {
			testMessage = { type: 'error', text: 'Failed to validate API key' };
		}
		testing = false;
	}

	async function saveConfig() {
		saving = true;
		saveMessage = null;

		try {
			const update: UIConfigUpdate = {
				llm_provider: llmProvider,
				llm_model: llmModel,
				agent_personality: agentPersonality,
				agent_goal: agentGoal,
				mcp_enabled: mcpEnabled
			};

			// Only include API key if it was changed
			if (apiKeyChanged && llmApiKey) {
				update.llm_api_key = llmApiKey;
			}

			const res = await configAPI.saveUIConfig(update);
			if (res.success) {
				saveMessage = { type: 'success', text: 'Configuration saved successfully' };
				// Update masked key display
				if (res.data.llm_api_key_masked) {
					llmApiKeyMasked = res.data.llm_api_key_masked;
				}
				// Reset API key field
				llmApiKey = '';
				apiKeyChanged = false;
			} else {
				saveMessage = { type: 'error', text: 'Failed to save configuration' };
			}
		} catch (e) {
			saveMessage = { type: 'error', text: 'Failed to save configuration' };
		}
		saving = false;

		// Clear message after 3 seconds
		setTimeout(() => {
			saveMessage = null;
		}, 3000);
	}

	function handleApiKeyInput(event: Event) {
		const target = event.target as HTMLInputElement;
		llmApiKey = target.value;
		apiKeyChanged = true;
	}
</script>

<div class="space-y-6 max-w-3xl">
	<!-- Header -->
	<div>
		<h1 class="text-2xl font-bold text-apple-text-primary tracking-tight">Settings</h1>
		<p class="text-apple-text-secondary mt-1">Configure your Nevron agent</p>
	</div>

	{#if loading}
		<Card>
			<div class="space-y-4">
				{#each Array(6) as _}
					<div class="skeleton h-12 w-full"></div>
				{/each}
			</div>
		</Card>
	{:else}
		<!-- LLM Settings -->
		<Card title="LLM Configuration">
			<div class="space-y-5">
				<!-- Provider -->
				<div>
					<label for="provider" class="block text-sm font-medium text-apple-text-secondary mb-2">
						Provider
					</label>
					<select
						id="provider"
						class="input w-full"
						bind:value={llmProvider}
						onchange={handleProviderChange}
					>
						{#each providers as provider}
							<option value={provider.value}>{provider.label}</option>
						{/each}
					</select>
				</div>

				<!-- API Key -->
				<div>
					<label for="apiKey" class="block text-sm font-medium text-apple-text-secondary mb-2">
						API Key
					</label>
					<div class="flex gap-3">
						<div class="flex-1 relative">
							<input
								id="apiKey"
								type="password"
								class="input w-full"
								placeholder={llmApiKeyMasked || 'Enter your API key'}
								value={llmApiKey}
								oninput={handleApiKeyInput}
							/>
							{#if llmApiKeyMasked && !apiKeyChanged}
								<span class="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-apple-text-tertiary">
									{llmApiKeyMasked}
								</span>
							{/if}
						</div>
						<button
							class="btn btn-secondary"
							onclick={testApiKey}
							disabled={testing || (!llmApiKey && !llmApiKeyMasked)}
						>
							{testing ? 'Testing...' : 'Test'}
						</button>
					</div>
					{#if testMessage}
						<p class="mt-2 text-sm {testMessage.type === 'success' ? 'text-apple-green' : 'text-apple-red'}">
							{testMessage.text}
						</p>
					{/if}
				</div>

				<!-- Model -->
				<div>
					<label for="model" class="block text-sm font-medium text-apple-text-secondary mb-2">
						Model
					</label>
					<select id="model" class="input w-full" bind:value={llmModel}>
						{#each availableModels as model}
							<option value={model}>{model}</option>
						{/each}
					</select>
				</div>
			</div>
		</Card>

		<!-- Agent Settings -->
		<Card title="Agent Identity">
			<div class="space-y-5">
				<!-- Personality -->
				<div>
					<label for="personality" class="block text-sm font-medium text-apple-text-secondary mb-2">
						Personality
					</label>
					<textarea
						id="personality"
						class="input w-full min-h-[100px] resize-y"
						placeholder="Describe the agent's personality..."
						bind:value={agentPersonality}
					></textarea>
					<p class="mt-1 text-xs text-apple-text-tertiary">
						Define how the agent should behave and communicate
					</p>
				</div>

				<!-- Goal -->
				<div>
					<label for="goal" class="block text-sm font-medium text-apple-text-secondary mb-2">
						Goal
					</label>
					<textarea
						id="goal"
						class="input w-full min-h-[100px] resize-y"
						placeholder="What should the agent accomplish..."
						bind:value={agentGoal}
					></textarea>
					<p class="mt-1 text-xs text-apple-text-tertiary">
						The primary objective the agent should work towards
					</p>
				</div>
			</div>
		</Card>

		<!-- MCP Settings -->
		<Card title="MCP Integration">
			<div class="flex items-center justify-between">
				<div>
					<p class="text-apple-text-primary font-medium">Enable MCP</p>
					<p class="text-sm text-apple-text-tertiary mt-1">
						Allow the agent to use Model Context Protocol tools
					</p>
				</div>
				<label class="relative inline-flex items-center cursor-pointer">
					<input type="checkbox" class="sr-only peer" bind:checked={mcpEnabled} />
					<div class="w-11 h-6 bg-apple-bg-tertiary peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-apple-blue"></div>
				</label>
			</div>
		</Card>

		<!-- Save Button -->
		<div class="flex items-center justify-between">
			<div>
				{#if saveMessage}
					<p class="text-sm {saveMessage.type === 'success' ? 'text-apple-green' : 'text-apple-red'}">
						{saveMessage.text}
					</p>
				{/if}
			</div>
			<button class="btn btn-primary px-8" onclick={saveConfig} disabled={saving}>
				{#if saving}
					<svg class="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
						<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
						<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
					</svg>
					Saving...
				{:else}
					Save Configuration
				{/if}
			</button>
		</div>
	{/if}
</div>
