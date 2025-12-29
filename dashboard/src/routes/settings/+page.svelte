<script lang="ts">
	import { onMount } from 'svelte';
	import Card from '$lib/components/Card.svelte';
	import {
		configAPI,
		AVAILABLE_MODELS,
		type UIConfigResponse,
		type UIConfigUpdate,
		type ActionInfo,
		type IntegrationStatus,
		type MCPServerConfig
	} from '$lib/api/client';

	// Form state
	let loading = $state(true);
	let saving = $state(false);
	let testing = $state(false);
	let saveMessage = $state<{ type: 'success' | 'error'; text: string } | null>(null);
	let testMessage = $state<{ type: 'success' | 'error'; text: string } | null>(null);

	// Active tab
	let activeTab = $state<'llm' | 'agent' | 'actions' | 'integrations' | 'mcp'>('llm');

	// Config fields - LLM
	let llmProvider = $state('openai');
	let llmApiKey = $state('');
	let llmApiKeyMasked = $state('');
	let llmModel = $state('gpt-4o-mini');

	// Config fields - Agent
	let agentName = $state('Nevron');
	let agentPersonality = $state('');
	let agentGoal = $state('');
	let restTime = $state(300);
	let maxConsecutiveFailures = $state(3);
	let verbosity = $state('normal');

	// Config fields - Actions
	let availableActions = $state<ActionInfo[]>([]);
	let enabledActions = $state<string[]>([]);
	let actionIntegrationMap = $state<Record<string, string>>({});

	// Config fields - Integrations
	let integrations = $state<Record<string, Record<string, string>>>({});
	let integrationStatus = $state<IntegrationStatus[]>([]);

	// Config fields - MCP
	let mcpEnabled = $state(false);
	let mcpServers = $state<MCPServerConfig[]>([]);

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

	// Integration display names
	const integrationLabels: Record<string, string> = {
		twitter: 'Twitter/X',
		telegram: 'Telegram',
		discord: 'Discord',
		slack: 'Slack',
		whatsapp: 'WhatsApp',
		github: 'GitHub',
		google_drive: 'Google Drive',
		tavily: 'Tavily',
		perplexity: 'Perplexity',
		shopify: 'Shopify',
		youtube: 'YouTube',
		spotify: 'Spotify',
		lens: 'Lens Protocol'
	};

	// Integration field definitions
	const integrationFields: Record<string, { key: string; label: string; type: string }[]> = {
		twitter: [
			{ key: 'api_key', label: 'API Key', type: 'password' },
			{ key: 'api_secret_key', label: 'API Secret Key', type: 'password' },
			{ key: 'access_token', label: 'Access Token', type: 'password' },
			{ key: 'access_token_secret', label: 'Access Token Secret', type: 'password' }
		],
		telegram: [
			{ key: 'bot_token', label: 'Bot Token', type: 'password' },
			{ key: 'chat_id', label: 'Chat ID', type: 'text' }
		],
		discord: [
			{ key: 'bot_token', label: 'Bot Token', type: 'password' },
			{ key: 'channel_id', label: 'Channel ID', type: 'text' }
		],
		slack: [
			{ key: 'bot_token', label: 'Bot Token', type: 'password' },
			{ key: 'app_token', label: 'App Token', type: 'password' }
		],
		whatsapp: [
			{ key: 'id_instance', label: 'Instance ID', type: 'text' },
			{ key: 'api_token', label: 'API Token', type: 'password' }
		],
		github: [{ key: 'token', label: 'Personal Access Token', type: 'password' }],
		tavily: [{ key: 'api_key', label: 'API Key', type: 'password' }],
		perplexity: [
			{ key: 'api_key', label: 'API Key', type: 'password' },
			{ key: 'model', label: 'Model', type: 'text' }
		],
		shopify: [
			{ key: 'api_key', label: 'API Key', type: 'password' },
			{ key: 'password', label: 'Password', type: 'password' },
			{ key: 'store_name', label: 'Store Name', type: 'text' }
		],
		youtube: [
			{ key: 'api_key', label: 'API Key', type: 'password' },
			{ key: 'playlist_id', label: 'Playlist ID', type: 'text' }
		],
		spotify: [
			{ key: 'client_id', label: 'Client ID', type: 'password' },
			{ key: 'client_secret', label: 'Client Secret', type: 'password' },
			{ key: 'redirect_uri', label: 'Redirect URI', type: 'text' }
		],
		lens: [
			{ key: 'api_key', label: 'API Key', type: 'password' },
			{ key: 'profile_id', label: 'Profile ID', type: 'text' }
		]
	};

	// Group actions by category
	let actionsByCategory = $derived(() => {
		const grouped: Record<string, ActionInfo[]> = {};
		for (const action of availableActions) {
			if (!grouped[action.category]) {
				grouped[action.category] = [];
			}
			grouped[action.category].push(action);
		}
		return grouped;
	});

	// Category display names
	const categoryLabels: Record<string, string> = {
		workflows: 'Workflows',
		social_media: 'Social Media',
		research: 'Research',
		development: 'Development',
		ecommerce: 'E-Commerce',
		media: 'Media',
		other: 'Other'
	};

	onMount(async () => {
		await loadConfig();
		await loadActions();
		await loadIntegrationsStatus();
	});

	async function loadConfig() {
		loading = true;
		try {
			const res = await configAPI.getUIConfig();
			if (res.data) {
				// LLM
				llmProvider = res.data.llm_provider;
				llmApiKeyMasked = res.data.llm_api_key_masked;
				llmModel = res.data.llm_model;
				// Agent
				agentName = res.data.agent_name;
				agentPersonality = res.data.agent_personality;
				agentGoal = res.data.agent_goal;
				restTime = res.data.agent_behavior.rest_time;
				maxConsecutiveFailures = res.data.agent_behavior.max_consecutive_failures;
				verbosity = res.data.agent_behavior.verbosity;
				// Actions
				enabledActions = res.data.enabled_actions;
				// Integrations (masked values)
				integrations = res.data.integrations as unknown as Record<string, Record<string, string>>;
				// MCP
				mcpEnabled = res.data.mcp_enabled;
				mcpServers = res.data.mcp_servers;
			}
		} catch (e) {
			console.error('Failed to load config:', e);
		}
		loading = false;
	}

	async function loadActions() {
		try {
			const res = await configAPI.getAvailableActions();
			if (res.data) {
				availableActions = res.data.actions;
				actionIntegrationMap = res.data.action_integration_map;
			}
		} catch (e) {
			console.error('Failed to load actions:', e);
		}
	}

	async function loadIntegrationsStatus() {
		try {
			const res = await configAPI.getIntegrationsStatus();
			if (res.data) {
				integrationStatus = res.data;
			}
		} catch (e) {
			console.error('Failed to load integrations status:', e);
		}
	}

	function handleProviderChange() {
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
				agent_name: agentName,
				agent_personality: agentPersonality,
				agent_goal: agentGoal,
				agent_behavior: {
					rest_time: restTime,
					max_consecutive_failures: maxConsecutiveFailures,
					verbosity: verbosity
				},
				enabled_actions: enabledActions,
				mcp_enabled: mcpEnabled,
				mcp_servers: mcpServers
			};

			// Only include API key if it was changed
			if (apiKeyChanged && llmApiKey) {
				update.llm_api_key = llmApiKey;
			}

			const res = await configAPI.saveUIConfig(update);
			if (res.success) {
				saveMessage = { type: 'success', text: 'Configuration saved successfully' };
				if (res.data.llm_api_key_masked) {
					llmApiKeyMasked = res.data.llm_api_key_masked;
				}
				llmApiKey = '';
				apiKeyChanged = false;
			} else {
				saveMessage = { type: 'error', text: 'Failed to save configuration' };
			}
		} catch (e) {
			saveMessage = { type: 'error', text: 'Failed to save configuration' };
		}
		saving = false;

		setTimeout(() => {
			saveMessage = null;
		}, 3000);
	}

	function handleApiKeyInput(event: Event) {
		const target = event.target as HTMLInputElement;
		llmApiKey = target.value;
		apiKeyChanged = true;
	}

	function toggleAction(actionValue: string) {
		if (enabledActions.includes(actionValue)) {
			enabledActions = enabledActions.filter((a) => a !== actionValue);
		} else {
			enabledActions = [...enabledActions, actionValue];
		}
	}

	function isActionEnabled(actionValue: string): boolean {
		return enabledActions.includes(actionValue);
	}

	function getIntegrationForAction(actionValue: string): string | undefined {
		return actionIntegrationMap[actionValue];
	}

	function isIntegrationConfigured(integrationName: string): boolean {
		const status = integrationStatus.find((s) => s.integration === integrationName);
		return status?.configured ?? false;
	}

	function addMcpServer() {
		mcpServers = [
			...mcpServers,
			{
				name: '',
				transport: 'stdio',
				command: '',
				args: [],
				env: {},
				enabled: true
			}
		];
	}

	function removeMcpServer(index: number) {
		mcpServers = mcpServers.filter((_, i) => i !== index);
	}

	function updateMcpServerArgs(index: number, value: string) {
		const updated = [...mcpServers];
		updated[index].args = value
			.split('\n')
			.map((a) => a.trim())
			.filter((a) => a);
		mcpServers = updated;
	}
</script>

<div class="space-y-6 max-w-4xl">
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
		<!-- Tabs -->
		<div class="flex gap-1 p-1 bg-apple-bg-tertiary rounded-lg">
			<button
				class="flex-1 px-4 py-2 text-sm font-medium rounded-md transition-colors {activeTab ===
				'llm'
					? 'bg-white text-apple-text-primary shadow-sm'
					: 'text-apple-text-secondary hover:text-apple-text-primary'}"
				onclick={() => (activeTab = 'llm')}
			>
				LLM
			</button>
			<button
				class="flex-1 px-4 py-2 text-sm font-medium rounded-md transition-colors {activeTab ===
				'agent'
					? 'bg-white text-apple-text-primary shadow-sm'
					: 'text-apple-text-secondary hover:text-apple-text-primary'}"
				onclick={() => (activeTab = 'agent')}
			>
				Agent
			</button>
			<button
				class="flex-1 px-4 py-2 text-sm font-medium rounded-md transition-colors {activeTab ===
				'actions'
					? 'bg-white text-apple-text-primary shadow-sm'
					: 'text-apple-text-secondary hover:text-apple-text-primary'}"
				onclick={() => (activeTab = 'actions')}
			>
				Actions
			</button>
			<button
				class="flex-1 px-4 py-2 text-sm font-medium rounded-md transition-colors {activeTab ===
				'integrations'
					? 'bg-white text-apple-text-primary shadow-sm'
					: 'text-apple-text-secondary hover:text-apple-text-primary'}"
				onclick={() => (activeTab = 'integrations')}
			>
				Integrations
			</button>
			<button
				class="flex-1 px-4 py-2 text-sm font-medium rounded-md transition-colors {activeTab ===
				'mcp'
					? 'bg-white text-apple-text-primary shadow-sm'
					: 'text-apple-text-secondary hover:text-apple-text-primary'}"
				onclick={() => (activeTab = 'mcp')}
			>
				MCP
			</button>
		</div>

		<!-- LLM Tab -->
		{#if activeTab === 'llm'}
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
									<span
										class="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-apple-text-tertiary"
									>
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
							<p
								class="mt-2 text-sm {testMessage.type === 'success'
									? 'text-apple-green'
									: 'text-apple-red'}"
							>
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
		{/if}

		<!-- Agent Tab -->
		{#if activeTab === 'agent'}
			<Card title="Agent Identity">
				<div class="space-y-5">
					<!-- Name -->
					<div>
						<label for="agentName" class="block text-sm font-medium text-apple-text-secondary mb-2">
							Agent Name
						</label>
						<input id="agentName" type="text" class="input w-full" bind:value={agentName} />
					</div>

					<!-- Personality -->
					<div>
						<label
							for="personality"
							class="block text-sm font-medium text-apple-text-secondary mb-2"
						>
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

			<Card title="Agent Behavior">
				<div class="space-y-5">
					<!-- Rest Time -->
					<div>
						<label for="restTime" class="block text-sm font-medium text-apple-text-secondary mb-2">
							Rest Time (seconds)
						</label>
						<input
							id="restTime"
							type="number"
							class="input w-full"
							bind:value={restTime}
							min="1"
							max="3600"
						/>
						<p class="mt-1 text-xs text-apple-text-tertiary">
							How long the agent waits between actions
						</p>
					</div>

					<!-- Max Consecutive Failures -->
					<div>
						<label
							for="maxFailures"
							class="block text-sm font-medium text-apple-text-secondary mb-2"
						>
							Max Consecutive Failures
						</label>
						<input
							id="maxFailures"
							type="number"
							class="input w-full"
							bind:value={maxConsecutiveFailures}
							min="1"
							max="10"
						/>
						<p class="mt-1 text-xs text-apple-text-tertiary">
							Number of failures before triggering intervention
						</p>
					</div>

					<!-- Verbosity -->
					<div>
						<label for="verbosity" class="block text-sm font-medium text-apple-text-secondary mb-2">
							Logging Verbosity
						</label>
						<select id="verbosity" class="input w-full" bind:value={verbosity}>
							<option value="quiet">Quiet</option>
							<option value="normal">Normal</option>
							<option value="verbose">Verbose</option>
						</select>
					</div>
				</div>
			</Card>
		{/if}

		<!-- Actions Tab -->
		{#if activeTab === 'actions'}
			<Card title="Enabled Actions">
				<p class="text-sm text-apple-text-secondary mb-4">
					Select which actions the agent can perform. Actions requiring integrations will show the
					integration name.
				</p>

				{#each Object.entries(actionsByCategory()) as [category, actions]}
					<div class="mb-6 last:mb-0">
						<h3 class="text-sm font-semibold text-apple-text-primary mb-3">
							{categoryLabels[category] || category}
						</h3>
						<div class="space-y-2">
							{#each actions as action}
								{@const integration = getIntegrationForAction(action.value)}
								{@const integrationConfigured = integration
									? isIntegrationConfigured(integration)
									: true}
								<label
									class="flex items-center gap-3 p-3 rounded-lg border border-apple-border-subtle hover:bg-apple-bg-secondary transition-colors cursor-pointer"
								>
									<input
										type="checkbox"
										class="w-4 h-4 rounded border-apple-border-subtle text-apple-blue focus:ring-apple-blue"
										checked={isActionEnabled(action.value)}
										onchange={() => toggleAction(action.value)}
									/>
									<div class="flex-1">
										<span class="text-sm font-medium text-apple-text-primary">
											{action.name.replace(/_/g, ' ')}
										</span>
										{#if integration}
											<span
												class="ml-2 text-xs px-2 py-0.5 rounded-full {integrationConfigured
													? 'bg-apple-green/10 text-apple-green'
													: 'bg-apple-orange/10 text-apple-orange'}"
											>
												{integrationLabels[integration] || integration}
												{integrationConfigured ? '' : '(not configured)'}
											</span>
										{/if}
									</div>
								</label>
							{/each}
						</div>
					</div>
				{/each}
			</Card>
		{/if}

		<!-- Integrations Tab -->
		{#if activeTab === 'integrations'}
			<div class="space-y-4">
				{#each Object.entries(integrationFields) as [integrationName, fields]}
					{@const status = integrationStatus.find((s) => s.integration === integrationName)}
					<Card>
						<div class="flex items-center justify-between mb-4">
							<h3 class="text-lg font-medium text-apple-text-primary">
								{integrationLabels[integrationName] || integrationName}
							</h3>
							{#if status}
								<span
									class="text-xs px-2 py-1 rounded-full {status.configured
										? 'bg-apple-green/10 text-apple-green'
										: 'bg-apple-orange/10 text-apple-orange'}"
								>
									{status.configured ? 'Configured' : 'Not Configured'}
								</span>
							{/if}
						</div>
						<div class="space-y-4">
							{#each fields as field}
								<div>
									<label
										for="{integrationName}_{field.key}"
										class="block text-sm font-medium text-apple-text-secondary mb-2"
									>
										{field.label}
									</label>
									<input
										id="{integrationName}_{field.key}"
										type={field.type}
										class="input w-full"
										placeholder={integrations[integrationName]?.[field.key] || `Enter ${field.label}`}
									/>
								</div>
							{/each}
						</div>
					</Card>
				{/each}
			</div>
		{/if}

		<!-- MCP Tab -->
		{#if activeTab === 'mcp'}
			<Card title="MCP Integration">
				<div class="flex items-center justify-between mb-6">
					<div>
						<p class="text-apple-text-primary font-medium">Enable MCP</p>
						<p class="text-sm text-apple-text-tertiary mt-1">
							Allow the agent to use Model Context Protocol tools
						</p>
					</div>
					<label class="relative inline-flex items-center cursor-pointer">
						<input type="checkbox" class="sr-only peer" bind:checked={mcpEnabled} />
						<div
							class="w-11 h-6 bg-apple-bg-tertiary peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-apple-blue"
						></div>
					</label>
				</div>

				{#if mcpEnabled}
					<div class="space-y-4">
						<div class="flex items-center justify-between">
							<h3 class="text-sm font-semibold text-apple-text-primary">MCP Servers</h3>
							<button class="btn btn-secondary text-sm" onclick={addMcpServer}>
								+ Add Server
							</button>
						</div>

						{#each mcpServers as server, index}
							<div class="p-4 border border-apple-border-subtle rounded-lg space-y-4">
								<div class="flex items-center justify-between">
									<input
										type="text"
										class="input flex-1 mr-4"
										placeholder="Server name"
										bind:value={server.name}
									/>
									<button
										class="text-apple-red hover:text-apple-red/80"
										onclick={() => removeMcpServer(index)}
									>
										Remove
									</button>
								</div>

								<div class="grid grid-cols-2 gap-4">
									<div>
										<label class="block text-sm text-apple-text-secondary mb-1" for="mcp-transport-{index}">Transport</label>
										<select id="mcp-transport-{index}" class="input w-full" bind:value={server.transport}>
											<option value="stdio">STDIO</option>
											<option value="http">HTTP</option>
											<option value="sse">SSE</option>
										</select>
									</div>
									<div>
										<span class="block text-sm text-apple-text-secondary mb-1">Enabled</span>
										<label class="flex items-center mt-2">
											<input type="checkbox" class="mr-2" bind:checked={server.enabled} />
											<span class="text-sm">Active</span>
										</label>
									</div>
								</div>

								{#if server.transport === 'stdio'}
									<div>
										<label class="block text-sm text-apple-text-secondary mb-1" for="mcp-command-{index}">Command</label>
										<input
											id="mcp-command-{index}"
											type="text"
											class="input w-full"
											placeholder="e.g., npx"
											bind:value={server.command}
										/>
									</div>
									<div>
										<label class="block text-sm text-apple-text-secondary mb-1" for="mcp-args-{index}"
											>Arguments (one per line)</label
										>
										<textarea
											id="mcp-args-{index}"
											class="input w-full min-h-[80px]"
											placeholder="@modelcontextprotocol/server-filesystem&#10;/workspace"
											value={server.args.join('\n')}
											oninput={(e) =>
												updateMcpServerArgs(index, (e.target as HTMLTextAreaElement).value)}
										></textarea>
									</div>
								{:else}
									<div>
										<label class="block text-sm text-apple-text-secondary mb-1" for="mcp-url-{index}">URL</label>
										<input
											id="mcp-url-{index}"
											type="text"
											class="input w-full"
											placeholder="https://..."
											bind:value={server.url}
										/>
									</div>
								{/if}
							</div>
						{/each}

						{#if mcpServers.length === 0}
							<p class="text-center text-apple-text-tertiary py-8">
								No MCP servers configured. Click "Add Server" to add one.
							</p>
						{/if}
					</div>
				{/if}
			</Card>
		{/if}

		<!-- Save Button -->
		<div class="flex items-center justify-between">
			<div>
				{#if saveMessage}
					<p
						class="text-sm {saveMessage.type === 'success' ? 'text-apple-green' : 'text-apple-red'}"
					>
						{saveMessage.text}
					</p>
				{/if}
			</div>
			<button class="btn btn-primary px-8" onclick={saveConfig} disabled={saving}>
				{#if saving}
					<svg class="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
						<circle
							class="opacity-25"
							cx="12"
							cy="12"
							r="10"
							stroke="currentColor"
							stroke-width="4"
						></circle>
						<path
							class="opacity-75"
							fill="currentColor"
							d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
						></path>
					</svg>
					Saving...
				{:else}
					Save Configuration
				{/if}
			</button>
		</div>
	{/if}
</div>
